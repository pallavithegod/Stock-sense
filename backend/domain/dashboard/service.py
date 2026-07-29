"""Dashboard composition service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.domain.market import MarketService
from backend.domain.portfolio import PortfolioService


class DashboardService:
    def __init__(self, *, market_service: MarketService, portfolio_service: PortfolioService):
        self.market_service = market_service
        self.portfolio_service = portfolio_service

    def snapshot(self) -> dict[str, Any]:
        holdings = self.portfolio_service.list_positions()
        intelligence = self.portfolio_service.compute_intelligence(holdings)
        stocks = self.market_service.list_stocks(limit=8)
        return {
            "success": True,
            "live_indices": [],
            "top_stocks": stocks,
            "positions": intelligence["positions"],
            "portfolio": intelligence,
            "data_quality": "unavailable",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

