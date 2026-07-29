"""Application factory for the StockSense Flask backend."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from flask import Flask, jsonify, request

from backend.app.config import Settings
from backend.app.extensions import init_extensions, socketio
from backend.app.services import AppServices, MarketUniverse, RuntimeContext, SQLitePortfolioRepository
from backend.routes.dashboard import create_dashboard_blueprint
from backend.routes.market_routes import create_market_blueprint
from backend.routes.predictions import create_predictions_blueprint
from backend.routes.portfolio import create_portfolio_blueprint
from backend.routes.research import create_research_blueprint
from backend.routes.system import create_system_blueprint
from backend.services.security import (
    mutation_guard_error,
    rate_limit_error,
    request_size_error,
    validate_security_configuration,
)
from backend.services.validation import (
    ValidationError,
    validate_portfolio_create,
    validation_error_payload,
)


def normalize_symbol(value: Any) -> str | None:
    if value is None:
        return None
    symbol = str(value).strip().upper().replace(".NS", "").replace(".BO", "")
    return symbol or None


def _build_services(settings: Settings) -> AppServices:
    logger = logging.getLogger("stocksense.factory")
    portfolio = SQLitePortfolioRepository(settings.resolved_db_path())
    market = MarketUniverse()
    runtime = RuntimeContext(portfolio=portfolio, logger=logger)
    runtime.cache_ttl = settings.cache_timeout
    return AppServices(
        settings=settings,
        portfolio=portfolio,
        market=market,
        runtime=runtime,
        logger=logger,
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

    def dashboard_payload():
        holdings = services.portfolio.get_portfolio()
        intelligence = services.runtime.compute_portfolio_intelligence(holdings)
        return jsonify(
            {
                "success": True,
                "live_indices": [],
                "top_stocks": services.market.search("", limit=5),
                "positions": intelligence["positions"],
                "portfolio": intelligence,
                "timestamp": datetime.now().isoformat(),
            }
        )

    app.register_blueprint(
        create_dashboard_blueprint(
            dashboard_data_handler=dashboard_payload,
            live_dashboard_handler=dashboard_payload,
            debug_dashboard_handler=dashboard_payload,
        )
    )


def _register_blueprints(app: Flask, services: AppServices) -> None:
    settings = services.settings
    app.register_blueprint(
        create_system_blueprint(
            project_root=settings.project_root,
            system_config={"DB_PATH": str(settings.resolved_db_path())},
            feature_flags={
                "machine_learning": False,
                "deep_learning": False,
                "technical_analysis": True,
                "sentiment_analysis": False,
            },
            quantum_ai=services.runtime,
            optional_modules=["yfinance", "pandas", "numpy", "sklearn", "tensorflow", "feedparser", "flask_socketio"],
        )
    )

    def api_search():
        query = request.args.get("q", "")
        limit = request.args.get("limit", 15, type=int) or 15
        return jsonify({"success": True, "results": services.market.search(query, limit=limit)})

    def api_get_portfolio():
        return jsonify(services.portfolio.get_portfolio())

    def api_portfolio_state():
        holdings = services.portfolio.get_portfolio()
        intelligence = services.runtime.compute_portfolio_intelligence(holdings)
        return jsonify({"success": True, **intelligence})

    def create_portfolio():
        try:
            data = validate_portfolio_create(
                request.get_json(silent=True),
                normalize_symbol=normalize_symbol,
                known_symbols=set(services.market.symbols.keys()),
            )
            services.portfolio.add_to_portfolio(
                data["symbol"],
                data["quantity"],
                data["avg_price"],
                data["purchase_date"],
            )
            return jsonify({"status": "ok", "exchange_symbol": f"{data['symbol']}.NS"})
        except ValidationError as exc:
            return jsonify(validation_error_payload(exc)), 400

    app.register_blueprint(create_market_blueprint(handlers={"api_search": api_search}))
    app.register_blueprint(
        create_portfolio_blueprint(
            handlers={
                "api_get_portfolio": api_get_portfolio,
                "api_portfolio_state": api_portfolio_state,
                "create_portfolio": create_portfolio,
                "create_portfolio_legacy": create_portfolio,
            }
        )
    )
    app.register_blueprint(
        create_predictions_blueprint(
            ai_engine_state=services.ai_engine_state,
            state_cache=services.state_cache,
            system_cache=services.system_cache,
            quantum_ai=services.runtime,
            dynamic_db=services.portfolio,
            normalize_symbol=normalize_symbol,
            realtime_state_builder=lambda rows: {},
            logger=services.logger,
        )
    )
    app.register_blueprint(
        create_research_blueprint(
            normalize_symbol=normalize_symbol,
            fetch_price_history=lambda symbol, period="1y": None,
            foresight_system=None,
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

    services = _build_services(resolved_settings)
    app.extensions["stocksense_services"] = services
    app.foresight_system = services.runtime

    init_extensions(app, resolved_settings)
    _register_security(app)
    _register_core_routes(app, services)
    _register_blueprints(app, services)

    if not resolved_settings.testing:
        startup(app)

    return app


def run_dev(app: Flask | None = None) -> None:
    flask_app = app or create_app()
    settings: Settings = flask_app.config["STOCKSENSE_SETTINGS"]
    socketio.run(flask_app, debug=settings.debug, host=settings.host, port=settings.port)


__all__ = ["Settings", "create_app", "run_dev", "shutdown", "socketio", "startup"]

