"""Thin news, alerts, and research API routes."""

from __future__ import annotations

from flask import Blueprint, jsonify

from backend.services.news_service import NewsService


def create_news_blueprint(*, news_service: NewsService) -> Blueprint:
    blueprint = Blueprint("news", __name__)

    @blueprint.get("/api/news")
    @blueprint.get("/api/news/market")
    def get_news():
        return jsonify(news_service.market_news())

    @blueprint.get("/api/news/symbol/<symbol>")
    def get_symbol_news(symbol: str):
        return jsonify(news_service.symbol_news(symbol))

    @blueprint.get("/api/alerts")
    def get_alerts():
        return jsonify(news_service.alerts())

    @blueprint.get("/api/research")
    def get_research():
        return jsonify(news_service.research())

    return blueprint

