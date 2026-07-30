"""SQLite schema, migrations, and maintenance helpers."""

from backend.db.connection import connect
from backend.db.migrations import apply_migrations, migration_status, validate_schema
from backend.db.retention import cleanup_report
from backend.db.schema import AUXILIARY_DATABASE_OWNERSHIP, LATEST_SCHEMA_VERSION

__all__ = [
    "AUXILIARY_DATABASE_OWNERSHIP",
    "LATEST_SCHEMA_VERSION",
    "apply_migrations",
    "cleanup_report",
    "connect",
    "migration_status",
    "validate_schema",
]
