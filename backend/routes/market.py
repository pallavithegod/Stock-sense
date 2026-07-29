"""Thin market and stock query API routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from backend.domain.market import MarketService


def create_market_blueprint(*, market_service: MarketService) -> Blueprint:
    blueprint = Blueprint("market", __name__)

    @blueprint.get("/api/search")
    @blueprint.get("/api/search/comprehensive")
    def api_search():
        query = request.args.get("q", "")
        limit = request.args.get("limit", 15, type=int) or 15
        return jsonify({"success": True, "results": market_service.search(query, limit=limit)})

    @blueprint.get("/api/stocks")
    def api_stocks():
        limit = request.args.get("limit", 20, type=int) or 20
        stocks = market_service.list_stocks(limit=limit)
        return jsonify({"success": True, "stocks": stocks, "data": stocks, "results": stocks})

    @blueprint.get("/api/stock/<symbol>")
    def api_stock(symbol: str):
        stock = market_service.get_stock(symbol)
        if stock is None:
            return jsonify({"success": False, "error": f"Unknown symbol: {symbol}"}), 404
        return jsonify(stock)

    @blueprint.get("/api/market_universe")
    def api_market_universe():
        return jsonify(market_service.universe_payload())

    @blueprint.post("/api/user_tickers")
    def save_user_tickers():
        payload = request.get_json(silent=True) or {}
        return jsonify(market_service.save_user_tickers_payload(payload))

    @blueprint.get("/api/stock/<symbol>/history")
    @blueprint.get("/api/historical/<symbol>")
    def api_stock_history(symbol: str):
        return jsonify(market_service.stock_history_payload(symbol))

    @blueprint.get("/api/stock/analysis/<symbol>")
    @blueprint.get("/api/indicators/<symbol>")
    def api_stock_analysis(symbol: str):
        payload = market_service.stock_analysis_payload(symbol)
        return jsonify(payload), 200 if payload["success"] else 404

    @blueprint.post("/api/compare")
    def compare_stocks():
        payload = request.get_json(silent=True) or {}
        return jsonify(market_service.compare_payload(payload))

    @blueprint.get("/api/autocomplete")
    def autocomplete():
        query = request.args.get("q", "")
        limit = request.args.get("limit", 10, type=int) or 10
        return jsonify(market_service.autocomplete_payload(query, limit=limit))

    @blueprint.get("/api/analytics/market-trends")
    def api_market_trends():
        return jsonify(market_service.market_trends_payload())

    @blueprint.get("/api/analytics/sectors")
    def api_sector_analytics():
        return jsonify(market_service.sector_analytics_payload())

    @blueprint.get("/api/analytics/risk-return")
    def api_risk_return():
        return jsonify(market_service.risk_return_payload())

    return blueprint
