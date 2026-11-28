"""Gunicorn settings for the production Flask API container/process."""

from __future__ import annotations

import multiprocessing
import os


def resolve_bind(environ: dict[str, str] | None = None) -> str:
    """Return the Gunicorn bind address.

    Port precedence: ``PORT`` (injected by Render and similar platforms, which
    route traffic to it) > ``FLASK_PORT`` (local/Docker) > 5000.
    """
    env = os.environ if environ is None else environ
    host = env.get("FLASK_HOST", "").strip() or "0.0.0.0"
    port = env.get("PORT", "").strip() or env.get("FLASK_PORT", "").strip() or "5000"
    if not port.isdigit() or not 0 < int(port) < 65536:
        raise ValueError("PORT/FLASK_PORT must be an integer between 1 and 65535.")
    return f"{host}:{port}"


bind = resolve_bind()
def resolve_workers(environ: dict[str, str] | None = None, *, cpu_count: int | None = None) -> int:
    """Worker count: GUNICORN_WORKERS > WEB_CONCURRENCY (set by Render) > CPU-based default.

    Each worker is a separate process with its own in-memory caches and rate-limit
    counters, so honoring the platform's sizing avoids exhausting a small instance.
    """
    env = os.environ if environ is None else environ
    for name in ("GUNICORN_WORKERS", "WEB_CONCURRENCY"):
        raw = env.get(name, "").strip()
        if raw:
            if not raw.isdigit() or int(raw) < 1:
                raise ValueError(f"{name} must be a positive integer.")
            return int(raw)
    return max(2, (cpu_count or multiprocessing.cpu_count()) // 2)


workers = resolve_workers()
threads = int(os.getenv("GUNICORN_THREADS", "4"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "60"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
