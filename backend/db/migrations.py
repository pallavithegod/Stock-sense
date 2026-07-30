"""Numbered SQLite migration runner."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.db.connection import connect
from backend.db.schema import LATEST_SCHEMA_VERSION, MIGRATIONS, REQUIRED_COLUMNS, REQUIRED_TABLES


@dataclass(frozen=True)
class MigrationResult:
    db_path: Path
    applied_versions: list[int]
    pending_versions: list[int]
    backup_path: Path | None


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def backup_database(db_path: Path, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{db_path.stem}_{utc_stamp()}.db"
    if db_path.exists():
        shutil.copy2(db_path, backup_path)
    else:
        backup_path.write_bytes(b"")
    return backup_path


def restore_database(*, backup_path: str | Path, target_path: str | Path) -> Path:
    backup = Path(backup_path)
    target = Path(target_path)
    if not backup.exists():
        raise FileNotFoundError(backup)
    target.parent.mkdir(parents=True, exist_ok=True)
    for suffix in ("-wal", "-shm"):
        sidecar = Path(f"{target}{suffix}")
        if sidecar.exists():
            sidecar.unlink()
    shutil.copy2(backup, target)
    return target


def _migration_table_exists(conn) -> bool:
    return bool(conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations'").fetchone())


def _applied_versions(conn) -> set[int]:
    if not _migration_table_exists(conn):
        return set()
    return {int(row["version"]) for row in conn.execute("SELECT version FROM schema_migrations").fetchall()}


def migration_status(db_path: str | Path) -> dict[str, Any]:
    path = Path(db_path)
    if not path.exists():
        return {
            "db_path": str(path),
            "exists": False,
            "latest_schema_version": LATEST_SCHEMA_VERSION,
            "applied_versions": [],
            "pending_versions": [migration.version for migration in MIGRATIONS],
        }
    with connect(path) as conn:
        applied = sorted(_applied_versions(conn))
    pending = [migration.version for migration in MIGRATIONS if migration.version not in applied]
    return {
        "db_path": str(path),
        "exists": True,
        "latest_schema_version": LATEST_SCHEMA_VERSION,
        "applied_versions": applied,
        "pending_versions": pending,
    }


def apply_migrations(
    db_path: str | Path,
    *,
    backup: bool = True,
    backup_dir: str | Path | None = None,
) -> MigrationResult:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existed = path.exists()
    backup_path = None

    with connect(path) as conn:
        applied = _applied_versions(conn)
        pending = [migration for migration in MIGRATIONS if migration.version not in applied]

    if pending and backup and existed:
        backup_path = backup_database(path, Path(backup_dir) if backup_dir else path.parent / "backups")

    applied_now: list[int] = []
    with connect(path) as conn:
        try:
            conn.execute("BEGIN")
            for migration in MIGRATIONS:
                if migration.version in _applied_versions(conn):
                    continue
                migration.apply(conn)
                conn.execute(
                    "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
                    (migration.version, migration.name, datetime.now(timezone.utc).isoformat()),
                )
                applied_now.append(migration.version)
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    status = migration_status(path)
    return MigrationResult(
        db_path=path,
        applied_versions=applied_now,
        pending_versions=status["pending_versions"],
        backup_path=backup_path,
    )


def validate_schema(db_path: str | Path) -> dict[str, Any]:
    path = Path(db_path)
    if not path.exists():
        return {"ok": False, "missing": {"database": [str(path)]}}

    missing: dict[str, list[str]] = {}
    with connect(path) as conn:
        tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'").fetchall()
        }
        absent_tables = sorted(REQUIRED_TABLES - tables)
        if absent_tables:
            missing["tables"] = absent_tables

        for table, columns in REQUIRED_COLUMNS.items():
            if table not in tables:
                continue
            present = {row["name"] for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()}
            absent_columns = sorted(columns - present)
            if absent_columns:
                missing[table] = absent_columns

        quick_check = conn.execute("PRAGMA quick_check").fetchone()
        if quick_check and str(quick_check[0]).lower() != "ok":
            missing["quick_check"] = [str(quick_check[0])]

        fk_rows = conn.execute("PRAGMA foreign_key_check").fetchall()
        if fk_rows:
            missing["foreign_keys"] = [str(tuple(row)) for row in fk_rows]

    return {"ok": not missing, "missing": missing}
