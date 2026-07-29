"""Application-level service container objects."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from backend.domain.dashboard import DashboardService
from backend.domain.market import MarketService
from backend.domain.predictions import PredictionQueryService
from backend.domain.portfolio import PortfolioService
from backend.domain.system import SystemService
from backend.services.market_data import ResilientMarketDataClient


class RuntimeContext:
    """Compatibility context for infrastructure that still expects runtime state."""

    def __init__(self, *, portfolio: PortfolioService, logger: logging.Logger):
        self.db = portfolio.repository
        self.portfolio = portfolio
        self.logger = logger
        self.prediction_history: list[dict[str, Any]] = []
        self.models: dict[str, Any] = {}
        self.cache: dict[str, Any] = {}
        self.cache_ttl = 60

    def compute_portfolio_intelligence(
        self,
        holdings: list[dict[str, Any]],
        preds: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.portfolio.compute_intelligence(holdings)


@dataclass
class AppServices:
    settings: Any
    portfolio: PortfolioService
    market: MarketService
    market_data: ResilientMarketDataClient
    dashboard: DashboardService
    predictions: PredictionQueryService
    system: SystemService
    runtime: RuntimeContext
    logger: logging.Logger
    ai_engine_state: dict[str, Any] = field(default_factory=lambda: {"predictions": {}, "last_update": None, "cognitive_state": {}})
    state_cache: dict[str, Any] = field(default_factory=dict)
    system_cache: dict[str, Any] = field(default_factory=dict)
