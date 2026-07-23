"""Market data helpers used by the legacy Flask app and future API layers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def configure_yfinance_cache(yfinance_module: Any, *, cache_dir: str | os.PathLike[str] = "cache/yfinance") -> Path:
    """Ensure yfinance can create its timezone cache on locked-down Windows setups."""
    path = Path(cache_dir)
    path.mkdir(parents=True, exist_ok=True)
    if hasattr(yfinance_module, "set_tz_cache_location"):
        yfinance_module.set_tz_cache_location(str(path.resolve()))
    return path


def to_yfinance_symbol(symbol: str, *, default_exchange: str = ".NS") -> str:
    cleaned = str(symbol or "").upper().strip()
    if not cleaned:
        return cleaned
    if cleaned.endswith((".NS", ".BO")) or cleaned.startswith("^"):
        return cleaned
    return f"{cleaned}{default_exchange}"
