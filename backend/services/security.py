"""Small Flask security helpers for local-demo and public-demo modes."""

from __future__ import annotations

import hashlib
import hmac
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
    "/api/v1/portfolio",
    "/api/v1/predictions/execute",
    "/api/v1/predictions/feedback",
    "/api/v1/predictions/governance-decision",
)

_RATE_LIMIT_LOCK = Lock()
_RATE_LIMIT_BUCKETS: dict[str, deque[float]] = defaultdict(deque)

_INSECURE_SECRET_VALUES = {
    "",
    "change-me",
    "change-me-local-dev-secret",
    "changeme",
    "replace-me",
    "replace_with_a_long_random_secret",
}


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


def is_production_environment() -> bool:
    return os.getenv("APP_ENV", "development").strip().lower() == "production"


def validate_security_configuration() -> None:
    """Reject unsafe secrets when the process is explicitly in production."""
    if not is_production_environment():
        return

    secret = os.getenv("FLASK_SECRET_KEY", "").strip()
    if secret.lower() in _INSECURE_SECRET_VALUES or len(secret) < 32:
        raise RuntimeError(
            "FLASK_SECRET_KEY must be a non-placeholder value of at least "
            "32 characters when APP_ENV=production."
        )

    if _env_bool("REQUIRE_MUTATION_TOKEN", False) and not _env_bool("REQUIRE_AUTH", False):
        token = os.getenv("DEMO_WRITE_TOKEN", "").strip()
        if len(token) < 24:
            raise RuntimeError(
                "DEMO_WRITE_TOKEN must contain at least 24 characters when "
                "write protection is enabled in production."
            )


def _client_identity() -> str:
    # ProxyFix, when explicitly enabled by the application, safely resolves
    # trusted forwarding headers before this helper runs.
    return request.remote_addr or "local"


def _rate_limit_key(scope: str) -> str:
    token_hash = ""
    token = _request_token()
    if token:
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
        token_hash = f":token:{digest}"
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
    if _env_bool("REQUIRE_AUTH", False):
        return None

    expected = os.getenv("DEMO_WRITE_TOKEN", "").strip()
    supplied = _request_token()
    if expected and supplied and hmac.compare_digest(supplied, expected):
        return None

    return jsonify(
        {
            "success": False,
            "status": "error",
            "error": "Write access is protected in this demo environment.",
        }
    ), 403


def install_security_headers(app, settings=None) -> None:
    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        csp = getattr(settings, "content_security_policy", "") if settings else ""
        if csp:
            response.headers.setdefault("Content-Security-Policy", csp)
        if request.path.startswith("/api/") or request.path.startswith("/health/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response


def clear_rate_limit_state() -> None:
    """Clear process-local limiter state between isolated tests."""
    with _RATE_LIMIT_LOCK:
        _RATE_LIMIT_BUCKETS.clear()
