from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from backend.db import apply_migrations, cleanup_report, connect, migration_status, validate_schema
from backend.db.migrations import backup_database, restore_database
from backend.db.retention import RetentionPolicy, apply_cleanup
from backend.domain.market import MarketService, MarketUniverse
from backend.domain.portfolio import PortfolioService, SQLitePortfolioRepository


@pytest.fixture()
def db_tmp_path() -> Path:
    path = Path.cwd() / ".pytest-runtime" / "db-tests" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_migrations_create_authoritative_schema_and_hardened_pragmas(db_tmp_path):
    db_path = db_tmp_path / "nexus.db"

    result = apply_migrations(db_path)
    validation = validate_schema(db_path)

    assert result.applied_versions == [1]
    assert result.pending_versions == []
    assert validation["ok"] is True
    with connect(db_path) as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] >= 5000
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"


def test_existing_database_is_backed_up_before_pending_migration(db_tmp_path):
    db_path = db_tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE legacy_marker (id INTEGER PRIMARY KEY)")

    result = apply_migrations(db_path, backup=True, backup_dir=db_tmp_path / "backups")

    assert result.backup_path is not None
    assert result.backup_path.exists()
    with sqlite3.connect(result.backup_path) as conn:
        assert conn.execute("SELECT name FROM sqlite_master WHERE name = 'legacy_marker'").fetchone()


def test_constraints_allow_fractional_portfolio_and_reject_invalid_rows(db_tmp_path):
    db_path = db_tmp_path / "portfolio.db"
    repository = SQLitePortfolioRepository(db_path)
    service = PortfolioService(repository=repository, market_service=MarketService(MarketUniverse()))

    service.create_position({"symbol": "INFY", "quantity": 1.5, "avg_price": 100, "purchase_date": None})

    assert service.list_positions()[0]["quantity"] == 1.5
    with connect(db_path) as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO portfolio (symbol, quantity, avg_price, added_date) VALUES ('BAD', -1, 10, '2026-07-30T00:00:00+00:00')"
            )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO portfolio_transactions (symbol, side, quantity, price, trade_date, created_at) VALUES ('BAD', 'HOLD', 1, 10, '2026-07-30T00:00:00+00:00', '2026-07-30T00:00:00+00:00')"
            )


def test_prediction_idempotency_and_json_metadata_constraints(db_tmp_path):
    db_path = db_tmp_path / "predictions.db"
    apply_migrations(db_path)
    payload = {
        "fingerprint": "fp-1",
        "symbol": "INFY",
        "horizon": "6m",
        "as_of": "2026-07-30T00:00:00+00:00",
        "current_price": 100,
        "target_price": 110,
        "predicted_price": 110,
        "signal": "BUY",
        "confidence": 70,
        "source_type": "heuristic",
        "provider": "unit_test",
        "data_quality": "fixture",
        "metadata_json": json.dumps({"model": "none"}),
        "models_used": json.dumps(["heuristic"]),
        "timestamp": "2026-07-30T00:00:00+00:00",
    }

    with connect(db_path) as conn:
        columns = ", ".join(payload)
        placeholders = ", ".join("?" for _ in payload)
        conn.execute(f"INSERT INTO predictions ({columns}) VALUES ({placeholders})", tuple(payload.values()))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(f"INSERT INTO predictions ({columns}) VALUES ({placeholders})", tuple(payload.values()))
        conn.execute(
            """
            INSERT INTO prediction_events (idempotency_key, prediction_fingerprint, event_type, payload_json)
            VALUES ('event-1', 'fp-1', 'created', '{}')
            """
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO prediction_events (idempotency_key, prediction_fingerprint, event_type, payload_json)
                VALUES ('event-1', 'fp-1', 'created', '{}')
                """
            )


def test_cleanup_report_is_dry_run_and_cleanup_requires_confirmation(db_tmp_path):
    db_path = db_tmp_path / "cleanup.db"
    apply_migrations(db_path)
    with connect(db_path) as conn:
        for index in range(3):
            conn.execute(
                """
                INSERT INTO predictions
                (fingerprint, symbol, horizon, as_of, source_type, provider, data_quality, metadata_json, models_used, timestamp, created_at)
                VALUES (?, 'INFY', '6m', ?, 'heuristic', 'unit_test', 'fixture', '{}', '[]', ?, ?)
                """,
                (
                    f"fp-{index}",
                    f"2026-07-0{index + 1}T00:00:00+00:00",
                    f"2026-07-0{index + 1}T00:00:00+00:00",
                    f"2026-07-0{index + 1}T00:00:00+00:00",
                ),
            )

    report = cleanup_report(db_path, policy=RetentionPolicy(max_raw_predictions=1))

    assert report["estimated_reclaimed_rows"] == 2
    with connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0] == 3
    with pytest.raises(ValueError):
        apply_cleanup(db_path, confirmation="", policy=RetentionPolicy(max_raw_predictions=1))

    applied = apply_cleanup(
        db_path,
        confirmation="APPLY_SQLITE_CLEANUP",
        backup_dir=db_tmp_path / "backups",
        policy=RetentionPolicy(max_raw_predictions=1),
    )

    assert Path(applied["backup_path"]).exists()
    with connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM prediction_archive").fetchone()[0] == 2


def test_backup_can_restore_database(db_tmp_path):
    db_path = db_tmp_path / "restore.db"
    apply_migrations(db_path)
    backup_path = backup_database(db_path, db_tmp_path / "backups")
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO dynamic_symbols (symbol, name, sector, last_updated) VALUES ('INFY', 'Infosys', 'Tech', '2026-07-30T00:00:00+00:00')"
        )

    restore_database(backup_path=backup_path, target_path=db_path)

    with connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM dynamic_symbols").fetchone()[0] == 0


def test_concurrent_reads_work_with_wal(db_tmp_path):
    db_path = db_tmp_path / "concurrent.db"
    apply_migrations(db_path)
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO dynamic_symbols (symbol, name, sector, last_updated) VALUES ('INFY', 'Infosys', 'Tech', '2026-07-30T00:00:00+00:00')"
        )

    def read_count() -> int:
        with connect(db_path) as conn:
            return int(conn.execute("SELECT COUNT(*) FROM dynamic_symbols").fetchone()[0])

    with ThreadPoolExecutor(max_workers=4) as executor:
        assert list(executor.map(lambda _: read_count(), range(8))) == [1] * 8


def test_maintenance_script_check_and_status_use_migrations(db_tmp_path):
    db_path = db_tmp_path / "script.db"
    check = subprocess.run(
        [sys.executable, "scripts/sqlite_maintenance.py", "check", "--db", str(db_path)],
        cwd=Path.cwd(),
        check=True,
        capture_output=True,
        text=True,
    )
    status = subprocess.run(
        [sys.executable, "scripts/sqlite_maintenance.py", "status", "--db", str(db_path)],
        cwd=Path.cwd(),
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(check.stdout)["status"] == "ok"
    assert migration_status(db_path)["pending_versions"] == []
    assert json.loads(status.stdout)["applied_versions"] == [1]
