"""Portfolio route wiring."""

from __future__ import annotations

from typing import Mapping

from flask import Blueprint


def create_portfolio_blueprint(*, handlers: Mapping[str, object]) -> Blueprint:
    blueprint = Blueprint("portfolio", __name__)

    route_specs = [
        ("/api/portfolio", "create_portfolio", ["POST"]),
        ("/api/portfolio/add", "create_portfolio_legacy", ["POST"]),
        ("/api/portfolio/state", "api_portfolio_state", ["GET"]),
        ("/api/portfolio", "api_get_portfolio", ["GET"]),
        ("/api/portfolio/lots", "api_get_portfolio_lots", ["GET"]),
        ("/api/portfolio/lots/<int:lot_id>", "api_update_portfolio_lot", ["PUT"]),
        ("/api/portfolio/lots/<int:lot_id>", "api_delete_portfolio_lot", ["DELETE"]),
        ("/api/portfolio/realized-gains", "api_get_realized_gains", ["GET"]),
        ("/api/portfolio/<symbol>", "api_delete_portfolio", ["DELETE"]),
        ("/api/portfolio/<symbol>", "api_modify_portfolio", ["PUT"]),
        ("/api/portfolio/sell", "api_sell_portfolio", ["POST"]),
        ("/api/portfolio/sell/simulate", "api_sell_simulation", ["POST"]),
        ("/api/portfolio/tax-summary", "api_portfolio_tax_summary", ["GET"]),
        ("/api/portfolio/ltcg-alerts", "api_portfolio_ltcg_alerts", ["GET"]),
        ("/api/portfolio/lot-insights", "api_portfolio_lot_insights", ["GET"]),
        ("/api/portfolio/forecast", "api_portfolio_forecast", ["GET"]),
        ("/api/portfolio/survival", "api_portfolio_survival", ["GET"]),
        ("/api/portfolio/intelligence-suite", "api_portfolio_intelligence_suite", ["GET"]),
        ("/api/portfolio/backtesting", "api_portfolio_backtesting", ["GET"]),
        ("/api/portfolio/drift", "api_portfolio_drift", ["GET"]),
        ("/api/portfolio/governance", "api_portfolio_governance", ["GET"]),
        ("/api/portfolio/explainability", "api_portfolio_explainability", ["GET"]),
        ("/api/portfolio/scorecard", "api_portfolio_scorecard", ["GET"]),
        ("/api/portfolio/allocation", "api_portfolio_allocation_chart", ["GET"]),
    ]

    for rule, handler_name, methods in route_specs:
        blueprint.add_url_rule(
            rule,
            endpoint=handler_name,
            view_func=handlers[handler_name],
            methods=methods,
        )

    return blueprint
