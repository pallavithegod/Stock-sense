"""Application factory for the StockSense Flask backend."""

from __future__ import annotations

import logging
from typing import Mapping

from flask import Flask, jsonify

from backend.app.compatibility import register_compatibility_deprecation_logging
from backend.app.config import Settings
from backend.app.errors import register_error_handlers
from backend.app.extensions import init_extensions, socketio
from backend.app.services import AppServices, RuntimeContext
from backend.domain.dashboard import DashboardService
from backend.domain.market import MarketService, MarketUniverse, normalize_symbol
from backend.domain.predictions import PredictionQueryService
from backend.domain.portfolio import PortfolioService, SQLitePortfolioRepository
from backend.domain.system import SystemService
from backend.routes.api_v1 import create_api_v1_blueprint
from backend.routes.dashboard_api import create_dashboard_api_blueprint
from backend.routes.health import create_health_blueprint
from backend.routes.market import create_market_blueprint
from backend.routes.news import create_news_blueprint
from backend.routes.portfolio_api import create_portfolio_api_blueprint
from backend.routes.prediction_api import create_prediction_api_blueprint
from backend.routes.research import create_research_blueprint
from backend.routes.system import create_system_blueprint
from backend.services.market_data import build_market_data_client
from backend.services.news_service import NewsService
from backend.services.observability import configure_logging, install_request_observability
from backend.services.security import (
    mutation_guard_error,
    rate_limit_error,
    request_size_error,
    validate_security_configuration,
)


def _build_services(settings: Settings) -> AppServices:
    logger = logging.getLogger("stocksense.factory")
    market_data = build_market_data_client(
        disabled=settings.disable_startup_network or settings.testing,
        timeout_seconds=settings.provider_timeout_seconds,
        cache_ttl_seconds=settings.cache_timeout,
    )
    market = MarketService(MarketUniverse(), market_data=market_data)
    portfolio = PortfolioService(
        repository=SQLitePortfolioRepository(settings.resolved_db_path()),
        market_service=market,
    )
    runtime = RuntimeContext(portfolio=portfolio, logger=logger)
    ai_engine_state = {"predictions": {}, "last_update": None, "cognitive_state": {}}
    predictions = PredictionQueryService(ai_engine_state=ai_engine_state)
    dashboard = DashboardService(market_service=market, portfolio_service=portfolio)
    runtime.cache_ttl = settings.cache_timeout
    system = SystemService(
        project_root=settings.project_root,
        db_path=settings.resolved_db_path(),
        feature_flags={
            "machine_learning": False,
            "deep_learning": False,
            "technical_analysis": True,
            "sentiment_analysis": False,
        },
        runtime=runtime,
        provider_health=market_data.health,
        optional_modules=["yfinance", "pandas", "numpy", "sklearn", "tensorflow", "feedparser", "flask_socketio"],
    )
    return AppServices(
        settings=settings,
        portfolio=portfolio,
        market=market,
        market_data=market_data,
        dashboard=dashboard,
        predictions=predictions,
        system=system,
        runtime=runtime,
        logger=logger,
        ai_engine_state=ai_engine_state,
    )


def _register_security(app: Flask) -> None:
    @app.before_request
    def enforce_request_guards():
        size_error = request_size_error()
        if size_error:
            return size_error
        limited = rate_limit_error()
        if limited:
            return limited
        return mutation_guard_error()


def _register_core_routes(app: Flask, services: AppServices) -> None:
    @app.get("/")
    def api_root():
        return jsonify(
            {
                "service": "StockSense API",
                "status": "ok",
                "frontend": "Run the Vite frontend from frontend/ during local development.",
            }
        )


def _register_blueprints(app: Flask, services: AppServices) -> None:
    news_service = NewsService(normalize_symbol=normalize_symbol)
    app.register_blueprint(create_health_blueprint())
    app.register_blueprint(create_api_v1_blueprint(services=services, news_service=news_service))
    app.register_blueprint(create_system_blueprint(system_service=services.system))
    app.register_blueprint(create_dashboard_api_blueprint(dashboard_service=services.dashboard))
    app.register_blueprint(create_news_blueprint(news_service=news_service))
    app.register_blueprint(create_market_blueprint(market_service=services.market))
    app.register_blueprint(
        create_portfolio_api_blueprint(
            portfolio_service=services.portfolio,
            market_service=services.market,
        )
    )
    app.register_blueprint(create_prediction_api_blueprint(prediction_service=services.predictions))
    app.register_blueprint(
        create_research_blueprint(
            normalize_symbol=normalize_symbol,
            fetch_price_history=lambda symbol, period="1y", interval="1d": None,
            foresight_system=services.runtime,
            logger=services.logger,
        )
    )


def startup(app: Flask) -> None:
    services: AppServices = app.extensions["stocksense_services"]
    services.portfolio.ensure_schema()
    app.config["_STARTUP_COMPLETE"] = True


def shutdown(app: Flask) -> None:
    app.config["_SHUTDOWN_COMPLETE"] = True


def create_app(settings: Settings | Mapping[str, object] | None = None) -> Flask:
    if isinstance(settings, Settings):
        resolved_settings = settings
    else:
        resolved_settings = Settings.from_env(settings)

    validate_security_configuration()

    app = Flask(__name__, static_folder=None)
    app.config.update(
        TESTING=resolved_settings.testing,
        SECRET_KEY=resolved_settings.secret_key,
        STOCKSENSE_SETTINGS=resolved_settings,
    )

    logger = configure_logging(app, resolved_settings)
    install_request_observability(app, logger)

    services = _build_services(resolved_settings)
    services.logger = logger
    services.runtime.logger = logger
    services.runtime.worker_status = services.worker_status
    app.extensions["stocksense_services"] = services
    app.foresight_system = services.runtime

    init_extensions(app, resolved_settings)
    register_error_handlers(app)
    _register_security(app)
    register_compatibility_deprecation_logging(app)
    _register_core_routes(app, services)
    _register_blueprints(app, services)

    return app


def run_dev(app: Flask | None = None) -> None:
    flask_app = app or create_app()
    settings: Settings = flask_app.config["STOCKSENSE_SETTINGS"]
    startup(flask_app)
    socketio.run(
        flask_app,
        debug=settings.debug,
        host=settings.host,
        port=settings.port,
        allow_unsafe_werkzeug=True,
    )


__all__ = ["Settings", "create_app", "run_dev", "shutdown", "socketio", "startup"]
