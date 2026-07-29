"""News, alerts, and research read-model helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable


NormalizeSymbol = Callable[[Any], str | None]


class NewsService:
    """Small deterministic news service for the factory path.

    Live providers are intentionally deferred to the market/news reliability
    phases. These methods keep response shapes stable without pretending that
    unavailable provider data is live news.
    """

    def __init__(self, *, normalize_symbol: NormalizeSymbol):
        self._normalize_symbol = normalize_symbol

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def market_news(self) -> dict[str, Any]:
        return {
            "success": True,
            "articles": [],
            "data": [],
            "source": "unavailable",
            "data_quality": "unavailable",
            "timestamp": self._timestamp(),
        }

    def symbol_news(self, symbol: str) -> dict[str, Any]:
        return {
            "success": True,
            "symbol": self._normalize_symbol(symbol),
            "articles": [],
            "data": [],
            "source": "unavailable",
            "data_quality": "unavailable",
            "timestamp": self._timestamp(),
        }

    def alerts(self) -> dict[str, Any]:
        return {
            "success": True,
            "active_alerts": 0,
            "triggered_today": 0,
            "alerts": [],
            "data": [],
            "timestamp": self._timestamp(),
        }

    def research(self) -> dict[str, Any]:
        return {
            "success": True,
            "researchreports": [],
            "aiinsights": [],
            "model_performance": {},
            "live_stats": {},
            "data": [],
            "message": "Research providers are unavailable in the lightweight factory runtime.",
            "data_quality": "unavailable",
            "timestamp": self._timestamp(),
        }

