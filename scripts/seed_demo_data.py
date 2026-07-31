#!/usr/bin/env python3
"""Create safe demo data without modifying the active database by default.

Default behavior:
  - reads data/stocksense.db when it exists
  - writes a separate data/stocksense_demo.db copy
  - inserts only DEMO_* symbols and DEMO_SEED_V1 tagged rows

Use --apply-current only when you intentionally want demo rows in data/stocksense.db.
The script is idempotent: running it again skips rows it already seeded.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.db import apply_migrations
from backend.domain.predictions import canonicalize_prediction

DEFAULT_SOURCE_DB = PROJECT_ROOT / "data" / "stocksense.db"
DEFAULT_DEMO_DB = PROJECT_ROOT / "data" / "stocksense_demo.db"
SEED_MARKER = "DEMO_SEED_V1"


@dataclass(frozen=True)
class DemoPosition:
    symbol: str
    name: str
    sector: str
    quantity: float
    avg_price: float
    current_price: float
    target_price: float
    signal: str
    confidence: float
    days_ago: int


DEMO_POSITIONS = (
    DemoPosition("DEMOALPHA", "Demo Alpha Industries", "Technology", 12, 1480.0, 1548.0, 1710.0, "BUY", 78.0, 130),
    DemoPosition("DEMOBETA", "Demo Beta Bank", "Financial Services", 20, 642.0, 618.0, 690.0, "HOLD", 64.0, 95),
    DemoPosition("DEMOGAMMA", "Demo Gamma Energy", "Energy", 35, 214.0, 232.0, 255.0, "BUY", 72.0, 60),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed non-destructive demo data for StockSense.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE_DB, help="Source DB to copy when creating demo DB.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DEMO_DB, help="Target DB to seed.")
    parser.add_argument("--refresh-copy", action="store_true", help="Recreate demo DB from source before seeding.")
    parser.add_argument("--apply", action="store_true", help="Actually write seed rows. Without this, only prints a dry run.")
    parser.add_argument(
        "--apply-current",
        action="store_true",
        help="Seed the active data/stocksense.db. Requires --apply and bypasses demo-copy mode.",
    )
    return parser.parse_args()


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def ensure_schema(target: Path) -> None:
    apply_migrations(target, backup=target.exists(), backup_dir=target.parent / "backups")


def prepare_target_db(source: Path, target: Path, *, refresh_copy: bool, apply_current: bool, dry_run: bool) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if apply_current:
        return

    if target.exists() and not refresh_copy:
        return

    if dry_run:
        return

    if target.exists():
        target.unlink()

    if source.exists():
        shutil.copy2(source, target)
        return

    target.touch()


def row_exists(conn: sqlite3.Connection, query: str, params: Iterable[object]) -> bool:
    return bool(conn.execute(query, tuple(params)).fetchone())


def rebuild_portfolio_summary(conn: sqlite3.Connection, symbol: str) -> None:
    row = conn.execute(
        """
        SELECT
            COALESCE(SUM(remaining_quantity), 0) AS quantity,
            COALESCE(SUM(remaining_quantity * buy_price), 0) AS cost,
            MIN(buy_date) AS added_date
        FROM portfolio_lots
        WHERE symbol = ? AND remaining_quantity > 0
        """,
        (symbol,),
    ).fetchone()
    quantity = float(row["quantity"] or 0)
    if quantity <= 0:
        return
    avg_price = float(row["cost"] or 0) / quantity
    added_date = row["added_date"] or datetime.now().isoformat()
    conn.execute(
        """
        INSERT INTO portfolio (symbol, quantity, avg_price, added_date)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET
            quantity = excluded.quantity,
            avg_price = excluded.avg_price,
            added_date = excluded.added_date
        """,
        (symbol, quantity, round(avg_price, 4), added_date),
    )


def seed_position(conn: sqlite3.Connection, position: DemoPosition, *, now: datetime) -> list[str]:
    actions: list[str] = []
    trade_date = (now - timedelta(days=position.days_ago)).isoformat()
    created_at = now.isoformat()

    conn.execute(
        """
        INSERT INTO dynamic_symbols (symbol, name, sector, last_updated)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET
            name = excluded.name,
            sector = excluded.sector,
            last_updated = excluded.last_updated
        """,
        (position.symbol, position.name, position.sector, created_at),
    )
    actions.append(f"upsert dynamic symbol {position.symbol}")

    has_demo_lot = row_exists(
        conn,
        """
        SELECT 1
        FROM portfolio_transactions
        WHERE symbol = ? AND notes = ?
        LIMIT 1
        """,
        (position.symbol, SEED_MARKER),
    )
    if not has_demo_lot:
        cursor = conn.execute(
            """
            INSERT INTO portfolio_transactions
            (symbol, side, quantity, price, trade_date, fees, notes, created_at)
            VALUES (?, 'BUY', ?, ?, ?, 0, ?, ?)
            """,
            (
                position.symbol,
                position.quantity,
                position.avg_price,
                trade_date,
                SEED_MARKER,
                created_at,
            ),
        )
        conn.execute(
            """
            INSERT INTO portfolio_lots
            (symbol, buy_txn_id, buy_date, buy_price, original_quantity, remaining_quantity, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                position.symbol,
                cursor.lastrowid,
                trade_date,
                position.avg_price,
                position.quantity,
                position.quantity,
                created_at,
            ),
        )
        actions.append(f"insert demo portfolio lot {position.symbol}")
    else:
        actions.append(f"skip existing demo lot {position.symbol}")

    rebuild_portfolio_summary(conn, position.symbol)

    has_demo_prediction = row_exists(
        conn,
        """
        SELECT 1
        FROM predictions
        WHERE symbol = ? AND models_used LIKE ?
        LIMIT 1
        """,
        (position.symbol, f"%{SEED_MARKER}%"),
    )
    if not has_demo_prediction:
        expected_return = ((position.target_price - position.current_price) / position.current_price) * 100
        canonical = canonicalize_prediction(
            {
                "symbol": position.symbol,
                "horizon": "6m",
                "as_of": created_at,
                "current_price": position.current_price,
                "target_price": position.target_price,
                "expected_return": expected_return,
                "signal": position.signal,
                "confidence": position.confidence,
                "risk": "DEMO",
                "source_type": "synthetic_demo",
                "provider": "seed_demo_data",
                "data_quality": "demo",
                "model_version": SEED_MARKER,
                "feature_version": "demo-v1",
                "is_synthetic": True,
                "is_demo": True,
            }
        )
        assert canonical is not None
        payload = canonical.to_dict()
        conn.execute(
            """
            INSERT INTO predictions
            (fingerprint, symbol, horizon, as_of, predicted_price, current_price, target_price,
             expected_return, signal, confidence, risk, source_type, provider, data_quality,
             model_version, feature_version, metadata_json, models_used, timestamp, matured_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["fingerprint"],
                payload["symbol"],
                payload["horizon"],
                payload["as_of"],
                round(position.target_price, 2),
                round(position.current_price, 2),
                round(position.target_price, 2),
                round(expected_return, 4),
                payload["signal"],
                payload["confidence"],
                payload["risk"],
                payload["source_type"],
                payload["provider"],
                payload["data_quality"],
                payload["model_version"],
                payload["feature_version"],
                json.dumps({"seed_marker": SEED_MARKER, "is_demo": True, "is_synthetic": True}),
                json.dumps([SEED_MARKER, "demo-technical"]),
                created_at,
                payload["matured_at"],
            ),
        )
        actions.append(f"insert demo prediction {position.symbol}")
    else:
        actions.append(f"skip existing demo prediction {position.symbol}")

    return actions


def seed_model_performance(conn: sqlite3.Connection, *, now: datetime) -> list[str]:
    model_name = f"{SEED_MARKER}_ENSEMBLE"
    if row_exists(conn, "SELECT 1 FROM model_performance WHERE model_name = ? LIMIT 1", (model_name,)):
        return [f"skip existing model performance {model_name}"]
    conn.execute(
        """
        INSERT INTO model_performance
        (model_name, model_version, feature_version, directional_accuracy, coverage, metrics_json, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            model_name,
            SEED_MARKER,
            "demo-v1",
            None,
            0,
            json.dumps({"basis": "demo_seed_no_matured_outcomes", "weight": 0.35}),
            now.isoformat(),
        ),
    )
    return [f"insert model performance {model_name}"]


def print_plan(target: Path, source: Path, *, apply_current: bool, dry_run: bool) -> None:
    mode = "active DB" if apply_current else "demo DB copy"
    action = "DRY RUN" if dry_run else "APPLY"
    print(f"{action}: seed {mode}")
    print(f"Source DB: {source}")
    print(f"Target DB: {target}")
    print(f"Seed marker: {SEED_MARKER}")
    print("Demo symbols:", ", ".join(position.symbol for position in DEMO_POSITIONS))


def main() -> int:
    args = parse_args()
    source = resolve_path(args.source)
    target = DEFAULT_SOURCE_DB if args.apply_current else resolve_path(args.db)
    dry_run = not args.apply

    if args.apply_current and not args.apply:
        raise SystemExit("--apply-current requires --apply")

    print_plan(target, source, apply_current=args.apply_current, dry_run=dry_run)
    prepare_target_db(source, target, refresh_copy=args.refresh_copy, apply_current=args.apply_current, dry_run=dry_run)

    if dry_run:
        print("No database writes performed. Re-run with --apply to seed the target DB.")
        return 0

    ensure_schema(target)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    try:
        now = datetime.now()
        actions: list[str] = []
        for position in DEMO_POSITIONS:
            actions.extend(seed_position(conn, position, now=now))
        actions.extend(seed_model_performance(conn, now=now))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print("Seed complete:")
    for action in actions:
        print(f"- {action}")
    print(f"Current production DB was {'seeded intentionally' if args.apply_current else 'not modified'}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
