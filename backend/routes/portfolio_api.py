"""Thin portfolio API routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from backend.domain.market import MarketService, normalize_symbol
from backend.domain.portfolio import PortfolioService
from backend.services.validation import (
    ValidationError,
    validate_portfolio_create,
    validate_portfolio_update,
    validate_sell_order,
    validation_error_payload,
)


def create_portfolio_api_blueprint(*, portfolio_service: PortfolioService, market_service: MarketService) -> Blueprint:
    blueprint = Blueprint("portfolio_api", __name__)

    @blueprint.get("/api/portfolio")
    def api_get_portfolio():
        return jsonify(portfolio_service.list_positions())

    @blueprint.get("/api/portfolio/state")
    def api_portfolio_state():
        return jsonify(portfolio_service.build_state())

    @blueprint.post("/api/portfolio")
    @blueprint.post("/api/portfolio/add")
    def create_portfolio():
        try:
            data = validate_portfolio_create(
                request.get_json(silent=True),
                normalize_symbol=normalize_symbol,
                known_symbols=set(market_service.symbols.keys()),
            )
            return jsonify(portfolio_service.create_position(data))
        except ValidationError as exc:
            return jsonify(validation_error_payload(exc)), 400

    @blueprint.put("/api/portfolio/<symbol>")
    def update_portfolio(symbol: str):
        try:
            data = validate_portfolio_update(request.get_json(silent=True), normalize_symbol=normalize_symbol, symbol=symbol)
            return jsonify(portfolio_service.update_position(symbol, data))
        except ValidationError as exc:
            return jsonify(validation_error_payload(exc)), 400

    @blueprint.delete("/api/portfolio/<symbol>")
    def delete_portfolio(symbol: str):
        result = portfolio_service.delete_position(symbol)
        status = 400 if result.get("status") == "error" else 200
        return jsonify(result), status

    @blueprint.get("/api/portfolio/lots")
    def get_portfolio_lots():
        symbol = normalize_symbol(request.args.get("symbol")) if request.args.get("symbol") else None
        return jsonify(portfolio_service.lots(symbol=symbol))

    @blueprint.get("/api/portfolio/realized-gains")
    def get_realized_gains():
        symbol = normalize_symbol(request.args.get("symbol")) if request.args.get("symbol") else None
        return jsonify(portfolio_service.realized_gains(symbol=symbol))

    @blueprint.get("/api/portfolio/tax-summary")
    def get_portfolio_tax_summary():
        return jsonify(portfolio_service.tax_summary())

    @blueprint.get("/api/portfolio/lot-insights")
    def get_portfolio_lot_insights():
        symbol = normalize_symbol(request.args.get("symbol")) if request.args.get("symbol") else None
        return jsonify(portfolio_service.lot_insights(symbol=symbol))

    @blueprint.get("/api/portfolio/intelligence-suite")
    def get_portfolio_intelligence_suite():
        return jsonify(portfolio_service.intelligence_suite())

    @blueprint.get("/api/portfolio/forecast")
    def get_portfolio_forecast():
        return jsonify(portfolio_service.forecast())

    @blueprint.get("/api/portfolio/survival")
    def get_portfolio_survival():
        return jsonify(portfolio_service.survival())

    @blueprint.get("/api/portfolio/backtesting")
    def get_portfolio_backtesting():
        return jsonify(portfolio_service.backtesting())

    @blueprint.get("/api/portfolio/drift")
    def get_portfolio_drift():
        return jsonify(portfolio_service.drift())

    @blueprint.get("/api/portfolio/governance")
    def get_portfolio_governance():
        return jsonify(portfolio_service.governance())

    @blueprint.get("/api/portfolio/explainability")
    def get_portfolio_explainability():
        return jsonify(portfolio_service.explainability())

    @blueprint.get("/api/portfolio/scorecard")
    def get_portfolio_scorecard():
        return jsonify(portfolio_service.scorecard())

    @blueprint.get("/api/portfolio/allocation")
    def get_portfolio_allocation():
        return jsonify(portfolio_service.allocation_chart())

    @blueprint.post("/api/portfolio/sell/simulate")
    def simulate_portfolio_sell():
        try:
            data = validate_sell_order(request.get_json(silent=True), normalize_symbol=normalize_symbol)
            return jsonify(portfolio_service.simulate_sell(data))
        except ValidationError as exc:
            return jsonify(validation_error_payload(exc)), 400

    return blueprint
