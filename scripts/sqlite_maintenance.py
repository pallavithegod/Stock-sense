#!/usr/bin/env python3
"""SQLite maintenance helpers for local/demo mode."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = PROJECT_ROOT / "data" / "stocksense.db"
DEFAULT_EXPORT_DIR = PROJECT_ROOT / "data" / "exports"
DEFAULT_BACKUP_DIR = PROJECT_ROOT / "data" / "backups"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.db import apply_migrations, cleanup_report, connect, migration_status, validate_schema
from backend.db.migrations import backup_database
from backend.db.retention import apply_cleanup


def check_schema(db_path: Path) -> None:
    result = apply_migrations(db_path, backup=db_path.exists(), backup_dir=db_path.parent / "backups")
    validation = validate_schema(db_path)
    missing = dict(validation["missing"])
    foreign_key_issues = missing.pop("foreign_keys", [])
    if missing:
        raise SystemExit(f"SQLite schema validation failed: {missing}")
    cleanup = cleanup_report(db_path, include_candidate_ids=False) if foreign_key_issues else None
    payload = {
        "status": "needs_cleanup_confirmation" if foreign_key_issues else "ok",
        "db_path": str(db_path),
        "applied_versions": result.applied_versions,
        "pending_versions": result.pending_versions,
        "backup_path": str(result.backup_path) if result.backup_path else None,
        "foreign_key_issues": foreign_key_issues,
        "cleanup_report": cleanup,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


def backup_db(db_path: Path, output_dir: Path) -> Path:
    backup_path = backup_database(db_path, output_dir)
    print(f"OK: Backup written to {backup_path}")
    return backup_path


def export_json(db_path: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_path = output_dir / f"stocksense_export_{stamp}.json"
    payload = {}
    with connect(db_path) as conn:
        tables = [
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        ]
        for table in tables:
            rows = conn.execute(f'SELECT * FROM "{table}"').fetchall()
            payload[table] = [dict(row) for row in rows]
    export_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"OK: JSON export written to {export_path}")
    return export_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Maintain the local SQLite demo database.")
    parser.add_argument(
        "action",
        choices=["check", "status", "backup", "export", "cleanup-report", "cleanup-apply", "vacuum"],
        help="check migrates+validates, status lists migrations, backup copies the DB, export writes JSON, cleanup-report is dry-run only",
    )
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Path to SQLite DB")
    parser.add_argument("--out", default=None, help="Output directory for backup/export")
    parser.add_argument("--confirm", default="", help="Required token for cleanup-apply: APPLY_SQLITE_CLEANUP")
    args = parser.parse_args()

    db_path = Path(args.db).resolve()
    allowed_without_db = {"check", "status", "cleanup-report"}
    if not db_path.exists() and args.action not in allowed_without_db:
        raise SystemExit(f"Database not found: {db_path}")

    if args.action == "check":
        check_schema(db_path)
    elif args.action == "status":
        print(json.dumps(migration_status(db_path), indent=2, sort_keys=True))
    elif args.action == "backup":
        backup_db(db_path, Path(args.out).resolve() if args.out else DEFAULT_BACKUP_DIR)
    elif args.action == "export":
        export_json(db_path, Path(args.out).resolve() if args.out else DEFAULT_EXPORT_DIR)
    elif args.action == "cleanup-report":
        print(json.dumps(cleanup_report(db_path, include_candidate_ids=False), indent=2, sort_keys=True))
    elif args.action == "cleanup-apply":
        report = cleanup_report(db_path, include_candidate_ids=False)
        if not report.get("exists"):
            raise SystemExit(f"Database not found: {db_path}")
        print(json.dumps(report, indent=2, sort_keys=True))
        result = apply_cleanup(
            db_path,
            confirmation=args.confirm,
            backup_dir=Path(args.out).resolve() if args.out else DEFAULT_BACKUP_DIR,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
    elif args.action == "vacuum":
        backup_path = backup_database(db_path, Path(args.out).resolve() if args.out else DEFAULT_BACKUP_DIR)
        with connect(db_path) as conn:
            conn.execute("VACUUM")
        print(json.dumps({"status": "ok", "backup_path": str(backup_path), "vacuumed_at": datetime.now(timezone.utc).isoformat()}))


if __name__ == "__main__":
    main()
