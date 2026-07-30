"""SQLite retention and cleanup planning."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.db.connection import connect
from backend.db.migrations import backup_database


@dataclass(frozen=True)
class RetentionPolicy:
    max_raw_predictions: int = 1000
    max_model_performance_rows: int = 500
    max_volatility_logs: int = 2000


def _table_count(conn, table: str) -> int:
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone():
        return 0
    return int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])


def _ids_after_limit(conn, table: str, *, order_column: str, keep: int) -> list[int]:
    if _table_count(conn, table) <= keep:
        return []
    rows = conn.execute(
        f"""
        SELECT id
        FROM "{table}"
        ORDER BY "{order_column}" DESC, id DESC
        LIMIT -1 OFFSET ?
        """,
        (keep,),
    ).fetchall()
    return [int(row["id"]) for row in rows]


def cleanup_report(
    db_path: str | Path,
    *,
    policy: RetentionPolicy | None = None,
    include_candidate_ids: bool = True,
) -> dict[str, Any]:
    path = Path(db_path)
    policy = policy or RetentionPolicy()
    if not path.exists():
        return {"db_path": str(path), "exists": False, "would_delete": {}, "row_counts": {}, "estimated_reclaimed_rows": 0}

    with connect(path) as conn:
        row_counts = {
            "predictions": _table_count(conn, "predictions"),
            "prediction_events": _table_count(conn, "prediction_events"),
            "model_performance": _table_count(conn, "model_performance"),
            "volatility_logs": _table_count(conn, "volatility_logs"),
        }
        duplicate_prediction_ids = [
            int(row["id"])
            for row in conn.execute(
                """
                SELECT id
                FROM (
                    SELECT id, ROW_NUMBER() OVER (PARTITION BY fingerprint ORDER BY id ASC) AS row_number
                    FROM predictions
                    WHERE fingerprint IS NOT NULL
                )
                WHERE row_number > 1
                """
            ).fetchall()
        ]
        old_prediction_ids = _ids_after_limit(conn, "predictions", order_column="created_at", keep=policy.max_raw_predictions)
        old_model_performance_ids = _ids_after_limit(conn, "model_performance", order_column="updated_at", keep=policy.max_model_performance_rows)
        old_volatility_log_ids = _ids_after_limit(conn, "volatility_logs", order_column="created_at", keep=policy.max_volatility_logs)
        orphan_realized_gain_ids = [
            int(row["id"])
            for row in conn.execute(
                """
                SELECT gains.id
                FROM portfolio_realized_gains AS gains
                LEFT JOIN portfolio_lots AS lots ON lots.id = gains.lot_id
                LEFT JOIN portfolio_transactions AS txns ON txns.id = gains.sell_txn_id
                WHERE lots.id IS NULL OR txns.id IS NULL
                """
            ).fetchall()
        ]

    would_delete = {
        "duplicate_predictions": duplicate_prediction_ids,
        "old_raw_predictions": old_prediction_ids,
        "old_model_performance": old_model_performance_ids,
        "old_volatility_logs": old_volatility_log_ids,
        "orphan_realized_gains": orphan_realized_gain_ids,
    }
    report = {
        "db_path": str(path),
        "exists": True,
        "row_counts": row_counts,
        "would_delete": {key: len(value) for key, value in would_delete.items()},
        "estimated_reclaimed_rows": sum(len(value) for value in would_delete.values()),
        "requires_confirmation": True,
    }
    if include_candidate_ids:
        report["candidate_ids"] = would_delete
    return report


def apply_cleanup(
    db_path: str | Path,
    *,
    confirmation: str,
    backup_dir: str | Path | None = None,
    policy: RetentionPolicy | None = None,
) -> dict[str, Any]:
    path = Path(db_path)
    report = cleanup_report(path, policy=policy, include_candidate_ids=True)
    expected = "APPLY_SQLITE_CLEANUP"
    if confirmation != expected:
        raise ValueError(f"Cleanup requires confirmation token {expected!r}")
    if not report.get("exists"):
        raise FileNotFoundError(path)

    backup_path = backup_database(path, Path(backup_dir) if backup_dir else path.parent / "backups")
    now = datetime.now(timezone.utc).isoformat()
    candidates = report["candidate_ids"]
    with connect(path) as conn:
        try:
            conn.execute("BEGIN")
            for table, ids in (
                ("predictions", candidates["duplicate_predictions"] + candidates["old_raw_predictions"]),
                ("model_performance", candidates["old_model_performance"]),
                ("volatility_logs", candidates["old_volatility_logs"]),
                ("portfolio_realized_gains", candidates["orphan_realized_gains"]),
            ):
                for row_id in sorted(set(ids)):
                    row = conn.execute(f'SELECT * FROM "{table}" WHERE id = ?', (row_id,)).fetchone()
                    if row is None:
                        continue
                    archive_table = "model_performance_archive" if table == "model_performance" else "prediction_archive"
                    conn.execute(
                        f'INSERT INTO "{archive_table}" (source_table, source_id, payload_json, archived_at) VALUES (?, ?, ?, ?)'
                        if archive_table == "prediction_archive"
                        else f'INSERT INTO "{archive_table}" (source_id, payload_json, archived_at) VALUES (?, ?, ?)',
                        (table, row_id, json.dumps(dict(row), sort_keys=True), now)
                        if archive_table == "prediction_archive"
                        else (row_id, json.dumps(dict(row), sort_keys=True), now),
                    )
                    conn.execute(f'DELETE FROM "{table}" WHERE id = ?', (row_id,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return {**report, "backup_path": str(backup_path), "applied": True}
