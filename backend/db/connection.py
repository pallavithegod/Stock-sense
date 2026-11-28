"""Hardened SQLite connection helpers."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        result = super().__exit__(exc_type, exc_value, traceback)
        self.close()
        return result


def connect(db_path: str | Path, *, timeout: float = 5.0) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=timeout, detect_types=sqlite3.PARSE_DECLTYPES, factory=ClosingConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(f"PRAGMA busy_timeout={int(timeout * 1000)}")
    if path.name != ":memory:":
        _ensure_wal(conn, timeout=timeout)
    return conn


def _ensure_wal(conn: sqlite3.Connection, *, timeout: float) -> None:
    """Put the database in WAL mode without failing when another process is writing.

    Switching journal mode needs an exclusive lock and returns "database is
    locked" immediately (the busy timeout does not apply), so concurrent
    startups must not all try it. WAL is persistent: once one connection has
    switched, later connections only read the mode.
    """
    deadline = time.monotonic() + timeout
    while True:
        try:
            if str(conn.execute("PRAGMA journal_mode").fetchone()[0]).lower() == "wal":
                return
            conn.execute("PRAGMA journal_mode=WAL")
            return
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc).lower() or time.monotonic() >= deadline:
                raise
            time.sleep(0.02)
