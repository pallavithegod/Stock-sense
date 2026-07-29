"""Validated application settings for the StockSense Flask app factory."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


DEFAULT_ALLOWED_ORIGINS = (
    "http://127.0.0.1:5000",
    "http://localhost:5000",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
)


def _env_bool(source: Mapping[str, str], name: str, default: bool = False) -> bool:
    value = source.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(source: Mapping[str, str], name: str, default: int) -> int:
    try:
        return int(source.get(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_csv(source: Mapping[str, str], name: str, default: tuple[str, ...]) -> list[str] | str:
    raw = source.get(name)
    if not raw:
        return list(default)
    if raw.strip() == "*":
        return "*"
    values = [item.strip() for item in raw.split(",") if item.strip()]
    return values or list(default)


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)


def _socketio_mode(source: Mapping[str, str]) -> str:
    mode = source.get("SOCKETIO_ASYNC_MODE", "threading").strip().lower()
    if mode == "eventlet":
        return "threading"
    return mode or "threading"


@dataclass(frozen=True)
class Settings:
    project_root: Path
    app_env: str
    testing: bool
    debug: bool
    debug_endpoints: bool
    secret_key: str
    cors_allowed_origins: list[str] | str
    socketio_cors_allowed_origins: list[str] | str
    socketio_async_mode: str
    trust_proxy_headers: bool
    trusted_proxy_count: int
    db_path: Path
    market_db_path: Path
    adaptive_db_path: Path
    audit_log_path: Path
    disable_startup_network: bool
    enable_workers: bool
    open_browser: bool
    cache_timeout: int
    provider_timeout_seconds: int
    log_max_bytes: int
    log_backup_count: int
    host: str
    port: int

    @classmethod
    def from_env(
        cls,
        overrides: Mapping[str, object] | None = None,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> "Settings":
        if environ is None:
            _load_dotenv_if_available()
        env = dict(environ or os.environ)
        root = Path(env.get("STOCKSENSE_PROJECT_ROOT", Path.cwd())).resolve()

        values: dict[str, object] = {
            "project_root": root,
            "app_env": env.get("APP_ENV", "development").strip().lower(),
            "testing": _env_bool(env, "TESTING", False),
            "debug": _env_bool(env, "DEBUG", False),
            "debug_endpoints": _env_bool(env, "DEBUG_ENDPOINTS", False),
            "secret_key": env.get("FLASK_SECRET_KEY", "change-me-local-dev-secret"),
            "cors_allowed_origins": _env_csv(env, "CORS_ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS),
            "socketio_cors_allowed_origins": _env_csv(
                env,
                "SOCKETIO_CORS_ALLOWED_ORIGINS",
                DEFAULT_ALLOWED_ORIGINS,
            ),
            "socketio_async_mode": _socketio_mode(env),
            "trust_proxy_headers": _env_bool(env, "TRUST_PROXY_HEADERS", False),
            "trusted_proxy_count": max(1, _env_int(env, "TRUSTED_PROXY_COUNT", 1)),
            "db_path": Path(env.get("STOCKSENSE_DB_PATH", root / "data" / "nexus.db")),
            "market_db_path": Path(env.get("STOCKSENSE_MARKET_DB_PATH", root / "data" / "market_intelligence.db")),
            "adaptive_db_path": Path(env.get("STOCKSENSE_ADAPTIVE_DB_PATH", root / "data" / "adaptive_thresholds.db")),
            "audit_log_path": Path(env.get("STOCKSENSE_AUDIT_LOG_PATH", root / "data" / "prediction_audit.jsonl")),
            "disable_startup_network": _env_bool(env, "DISABLE_STARTUP_NETWORK", False),
            "enable_workers": _env_bool(env, "ENABLE_WORKERS", False),
            "open_browser": _env_bool(env, "OPEN_BROWSER", False),
            "cache_timeout": max(1, _env_int(env, "CACHE_TIMEOUT", 60)),
            "provider_timeout_seconds": max(1, _env_int(env, "PROVIDER_TIMEOUT_SECONDS", 10)),
            "log_max_bytes": max(1024 * 1024, _env_int(env, "STOCKSENSE_LOG_MAX_BYTES", 5 * 1024 * 1024)),
            "log_backup_count": max(1, _env_int(env, "STOCKSENSE_LOG_BACKUP_COUNT", 3)),
            "host": env.get("FLASK_HOST", "0.0.0.0"),
            "port": _env_int(env, "FLASK_PORT", 5000),
        }
        values.update(overrides or {})
        return cls(**values)

    def resolved_db_path(self) -> Path:
        return self.db_path if self.db_path.is_absolute() else self.project_root / self.db_path
