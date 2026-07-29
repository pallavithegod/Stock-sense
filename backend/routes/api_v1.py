"""Versioned API routes with canonical response contracts."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from backend.app.contracts import (
    DashboardDTO,
    NewsArticleDTO,
    NewsDTO,
    PortfolioDTO,
    PortfolioPositionDTO,
    PredictionDTO,
    ResearchDTO,
    StockDTO,
    SystemDTO,
    contract_schemas,
    error_payload,
    model_payload,
    paginated_slice,
    parse_pagination,
    provenance,
    success_payload,
)
from backend.app.services import AppServices
from backend.domain.market import normalize_symbol
from backend.services.news_service import NewsService


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _stock_dto(row: dict[str, Any]) -> StockDTO:
    return StockDTO(
        symbol=str(row.get("symbol") or ""),
        name=row.get("name"),
        exchange=row.get("exchange"),
        display=row.get("display"),
        price=_float_or_none(row.get("price")),
        current_price=_float_or_none(row.get("current_price")),
        change_value=_float_or_none(row.get("change_value")),
        change_percent=_float_or_none(row.get("change_percent")),
        data_quality=row.get("data_quality") or "unavailable",
    )


def _position_dto(row: dict[str, Any]) -> PortfolioPositionDTO:
    return PortfolioPositionDTO(
        symbol=row.get("symbol"),
        quantity=_float_or_none(row.get("quantity")),
        avg_price=_float_or_none(row.get("avg_price")),
        current_price=_float_or_none(row.get("current_price")),
        market_value=_float_or_none(row.get("market_value")),
    )


def _portfolio_dto(payload: dict[str, Any], *, data_quality: str = "portfolio_only") -> PortfolioDTO:
    return PortfolioDTO(
        positions=[_position_dto(row) for row in payload.get("positions", [])],
        account_metrics=payload.get("account_metrics") or {},
        data_quality=payload.get("data_quality") or data_quality,
    )


def _prediction_dto(row: dict[str, Any]) -> PredictionDTO:
    return PredictionDTO(
        symbol=normalize_symbol(row.get("symbol")),
        signal=row.get("signal") or row.get("recommendation"),
        current_price=_float_or_none(row.get("current_price") or row.get("price")),
        target_price=_float_or_none(row.get("target_price") or row.get("predicted_price")),
        confidence=_float_or_none(row.get("confidence") or row.get("confidence_score")),
        risk=row.get("risk") or row.get("risk_level"),
        source_type=row.get("source_type"),
        data_quality=row.get("data_quality") or "unavailable",
    )


def _news_article_dto(row: dict[str, Any]) -> NewsArticleDTO:
    return NewsArticleDTO(
        title=row.get("title"),
        summary=row.get("summary") or row.get("description"),
        url=row.get("url") or row.get("link"),
        published_at=row.get("published_at") or row.get("published"),
        source=row.get("source"),
    )


def _validation_error_response(exc: ValidationError):
    return jsonify(error_payload(str(exc), code="VALIDATION_ERROR")), 400


def create_api_v1_blueprint(*, services: AppServices, news_service: NewsService) -> Blueprint:
    blueprint = Blueprint("api_v1", __name__)

    @blueprint.get("/api/v1/schema")
    def schema():
        return jsonify(success_payload(contract_schemas(), provenance_meta=provenance(provider="contracts", stale=False)))

    @blueprint.get("/api/v1/system/status")
    def system_status():
        payload = services.system.status_payload()
        dto = SystemDTO(
            status=payload["status"],
            version=payload.get("version"),
            ai_features=payload.get("ai_features") or {},
            models_loaded=payload.get("models_loaded") or [],
            data_sources=payload.get("data_sources") or [],
            performance=payload.get("performance") or {},
            cache_status=payload.get("cache_status") or {},
            startup_checks=payload.get("startup_checks") or {},
        )
        return jsonify(success_payload(dto, provenance_meta=provenance(provider="local_system", fetched_at=payload.get("timestamp"), stale=False)))

    @blueprint.get("/api/v1/dashboard")
    def dashboard():
        payload = services.dashboard.snapshot()
        dto = DashboardDTO(
            live_indices=payload.get("live_indices") or [],
            top_stocks=[_stock_dto(row) for row in payload.get("top_stocks", [])],
            positions=[_position_dto(row) for row in payload.get("positions", [])],
            portfolio=_portfolio_dto(payload.get("portfolio") or {}, data_quality=payload.get("data_quality") or "unavailable"),
            data_quality=payload.get("data_quality") or "unavailable",
        )
        meta = provenance(provider="local_dashboard", fetched_at=payload.get("timestamp"), quality_status=dto.data_quality)
        return jsonify(success_payload(dto, provenance_meta=meta, compatibility_alias="/api/dashboard-data/live"))

    @blueprint.get("/api/v1/stocks")
    def stocks():
        try:
            query = parse_pagination(request.args)
        except ValidationError as exc:
            return _validation_error_response(exc)
        rows = services.market.list_stocks(limit=len(services.market.symbols) or 1)
        page_rows, page_meta = paginated_slice(rows, query)
        data = {"stocks": [model_payload(_stock_dto(row)) for row in page_rows]}
        meta = provenance(provider="static_market_universe", stale=True, quality_status="unavailable")
        return jsonify(success_payload(data, provenance_meta=meta, pagination=page_meta, compatibility_alias="/api/stocks"))

    @blueprint.get("/api/v1/stocks/<symbol>")
    def stock(symbol: str):
        row = services.market.get_stock(symbol)
        if row is None:
            return jsonify(error_payload(f"Unknown symbol: {symbol}", code="STOCK_NOT_FOUND")), 404
        meta = provenance(provider="static_market_universe", stale=True, quality_status=row.get("data_quality") or "unavailable")
        return jsonify(success_payload(_stock_dto(row), provenance_meta=meta, compatibility_alias=f"/api/stock/{symbol}"))

    @blueprint.get("/api/v1/portfolio")
    def portfolio():
        payload = services.portfolio.build_state()
        dto = _portfolio_dto(payload, data_quality="portfolio_only")
        meta = provenance(provider="local_sqlite_portfolio", stale=False, quality_status=dto.data_quality)
        return jsonify(success_payload(dto, provenance_meta=meta, compatibility_alias="/api/portfolio/state"))

    @blueprint.get("/api/v1/predictions")
    def predictions():
        rows = [_prediction_dto(row) for row in services.predictions.rows()]
        data = {"predictions": [model_payload(row) for row in rows]}
        quality_status = "local_cache" if rows else "unavailable"
        meta = provenance(provider="local_prediction_cache", stale=not bool(rows), quality_status=quality_status)
        return jsonify(success_payload(data, provenance_meta=meta, compatibility_alias="/api/predictions/intelligence"))

    @blueprint.get("/api/v1/news")
    def news():
        payload = news_service.market_news()
        dto = NewsDTO(
            articles=[_news_article_dto(row) for row in payload.get("articles", [])],
            source=payload.get("source") or "unavailable",
            data_quality=payload.get("data_quality") or "unavailable",
        )
        meta = provenance(provider=dto.source, fetched_at=payload.get("timestamp"), quality_status=dto.data_quality)
        return jsonify(success_payload(dto, provenance_meta=meta, compatibility_alias="/api/news/market"))

    @blueprint.get("/api/v1/research")
    def research():
        payload = news_service.research()
        dto = ResearchDTO(
            research_reports=payload.get("research_reports") or payload.get("researchreports") or [],
            ai_insights=payload.get("ai_insights") or payload.get("aiinsights") or [],
            model_performance=payload.get("model_performance") or {},
            live_stats=payload.get("live_stats") or {},
            message=payload.get("message"),
            data_quality=payload.get("data_quality") or "unavailable",
        )
        meta = provenance(provider="research_service", fetched_at=payload.get("timestamp"), quality_status=dto.data_quality)
        return jsonify(success_payload(dto, provenance_meta=meta, compatibility_alias="/api/research"))

    return blueprint
