"""Small Flask security helpers for local-demo and public-demo modes."""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from threading import Lock
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

_RATE_LIMIT_LOCK = Lock()
_RATE_LIMIT_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


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


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def get_allowed_origins(name: str) -> list[str] | str:
    raw = os.getenv(name)
    if raw and raw.strip() == "*":
        return "*"
    return _split_csv(raw, DEFAULT_ALLOWED_ORIGINS)


def debug_endpoints_enabled() -> bool:
    return _env_bool("DEBUG_ENDPOINTS", False) or _env_bool("DEBUG", False)


def _client_identity() -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.remote_addr or "local"


def _rate_limit_key(scope: str) -> str:
    token_hash = ""
    token = _request_token()
    if token:
        token_hash = f":token:{hash(token)}"
    return f"{scope}:{_client_identity()}{token_hash}:{request.path}"


def _check_rate_limit(key: str, *, limit: int, window_seconds: int) -> tuple[bool, int]:
    now = time.monotonic()
    cutoff = now - window_seconds
    with _RATE_LIMIT_LOCK:
        bucket = _RATE_LIMIT_BUCKETS[key]
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            retry_after = max(1, int(window_seconds - (now - bucket[0])))
            return False, retry_after
        bucket.append(now)
        return True, 0


def _rate_limit_response(retry_after: int) -> Response:
    response = jsonify({
        "success": False,
        "status": "error",
        "error": "Too many requests. Please wait and try again.",
        "retry_after_seconds": retry_after,
    })
    response.status_code = 429
    response.headers["Retry-After"] = str(retry_after)
    return response


def request_size_error() -> Response | None:
    max_bytes = _env_int("MAX_JSON_BODY_BYTES", 64 * 1024)
    content_length = request.content_length
    if content_length is not None and content_length > max_bytes:
        return jsonify({
            "success": False,
            "status": "error",
            "error": f"Request body is too large. Max size is {max_bytes} bytes.",
        }), 413
    return None


def rate_limit_error() -> Response | None:
    """Return a 429 response when a client exceeds configured local limits."""
    if not request.path.startswith("/api/"):
        return None
    if not _env_bool("RATE_LIMIT_ENABLED", True):
        return None

    window_seconds = max(1, _env_int("RATE_LIMIT_WINDOW_SECONDS", 60))
    api_limit = max(1, _env_int("API_RATE_LIMIT_PER_MINUTE", 240))
    ok, retry_after = _check_rate_limit(
        _rate_limit_key("api"),
        limit=api_limit,
        window_seconds=window_seconds,
    )
    if not ok:
        return _rate_limit_response(retry_after)

    if request.method in MUTATION_METHODS:
        mutation_limit = max(1, _env_int("MUTATION_RATE_LIMIT_PER_MINUTE", 40))
        ok, retry_after = _check_rate_limit(
            _rate_limit_key("mutation"),
            limit=mutation_limit,
            window_seconds=window_seconds,
        )
        if not ok:
            return _rate_limit_response(retry_after)
    return None


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
