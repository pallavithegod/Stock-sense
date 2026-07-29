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

    return blueprint

