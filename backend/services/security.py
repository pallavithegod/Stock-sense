"""Small Flask security helpers for local-demo and public-demo modes."""

from __future__ import annotations

import os
from typing import Iterable

from flask import Response, jsonify, request


DEFAULT_ALLOWED_ORIGINS = (
    "http://127.0.0.1:5000",
    "http://localhost:5000",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
)

MUTATION_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

PROTECTED_MUTATION_PREFIXES = (
    "/api/portfolio",
    "/api/execute-prediction",
    "/api/feedback",
    "/api/governance-decision",
    "/api/user_tickers",
)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _split_csv(raw: str | None, fallback: Iterable[str]) -> list[str]:
    if not raw:
        return list(fallback)
    values = [item.strip() for item in raw.split(",") if item.strip()]
    return values or list(fallback)


def get_allowed_origins(name: str) -> list[str] | str:
    raw = os.getenv(name)
    if raw and raw.strip() == "*":
        return "*"
    return _split_csv(raw, DEFAULT_ALLOWED_ORIGINS)


def debug_endpoints_enabled() -> bool:
    return _env_bool("DEBUG_ENDPOINTS", False) or _env_bool("DEBUG", False)


def _request_token() -> str:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.headers.get("X-Demo-Token", "").strip()


def mutation_guard_error() -> Response | None:
    """Return a 403 response when public-demo write protection blocks a request."""

    if request.method not in MUTATION_METHODS:
        return None
    if not any(request.path.startswith(prefix) for prefix in PROTECTED_MUTATION_PREFIXES):
        return None
    if not _env_bool("REQUIRE_MUTATION_TOKEN", False):
        return None

    expected = os.getenv("DEMO_WRITE_TOKEN", "").strip()
    if expected and _request_token() == expected:
        return None

    return jsonify(
        {
            "success": False,
            "status": "error",
            "error": "Write access is protected in this demo environment.",
        }
    ), 403


def install_security_headers(app) -> None:
    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response
