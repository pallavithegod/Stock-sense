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
from backend.services.research_service import build_emotional_state_payload, build_futures_analysis_payload
from backend.services.validation import (
    ValidationError as RequestValidationError,
    validate_portfolio_create,
    validate_portfolio_update,
    validate_sell_order,
    validation_error_payload,
)


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
        source_type=row.get("source_type"),
        provider=row.get("provider"),
        model_version=row.get("model_version"),
        is_synthetic=bool(row.get("is_synthetic")),
        is_demo=bool(row.get("is_demo")),
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
        horizon=row.get("horizon"),
        as_of=row.get("as_of"),
        signal=row.get("signal") or row.get("recommendation"),
        current_price=_float_or_none(row.get("current_price") or row.get("price")),
        target_price=_float_or_none(row.get("target_price") or row.get("predicted_price")),
        expected_return=_float_or_none(row.get("expected_return") or row.get("predicted_return")),
        confidence=_float_or_none(row.get("confidence") or row.get("confidence_score")),
        risk=row.get("risk") or row.get("risk_level"),
        source_type=row.get("source_type"),
        provider=row.get("provider"),
        model_version=row.get("model_version"),
        feature_version=row.get("feature_version"),
        is_synthetic=bool(row.get("is_synthetic")),
        is_demo=bool(row.get("is_demo")),
        fingerprint=row.get("fingerprint"),
        idempotency_key=row.get("idempotency_key"),
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


def _quality_from(payload: dict[str, Any], fallback: str = "unavailable") -> str:
    return str(payload.get("data_quality") or payload.get("quality_status") or fallback)


def _raw_success(
    data: dict[str, Any] | list[Any],
    *,
    provider: str,
    fetched_at: Any = None,
    stale: bool = False,
    quality_status: str = "unavailable",
) -> Any:
    return jsonify(success_payload(
        data,
        provenance_meta=provenance(
            provider=provider,
            fetched_at=fetched_at,
            stale=stale,
            quality_status=quality_status,
        ),
    ))


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
        return jsonify(success_payload(dto, provenance_meta=meta))

    @blueprint.get("/api/v1/dashboard/live")
    def dashboard_live():
        return dashboard()

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
        return jsonify(success_payload(data, provenance_meta=meta, pagination=page_meta))

    @blueprint.get("/api/v1/search")
    @blueprint.get("/api/v1/search/comprehensive")
    def search():
        query = request.args.get("q", "")
        limit = request.args.get("limit", 15, type=int) or 15
        rows = services.market.search(query, limit=limit)
        data = {"results": [model_payload(_stock_dto(row)) for row in rows]}
        meta = provenance(provider="static_market_universe", stale=True, quality_status="unavailable")
        return jsonify(success_payload(data, provenance_meta=meta))

    @blueprint.get("/api/v1/stocks/<symbol>")
    def stock(symbol: str):
        row = services.market.get_stock(symbol)
        if row is None:
            return jsonify(error_payload(f"Unknown symbol: {symbol}", code="STOCK_NOT_FOUND")), 404
        meta = provenance(provider="static_market_universe", stale=True, quality_status=row.get("data_quality") or "unavailable")
        return jsonify(success_payload(_stock_dto(row), provenance_meta=meta))

    @blueprint.get("/api/v1/portfolio")
    def portfolio():
        payload = services.portfolio.build_state()
        dto = _portfolio_dto(payload, data_quality="portfolio_only")
        meta = provenance(provider="local_sqlite_portfolio", stale=False, quality_status=dto.data_quality)
        return jsonify(success_payload(dto, provenance_meta=meta))

    @blueprint.get("/api/v1/portfolio/positions")
    def portfolio_positions():
        rows = services.portfolio.list_positions()
        meta = provenance(provider="local_sqlite_portfolio", stale=False, quality_status="portfolio_only")
        return jsonify(success_payload({"positions": rows}, provenance_meta=meta))

    @blueprint.post("/api/v1/portfolio")
    def create_portfolio_position():
        try:
            data = validate_portfolio_create(
                request.get_json(silent=True),
                normalize_symbol=normalize_symbol,
                known_symbols=set(services.market.symbols.keys()),
            )
            result = services.portfolio.create_position(data)
            return _raw_success(result, provider="local_sqlite_portfolio", quality_status="portfolio_only")
        except RequestValidationError as exc:
            return jsonify(validation_error_payload(exc)), 400

    @blueprint.put("/api/v1/portfolio/<symbol>")
    def update_portfolio_position(symbol: str):
        try:
            data = validate_portfolio_update(request.get_json(silent=True), normalize_symbol=normalize_symbol, symbol=symbol)
            result = services.portfolio.update_position(symbol, data)
            return _raw_success(result, provider="local_sqlite_portfolio", quality_status="portfolio_only")
        except RequestValidationError as exc:
            return jsonify(validation_error_payload(exc)), 400

    @blueprint.delete("/api/v1/portfolio/<symbol>")
    def delete_portfolio_position(symbol: str):
        result = services.portfolio.delete_position(symbol)
        status = 400 if result.get("status") == "error" else 200
        return _raw_success(result, provider="local_sqlite_portfolio", quality_status="portfolio_only"), status

    @blueprint.get("/api/v1/portfolio/lots")
    def portfolio_lots():
        symbol = normalize_symbol(request.args.get("symbol")) if request.args.get("symbol") else None
        payload = services.portfolio.lots(symbol=symbol)
        return _raw_success(payload, provider="local_sqlite_portfolio", quality_status="portfolio_only")

    @blueprint.get("/api/v1/portfolio/realized-gains")
    def realized_gains():
        symbol = normalize_symbol(request.args.get("symbol")) if request.args.get("symbol") else None
        payload = services.portfolio.realized_gains(symbol=symbol)
        return _raw_success(payload, provider="local_sqlite_portfolio", quality_status="portfolio_only")

    @blueprint.get("/api/v1/portfolio/tax-summary")
    def portfolio_tax_summary():
        payload = services.portfolio.tax_summary()
        return _raw_success(payload, provider="local_sqlite_portfolio", quality_status="portfolio_only")

    @blueprint.get("/api/v1/portfolio/lot-insights")
    def portfolio_lot_insights():
        symbol = normalize_symbol(request.args.get("symbol")) if request.args.get("symbol") else None
        payload = services.portfolio.lot_insights(symbol=symbol)
        return _raw_success(payload, provider="local_sqlite_portfolio", quality_status="portfolio_only")

    @blueprint.get("/api/v1/portfolio/intelligence-suite")
    def portfolio_intelligence_suite():
        payload = services.portfolio.intelligence_suite()
        return _raw_success(payload, provider="local_sqlite_portfolio", quality_status="portfolio_only")

    @blueprint.post("/api/v1/portfolio/sell/simulate")
    def portfolio_sell_simulate():
        try:
            data = validate_sell_order(request.get_json(silent=True), normalize_symbol=normalize_symbol)
            payload = services.portfolio.simulate_sell(data)
            return _raw_success(payload, provider="local_sqlite_portfolio", quality_status="portfolio_only")
        except RequestValidationError as exc:
            return jsonify(validation_error_payload(exc)), 400

    @blueprint.get("/api/v1/predictions")
    def predictions():
        rows = [_prediction_dto(row) for row in services.predictions.rows()]
        data = {"predictions": [model_payload(row) for row in rows]}
        quality_status = "local_cache" if rows else "unavailable"
        meta = provenance(provider="local_prediction_cache", stale=not bool(rows), quality_status=quality_status)
        return jsonify(success_payload(data, provenance_meta=meta))

    @blueprint.get("/api/v1/predictions/intelligence")
    def prediction_intelligence():
        rows = [_prediction_dto(row) for row in services.predictions.rows()]
        data = {
            "rows": [model_payload(row) for row in rows],
            "predictions": [model_payload(row) for row in rows],
            "stocks": [model_payload(row) for row in rows],
            "opportunities": [model_payload(row) for row in rows],
        }
        quality_status = "local_cache" if rows else "unavailable"
        meta = provenance(provider="local_prediction_cache", stale=not bool(rows), quality_status=quality_status)
        return jsonify(success_payload(data, provenance_meta=meta))

    @blueprint.get("/api/v1/predictions/live/<symbol>")
    def live_prediction(symbol: str):
        payload = services.predictions.live_prediction_payload(symbol).get("data") or {}
        return _raw_success(payload, provider="unavailable_prediction_pipeline", quality_status=_quality_from(payload))

    @blueprint.get("/api/v1/news")
    def news():
        payload = news_service.market_news()
        dto = NewsDTO(
            articles=[_news_article_dto(row) for row in payload.get("articles", [])],
            source=payload.get("source") or "unavailable",
            data_quality=payload.get("data_quality") or "unavailable",
        )
        meta = provenance(provider=dto.source, fetched_at=payload.get("timestamp"), quality_status=dto.data_quality)
        return jsonify(success_payload(dto, provenance_meta=meta))

    @blueprint.get("/api/v1/news/market")
    def market_news():
        return news()

    @blueprint.get("/api/v1/news/symbol/<symbol>")
    def symbol_news(symbol: str):
        payload = news_service.symbol_news(symbol)
        meta = provenance(provider=payload.get("source") or "unavailable", fetched_at=payload.get("timestamp"), quality_status=_quality_from(payload))
        return jsonify(success_payload(payload, provenance_meta=meta))

    @blueprint.get("/api/v1/alerts")
    def alerts():
        payload = news_service.alerts()
        meta = provenance(provider="local_alerts", fetched_at=payload.get("timestamp"), quality_status=_quality_from(payload))
        return jsonify(success_payload(payload, provenance_meta=meta))

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
        return jsonify(success_payload(dto, provenance_meta=meta))

    @blueprint.get("/api/v1/emotional-state/<symbol>")
    def emotional_state(symbol: str):
        payload = build_emotional_state_payload(
            symbol,
            normalize_symbol=normalize_symbol,
            fetch_price_history=lambda requested_symbol, period="1y", interval="1d": None,
            foresight_system=services.runtime,
            logger=services.logger,
        )
        return _raw_success(payload, provider="research_service", quality_status="unavailable")

    @blueprint.get("/api/v1/futures-analysis/<symbol>")
    def futures_analysis(symbol: str):
        payload = build_futures_analysis_payload(
            symbol,
            normalize_symbol=normalize_symbol,
            fetch_price_history=lambda requested_symbol, period="1y", interval="1d": None,
            foresight_system=services.runtime,
            logger=services.logger,
        )
        return _raw_success(payload, provider="research_service", quality_status="unavailable")

    return blueprint
