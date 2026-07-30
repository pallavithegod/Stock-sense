"""Startup and dependency checks for the Flask backend."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any, Iterable

from backend.db import connect


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def collect_startup_checks(
    *,
    project_root: Path,
    db_path: Path,
    optional_modules: Iterable[str],
    provider_health: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return lightweight dependency/config diagnostics for status endpoints."""
    env_keys = [
        "FLASK_SECRET_KEY",
        "NEWS_API_KEY",
        "ALPHA_VANTAGE_API_KEY",
        "TWELVE_DATA_API_KEY",
        "FINNHUB_API_KEY",
    ]
    module_status = {name: _module_available(name) for name in optional_modules}

    db_ok = False
    db_error = None
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with connect(db_path) as conn:
            conn.execute("SELECT 1")
        db_ok = True
    except (OSError, Exception) as exc:
        db_error = str(exc)

    runtime_dirs = {}
    for relative in ("data", "cache", "logs", "models"):
        path = project_root / relative
        runtime_dirs[relative] = {
            "exists": path.exists(),
            "writable": os.access(path, os.W_OK) if path.exists() else os.access(project_root, os.W_OK),
        }

    return {
        "environment": {key: bool(os.getenv(key)) for key in env_keys},
        "modules": module_status,
        "database": {
            "path": str(db_path),
            "ok": db_ok,
            "error": db_error,
        },
        "runtime_dirs": runtime_dirs,
        "market_data_providers": provider_health or {},
    }
