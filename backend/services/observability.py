"""Request and job observability helpers for the Flask app and worker."""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from flask import Flask, g, request


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def configure_logging(app: Flask, settings: Any) -> logging.Logger:
    logger = logging.getLogger("stocksense")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    log_dir = Path(settings.project_root) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "stocksense.jsonl"
    handler_key = str(log_path.resolve())
    if not any(getattr(handler, "_stocksense_path", None) == handler_key for handler in logger.handlers):
        handler = RotatingFileHandler(
            log_path,
            maxBytes=settings.log_max_bytes,
            backupCount=settings.log_backup_count,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        handler._stocksense_path = handler_key
        logger.addHandler(handler)

    console_present = any(getattr(handler, "_stocksense_console", False) for handler in logger.handlers)
    if not console_present and not settings.testing:
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter("%(message)s"))
        console._stocksense_console = True
        logger.addHandler(console)

    app.logger.handlers = list(logger.handlers)
    app.logger.setLevel(logger.level)
    app.config["STOCKSENSE_LOG_PATH"] = str(log_path)
    configure_error_reporting(logger)
    return logger


def configure_error_reporting(logger: logging.Logger) -> None:
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        return
    try:
        import sentry_sdk
    except ImportError:
        log_event(logger, "error_reporting_unavailable", provider="sentry", reason="missing_dependency")
        return
    sentry_sdk.init(dsn=dsn, traces_sample_rate=0.05)
    log_event(logger, "error_reporting_enabled", provider="sentry")


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    payload = {"event": event, "timestamp": utc_now(), **fields}
    logger.info(json.dumps(payload, default=str, sort_keys=True))


def install_request_observability(app: Flask, logger: logging.Logger) -> None:
    @app.before_request
    def start_request_timer() -> None:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        g.request_id = request_id
        g.request_started_at = time.perf_counter()

    @app.after_request
    def add_request_observability(response):
        request_id = getattr(g, "request_id", str(uuid.uuid4()))
        started_at = getattr(g, "request_started_at", None)
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2) if started_at else None
        response.headers["X-Request-ID"] = request_id
        log_event(
            logger,
            "http_request",
            request_id=request_id,
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            latency_ms=latency_ms,
            remote_addr=request.remote_addr,
        )
        return response
