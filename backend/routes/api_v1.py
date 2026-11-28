"""Versioned API routes with canonical response contracts."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, g, jsonify, request
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
from backend.domain.portfolio.exceptions import PortfolioFeatureUnavailable
from backend.services.news_service import NewsService
from backend.services.research_service import build_emotional_state_payload, build_futures_analysis_payload
from backend.services.validation import (
    ValidationError as RequestValidationError,
    validate_portfolio_create,
    validate_portfolio_update,
    validate_recorded_sell,
    validate_sell_order,
    validation_error_payload,
)
from backend.services.supabase_auth import AuthProviderUnavailable, InvalidAccessToken


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


def _portfolio_feature_unavailable_response(exc: PortfolioFeatureUnavailable):
    return jsonify(error_payload(str(exc), code="FEATURE_UNAVAILABLE")), 501


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
    portfolio_provider = services.portfolio.repository.provider_name

    @blueprint.before_request
    def authenticate_private_requests():
        is_portfolio_request = request.path.startswith("/api/v1/portfolio")
        is_mutation = request.method in {"POST", "PUT", "PATCH", "DELETE"}
        authorization = request.headers.get("Authorization", "")
        is_authenticated_dashboard = (
            services.settings.require_auth
            and request.path in {"/api/v1/dashboard", "/api/v1/dashboard/live"}
            and authorization.lower().startswith("bearer ")
        )
        if not services.settings.require_auth or not (
            is_portfolio_request or is_mutation or is_authenticated_dashboard
        ):
            return None

        if not authorization.lower().startswith("bearer "):
            return jsonify(error_payload("Sign-in is required.", code="AUTH_REQUIRED")), 401
        token = authorization[7:].strip()
        if not token or services.supabase_auth is None:
            return jsonify(error_payload("Sign-in is required.", code="AUTH_REQUIRED")), 401
        try:
            g.stocksense_user = services.supabase_auth.get_user(token)
        except InvalidAccessToken:
            return jsonify(error_payload("Access token is invalid or expired.", code="INVALID_TOKEN")), 401
        except AuthProviderUnavailable:
            return jsonify(error_payload("Authentication service is temporarily unavailable.", code="AUTH_UNAVAILABLE")), 503
        return None

    def current_user():
        return getattr(g, "stocksense_user", None)

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
            worker_status=payload.get("worker_status") or {},
            startup_checks=payload.get("startup_checks") or {},
        )
        return jsonify(success_payload(dto, provenance_meta=provenance(provider="local_system", fetched_at=payload.get("timestamp"), stale=False)))

    @blueprint.get("/api/v1/system/diagnostics")
    def system_diagnostics():
        payload = services.system.diagnostics_payload()
        return _raw_success(payload, provider="local_system", fetched_at=payload.get("timestamp"), quality_status=_quality_from(payload))

    @blueprint.get("/api/v1/system/bootstrap/status")
    def system_bootstrap_status():
        payload = services.system.bootstrap_payload()
        return _raw_success(payload, provider="local_system", fetched_at=payload.get("timestamp"), quality_status=_quality_from(payload))

    @blueprint.get("/api/v1/dashboard")
    def dashboard():
        include_portfolio = not services.settings.require_auth or current_user() is not None
        payload = services.dashboard.snapshot(current_user(), include_portfolio=include_portfolio)
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
        payload = services.portfolio.build_state(current_user())
        dto = _portfolio_dto(payload, data_quality="portfolio_only")
        meta = provenance(provider=portfolio_provider, stale=False, quality_status=dto.data_quality)
        return jsonify(success_payload(dto, provenance_meta=meta))

    @blueprint.get("/api/v1/portfolio/positions")
    def portfolio_positions():
        rows = services.portfolio.list_positions(current_user())
        meta = provenance(provider=portfolio_provider, stale=False, quality_status="portfolio_only")
        return jsonify(success_payload({"positions": rows}, provenance_meta=meta))

    @blueprint.post("/api/v1/portfolio")
    def create_portfolio_position():
        try:
            data = validate_portfolio_create(
                request.get_json(silent=True),
                normalize_symbol=normalize_symbol,
                known_symbols=set(services.market.symbols.keys()),
            )
            result = services.portfolio.create_position(data, current_user())
            return _raw_success(result, provider=portfolio_provider, quality_status="portfolio_only")
        except RequestValidationError as exc:
            return jsonify(validation_error_payload(exc)), 400
        except ValueError as exc:
            return jsonify(error_payload(str(exc), code="VALIDATION_ERROR")), 400

    @blueprint.put("/api/v1/portfolio/<symbol>")
    def update_portfolio_position(symbol: str):
        try:
            data = validate_portfolio_update(request.get_json(silent=True), normalize_symbol=normalize_symbol, symbol=symbol)
            result = services.portfolio.update_position(symbol, data, current_user())
            return _raw_success(result, provider=portfolio_provider, quality_status="portfolio_only")
        except RequestValidationError as exc:
            return jsonify(validation_error_payload(exc)), 400
        except PortfolioFeatureUnavailable as exc:
            return _portfolio_feature_unavailable_response(exc)

    @blueprint.delete("/api/v1/portfolio/<symbol>")
    def delete_portfolio_position(symbol: str):
        try:
            result = services.portfolio.delete_position(symbol, current_user())
            status = 400 if result.get("status") == "error" else 200
            return _raw_success(result, provider=portfolio_provider, quality_status="portfolio_only"), status
        except PortfolioFeatureUnavailable as exc:
            return _portfolio_feature_unavailable_response(exc)

    @blueprint.get("/api/v1/portfolio/lots")
    def portfolio_lots():
        symbol = normalize_symbol(request.args.get("symbol")) if request.args.get("symbol") else None
        try:
            payload = services.portfolio.lots(symbol=symbol, principal=current_user())
            return _raw_success(payload, provider=portfolio_provider, quality_status="portfolio_only")
        except PortfolioFeatureUnavailable as exc:
            return _portfolio_feature_unavailable_response(exc)

    @blueprint.get("/api/v1/portfolio/realized-gains")
    def realized_gains():
        symbol = normalize_symbol(request.args.get("symbol")) if request.args.get("symbol") else None
        try:
            payload = services.portfolio.realized_gains(symbol=symbol, principal=current_user())
            return _raw_success(payload, provider=portfolio_provider, quality_status="portfolio_only")
        except PortfolioFeatureUnavailable as exc:
            return _portfolio_feature_unavailable_response(exc)

    @blueprint.get("/api/v1/portfolio/tax-summary")
    def portfolio_tax_summary():
        try:
            payload = services.portfolio.tax_summary(principal=current_user())
            return _raw_success(payload, provider=portfolio_provider, quality_status="portfolio_only")
        except PortfolioFeatureUnavailable as exc:
            return _portfolio_feature_unavailable_response(exc)

    @blueprint.get("/api/v1/portfolio/lot-insights")
    def portfolio_lot_insights():
        symbol = normalize_symbol(request.args.get("symbol")) if request.args.get("symbol") else None
        try:
            payload = services.portfolio.lot_insights(symbol=symbol, principal=current_user())
            return _raw_success(payload, provider=portfolio_provider, quality_status="portfolio_only")
        except PortfolioFeatureUnavailable as exc:
            return _portfolio_feature_unavailable_response(exc)

    @blueprint.get("/api/v1/portfolio/intelligence-suite")
    def portfolio_intelligence_suite():
        payload = services.portfolio.intelligence_suite(current_user())
        return _raw_success(payload, provider=portfolio_provider, quality_status="portfolio_only")

    @blueprint.get("/api/v1/portfolio/forecast")
    def portfolio_forecast():
        payload = services.portfolio.forecast(current_user())
        return _raw_success(payload, provider=portfolio_provider, quality_status="portfolio_only")

    @blueprint.get("/api/v1/portfolio/survival")
    def portfolio_survival():
        payload = services.portfolio.survival(current_user())
        return _raw_success(payload, provider=portfolio_provider, quality_status="portfolio_only")

    @blueprint.get("/api/v1/portfolio/backtesting")
    def portfolio_backtesting():
        payload = services.portfolio.backtesting(current_user())
        return _raw_success(payload, provider=portfolio_provider, quality_status="portfolio_only")

    @blueprint.get("/api/v1/portfolio/drift")
    def portfolio_drift():
        payload = services.portfolio.drift(current_user())
        return _raw_success(payload, provider=portfolio_provider, quality_status="portfolio_only")

    @blueprint.get("/api/v1/portfolio/governance")
    def portfolio_governance():
        payload = services.portfolio.governance(current_user())
        return _raw_success(payload, provider=portfolio_provider, quality_status="portfolio_only")

    @blueprint.get("/api/v1/portfolio/explainability")
    def portfolio_explainability():
        payload = services.portfolio.explainability(current_user())
        return _raw_success(payload, provider=portfolio_provider, quality_status="portfolio_only")

    @blueprint.get("/api/v1/portfolio/scorecard")
    def portfolio_scorecard():
        payload = services.portfolio.scorecard(current_user())
        return _raw_success(payload, provider=portfolio_provider, quality_status="portfolio_only")

    @blueprint.get("/api/v1/portfolio/allocation")
    def portfolio_allocation():
        payload = services.portfolio.allocation_chart(current_user())
        return _raw_success(payload, provider=portfolio_provider, quality_status="portfolio_only")

    @blueprint.post("/api/v1/portfolio/sell/simulate")
    def portfolio_sell_simulate():
        try:
            data = validate_sell_order(request.get_json(silent=True), normalize_symbol=normalize_symbol)
            payload = services.portfolio.simulate_sell(data, current_user())
            return _raw_success(payload, provider=portfolio_provider, quality_status="portfolio_only")
        except RequestValidationError as exc:
            return jsonify(validation_error_payload(exc)), 400
        except PortfolioFeatureUnavailable as exc:
            return _portfolio_feature_unavailable_response(exc)
        except ValueError as exc:
            return jsonify(error_payload(str(exc), code="VALIDATION_ERROR")), 400

    @blueprint.post("/api/v1/portfolio/sell")
    def portfolio_sell():
        try:
            data = validate_recorded_sell(request.get_json(silent=True), normalize_symbol=normalize_symbol)
            payload = services.portfolio.record_sell(data, current_user())
            return _raw_success(payload, provider=portfolio_provider, quality_status="portfolio_only")
        except RequestValidationError as exc:
            return jsonify(validation_error_payload(exc)), 400
        except PortfolioFeatureUnavailable as exc:
            return _portfolio_feature_unavailable_response(exc)
        except ValueError as exc:
            return jsonify(error_payload(str(exc), code="VALIDATION_ERROR")), 400

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
        return _raw_success(
            payload,
            provider=str(payload.get("provider") or "unavailable_prediction_pipeline"),
            quality_status=_quality_from(payload),
        )

    @blueprint.get("/api/v1/predictions/evolved/<symbol>")
    def evolved_prediction(symbol: str):
        payload = services.predictions.evolved_prediction_payload(symbol).get("data") or {}
        return _raw_success(payload, provider="unavailable_prediction_pipeline", quality_status=_quality_from(payload))

    @blueprint.post("/api/v1/predictions/governance-decision")
    def prediction_governance_decision():
        payload = services.predictions.governance_decision_payload(request.get_json(silent=True) or {})
        return _raw_success(payload, provider="prediction_presenter", quality_status=_quality_from(payload))

    @blueprint.post("/api/v1/predictions/execute/<symbol>")
    def execute_prediction(symbol: str):
        payload = services.predictions.execute_prediction_payload(symbol, request.get_json(silent=True) or {})
        return _raw_success(payload, provider="unavailable_prediction_pipeline", quality_status=_quality_from(payload)), 503

    @blueprint.get("/api/v1/predictions/audit/<symbol>")
    def prediction_audit(symbol: str):
        limit = request.args.get("limit", 100, type=int) or 100
        payload = services.predictions.audit_payload(symbol, limit=limit)
        return _raw_success(payload, provider="local_prediction_cache", quality_status="local_cache" if payload.get("count") else "unavailable")

    @blueprint.post("/api/v1/predictions/feedback")
    def prediction_feedback():
        payload = services.predictions.feedback_payload(request.get_json(silent=True) or {})
        return _raw_success(payload, provider="feedback_boundary", quality_status=_quality_from(payload))

    @blueprint.get("/api/v1/predictions/confidence-distribution")
    def prediction_confidence_distribution():
        payload = services.predictions.confidence_distribution_payload()
        return _raw_success(payload, provider="local_prediction_cache", quality_status=_quality_from(payload))

    @blueprint.get("/api/v1/predictions/learning/stats")
    def prediction_learning_stats():
        payload = services.predictions.learning_stats_payload()
        return _raw_success(payload, provider="local_prediction_cache", quality_status=_quality_from(payload))

    @blueprint.get("/api/v1/predictions/model/accuracy")
    def prediction_model_accuracy():
        payload = services.predictions.model_accuracy_payload()
        return _raw_success(payload, provider="local_prediction_cache", quality_status=_quality_from(payload))

    @blueprint.get("/api/v1/predictions/symbol/accuracy/<symbol>")
    def prediction_symbol_accuracy(symbol: str):
        payload = services.predictions.symbol_accuracy_payload(symbol)
        return _raw_success(payload, provider="local_prediction_cache", quality_status=_quality_from(payload))

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
