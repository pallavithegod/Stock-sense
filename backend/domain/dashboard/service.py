"""Dashboard composition service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.domain.market import MarketService
from backend.domain.portfolio import PortfolioService
from backend.services.supabase_auth import AuthenticatedUser


class DashboardService:
    def __init__(self, *, market_service: MarketService, portfolio_service: PortfolioService):
        self.market_service = market_service
        self.portfolio_service = portfolio_service

    def snapshot(
        self,
        principal: AuthenticatedUser | None = None,
        *,
        include_portfolio: bool = True,
    ) -> dict[str, Any]:
        holdings = self.portfolio_service.list_positions(principal) if include_portfolio else []
        intelligence = self.portfolio_service.compute_intelligence(holdings)
        index_response = self.market_service.market_data.indices(allow_stale=True) if self.market_service.market_data else None
        indices = index_response.data if index_response and isinstance(index_response.data, list) else []
        stocks = self.market_service.dashboard_stocks(limit=8)
        quality_states = [row.get("data_quality") for row in stocks]
        if index_response:
            quality_states.append(index_response.quality_status)
        data_quality = "live" if any(state == "live" for state in quality_states) else "cached_stale" if any(state == "cached_stale" for state in quality_states) else "unavailable"
        return {
            "success": True,
            "live_indices": indices,
            "top_stocks": stocks,
            "positions": intelligence["positions"],
            "portfolio": intelligence,
            "data_quality": data_quality,
            "provider": index_response.provider if index_response else None,
            "stale": index_response.stale if index_response else True,
            "synthetic": index_response.synthetic if index_response else False,
            "demo": index_response.demo if index_response else False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
