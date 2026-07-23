#!/usr/bin/env python3
"""SQLite maintenance helpers for local/demo mode."""

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = PROJECT_ROOT / "data" / "nexus.db"
DEFAULT_EXPORT_DIR = PROJECT_ROOT / "data" / "exports"
DEFAULT_BACKUP_DIR = PROJECT_ROOT / "data" / "backups"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import DatabaseManager


def check_schema(db_path: Path) -> None:
    manager = DatabaseManager(str(db_path))
    manager.validate_schema()
    print(f"OK: SQLite schema validated at {db_path}")


def backup_db(db_path: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = output_dir / f"nexus_{stamp}.db"
    with sqlite3.connect(db_path) as source:
        with sqlite3.connect(backup_path) as target:
            source.backup(target)
    print(f"OK: Backup written to {backup_path}")
    return backup_path


def export_json(db_path: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_path = output_dir / f"nexus_export_{stamp}.json"
    payload = {}
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
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
        choices=["check", "backup", "export"],
        help="check validates schema, backup copies the DB, export writes table data as JSON",
    )
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Path to SQLite DB")
    parser.add_argument("--out", default=None, help="Output directory for backup/export")
    args = parser.parse_args()

    db_path = Path(args.db).resolve()
    if not db_path.exists() and args.action != "check":
        raise SystemExit(f"Database not found: {db_path}")

    if args.action == "check":
        check_schema(db_path)
    elif args.action == "backup":
        backup_db(db_path, Path(args.out).resolve() if args.out else DEFAULT_BACKUP_DIR)
    elif args.action == "export":
        export_json(db_path, Path(args.out).resolve() if args.out else DEFAULT_EXPORT_DIR)


if __name__ == "__main__":
    main()
