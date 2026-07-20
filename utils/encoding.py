# -*- coding: utf-8 -*-
"""Central UTF-8 encoding utilities and logging setup.

- Phase 1 runtime bootstrap (executed on import).
- UTF-8 safe text sanitizer (Phase 5).
- Logging configuration helper that ensures all handlers use UTF-8 and
  attaches a filter to remove bad characters (and legacy mojibake).
- Flask helper to enforce UTF-8 charset on JSON responses.

This module is intended as the **single source of truth** for any encoding
related logic in the codebase.  Other modules should import from here and
avoid duplicating encoding code.
"""

import os
import sys
import logging
import re
from typing import Any

# ---------------------------------------------------------------------------
# phase 5 safe string sanitization & legacy cleanup
# ---------------------------------------------------------------------------

# pattern used to strip legacy mojibake sequences that crept in during the
# multi-phase encoding cleanup.  These sequences are valid UTF-8 but are
# visually garbage and confusing when they surface in log output.
_MOJIBAKE_RE = re.compile(r'ÃƒÆ’Ã‚Â¯Ãƒâ€šÃ‚Â¿Ãƒâ€šÃ‚Â½[Oo]?\.?')


def remove_mojibake(s: str) -> str:
    """Strip out any known mojibake artifacts from the provided string."""
    return _MOJIBAKE_RE.sub("", s)


def safe_text(text: Any) -> str:
    """Return a UTF-8-clean string suitable for logging or external output.

    Non-decodable bytes are ignored so that mis-encoded fragments do not
    crash the application or surface as corrupted characters in logs.
    """
    s = str(text)
    s = remove_mojibake(s)
    return s.encode("utf-8", "ignore").decode("utf-8")

# ---------------------------------------------------------------------------
# logging helpers (phase 2 + filter for phase 5)
# ---------------------------------------------------------------------------

class UTF8Filter(logging.Filter):
    """Logging filter that sanitizes message and argument text.

    Attach this filter to any logger or handler to guarantee that the final
    record contains only UTF-8-safe text.  This is the main mechanism that
    prevents badly encoded strings from ever reaching log files or stdout.
    """
    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover
        if record.msg is not None:
            record.msg = safe_text(record.msg)
        if record.args:
            try:
                record.args = tuple(safe_text(a) for a in record.args)
            except Exception:
                record.args = ()
        return True

# ---------------------------------------------------------------------------
# phase 1 runtime bootstrap (import-time side effects)
# ---------------------------------------------------------------------------

def bootstrap_utf8() -> None:
    """Force UTF-8 on standard IO streams and environment.

    This function may be called multiple times safely; it is invoked once in
    ``utils/__init__.py`` so that any import from ``utils`` triggers it early in
    the startup sequence.
    """
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    # make sure early log records are sanitized by attaching the filter
    root = logging.getLogger()
    root.addFilter(UTF8Filter())

# run automatically if module is imported directly
bootstrap_utf8()

# ---------------------------------------------------------------------------
# logging configuration helper
# ---------------------------------------------------------------------------

def configure_logging(log_file: str | None = None, level: int = logging.INFO) -> None:
    """Set up the root logger with UTF-8 handlers and filters.

    ``log_file`` may be a path to a file.  If provided a ``FileHandler`` is
    created with ``encoding='utf-8'``.  A ``StreamHandler`` writing to
    ``sys.stdout`` is always configured.
    """
    handlers: list[logging.Handler] = []

    # stream handler that writes to stdout (already reconfigured)
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(level)
    handlers.append(sh)

    if log_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(level)
        handlers.append(fh)

    fmt = logging.Formatter(
        '%(asctime)s - [%(name)s] - %(levelname)s - %(message)s',
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    for h in handlers:
        h.setFormatter(fmt)
        h.addFilter(UTF8Filter())

    root = logging.getLogger()
    if root.handlers:
        root.handlers.clear()
    logging.basicConfig(level=level, handlers=handlers)
    root.addFilter(UTF8Filter())

# ---------------------------------------------------------------------------
# helpers for Flask JSON responses
# ---------------------------------------------------------------------------

def sanitize_json(obj: Any) -> Any:
    """Recursively sanitize string values in a JSON-serializable object.

    This is intended for use prior to passing data to ``jsonify`` so that any
    external text has been stripped of invalid byte sequences.
    """
    if isinstance(obj, str):
        return safe_text(obj)
    elif isinstance(obj, dict):
        return {sanitize_json(k): sanitize_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, set)):
        return [sanitize_json(v) for v in obj]
    elif hasattr(obj, "__class__") and obj.__class__.__name__ == "deque":
        return [sanitize_json(v) for v in obj]
    elif isinstance(obj, tuple):
        return tuple(sanitize_json(v) for v in obj)
    else:
        return obj


def ensure_json_utf8(app) -> None:
    """Register a Flask after_request handler adding charset header.

    This keeps all existing routes untouched while satisfying phase 6.
    """
    @app.after_request
    def _set_json_charset(response):
        content_type = response.headers.get("Content-Type", "")
        if content_type.startswith("application/json") and "charset" not in content_type:
            response.headers["Content-Type"] = "application/json; charset=utf-8"
        return response
