"""Market, search, and stock route wiring."""

from __future__ import annotations

from typing import Mapping

from flask import Blueprint


def create_market_blueprint(*, handlers: Mapping[str, object]) -> Blueprint:
    blueprint = Blueprint("market", __name__)

    route_specs = [
        ("/api/search", "api_search", ["GET"]),
        ("/api/search/comprehensive", "comprehensive_search", ["GET"]),
        ("/api/market_universe", "market_debug", ["GET"]),
        ("/api/stocks", "get_stocks", ["GET"]),
        ("/api/user_tickers", "save_user_tickers", ["POST"]),
        ("/api/stock/<symbol>", "get_stock_prediction", ["GET"]),
        ("/api/stock/<symbol>/history", "api_stock_history_chart", ["GET"]),
        ("/api/stock/analysis/<symbol>", "stock_analysis", ["GET"]),
        ("/api/indicators/<symbol>", "get_technical_indicators", ["GET"]),
        ("/api/historical/<symbol>", "get_historical_data", ["GET"]),
        ("/api/compare", "compare_stocks", ["POST"]),
        ("/api/analytics/market-trends", "api_market_trends_chart", ["GET"]),
    ]

    for rule, handler_name, methods in route_specs:
        blueprint.add_url_rule(
            rule,
            endpoint=handler_name,
            view_func=handlers[handler_name],
            methods=methods,
        )

    return blueprint
