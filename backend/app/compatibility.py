"""Compatibility-alias logging for temporary pre-v1 endpoints."""

from __future__ import annotations

from flask import Flask, request


EXACT_ALIASES: dict[str, str] = {
    "/api/dashboard-data": "/api/v1/dashboard",
    "/api/dashboard-data/live": "/api/v1/dashboard",
    "/api/dashboard-data/debug": "/api/v1/dashboard",
    "/api/stocks": "/api/v1/stocks",
    "/api/portfolio": "/api/v1/portfolio",
    "/api/portfolio/state": "/api/v1/portfolio",
    "/api/predictions": "/api/v1/predictions",
    "/api/predictions/intelligence": "/api/v1/predictions",
    "/api/news": "/api/v1/news",
    "/api/news/market": "/api/v1/news",
    "/api/research": "/api/v1/research",
    "/api/system/status": "/api/v1/system/status",
}

PREFIX_ALIASES: tuple[tuple[str, str], ...] = (
    ("/api/stock/", "/api/v1/stocks/"),
    ("/api/news/symbol/", "/api/v1/news"),
)


def _replacement_for(path: str) -> str | None:
    if path in EXACT_ALIASES:
        return EXACT_ALIASES[path]
    for prefix, replacement in PREFIX_ALIASES:
        if path.startswith(prefix):
            suffix = path.removeprefix(prefix)
            return f"{replacement}{suffix}" if replacement.endswith("/") else replacement
    return None


def register_compatibility_deprecation_logging(app: Flask) -> None:
    app.extensions.setdefault("stocksense_compatibility_alias_log", [])

    @app.before_request
    def log_compatibility_alias():
        replacement = _replacement_for(request.path)
        if not replacement:
            return None
        entry = {"alias": request.path, "replacement": replacement}
        app.extensions["stocksense_compatibility_alias_log"].append(entry)
        app.logger.info("Compatibility API alias used: %s -> %s", request.path, replacement)
        return None
