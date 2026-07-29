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
    validate_portfolio_update,
    validate_sell_order,
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

    @app.get("/api/dashboard-data")
    @app.get("/api/dashboard-data/live")
    @app.get("/api/dashboard-data/debug")
    def dashboard_payload():
        holdings = services.portfolio.get_portfolio()
        intelligence = services.runtime.compute_portfolio_intelligence(holdings)
        stocks = services.market.list_stocks(limit=8)
        return jsonify(
            {
                "success": True,
                "live_indices": [],
                "top_stocks": stocks,
                "positions": intelligence["positions"],
                "portfolio": intelligence,
                "timestamp": datetime.now().isoformat(),
            }
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

    @app.get("/api/search")
    @app.get("/api/search/comprehensive")
    def api_search():
        query = request.args.get("q", "")
        limit = request.args.get("limit", 15, type=int) or 15
        return jsonify({"success": True, "results": services.market.search(query, limit=limit)})

    @app.get("/api/stocks")
    def api_stocks():
        limit = request.args.get("limit", 20, type=int) or 20
        stocks = services.market.list_stocks(limit=limit)
        return jsonify({"success": True, "stocks": stocks, "data": stocks, "results": stocks})

    @app.get("/api/stock/<symbol>")
    def api_stock(symbol: str):
        base_symbol = normalize_symbol(symbol)
        stock = next((row for row in services.market.list_stocks(limit=200) if row["symbol"] == base_symbol), None)
        if not stock:
            return jsonify({"success": False, "error": f"Unknown symbol: {symbol}"}), 404
        return jsonify(stock)

    @app.get("/api/portfolio")
    def api_get_portfolio():
        return jsonify(services.portfolio.get_portfolio())

    @app.get("/api/portfolio/state")
    def api_portfolio_state():
        holdings = services.portfolio.get_portfolio()
        intelligence = services.runtime.compute_portfolio_intelligence(holdings)
        return jsonify({"success": True, **intelligence})

    @app.post("/api/portfolio")
    @app.post("/api/portfolio/add")
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

    @app.put("/api/portfolio/<symbol>")
    def update_portfolio(symbol: str):
        try:
            data = validate_portfolio_update(request.get_json(silent=True), normalize_symbol=normalize_symbol, symbol=symbol)
            services.portfolio.update_portfolio_position_summary(
                data["symbol"],
                data["quantity"],
                data["avg_price"],
                data["purchase_date"],
            )
            return jsonify({"status": "ok", "message": f"{data['symbol']} updated"})
        except ValidationError as exc:
            return jsonify(validation_error_payload(exc)), 400

    @app.delete("/api/portfolio/<symbol>")
    def delete_portfolio(symbol: str):
        base_symbol = normalize_symbol(symbol)
        if not base_symbol:
            return jsonify({"status": "error", "error": "invalid symbol"}), 400
        services.portfolio.delete_portfolio_position(base_symbol)
        return jsonify({"status": "deleted"})

    @app.get("/api/portfolio/lots")
    def get_portfolio_lots():
        symbol = normalize_symbol(request.args.get("symbol")) if request.args.get("symbol") else None
        rows = services.portfolio.get_portfolio_lots(symbol=symbol)
        return jsonify({"status": "ok", "data": rows, "count": len(rows), "total": len(rows)})

    @app.get("/api/portfolio/realized-gains")
    def get_realized_gains():
        symbol = normalize_symbol(request.args.get("symbol")) if request.args.get("symbol") else None
        rows = services.portfolio.get_realized_gains(symbol=symbol)
        return jsonify({"status": "ok", "data": rows, "count": len(rows), "total": len(rows)})

    @app.get("/api/portfolio/tax-summary")
    def get_portfolio_tax_summary():
        return jsonify({"status": "ok", "data": services.portfolio.get_financial_year_realized_summary()})

    @app.get("/api/portfolio/lot-insights")
    def get_portfolio_lot_insights():
        symbol = normalize_symbol(request.args.get("symbol")) if request.args.get("symbol") else None
        return jsonify({
            "status": "ok",
            "data": {
                "symbol": symbol,
                "open_lots": services.portfolio.get_portfolio_lots(symbol=symbol),
                "all_lots": services.portfolio.get_portfolio_lots(symbol=symbol),
                "near_ltcg": [],
                "fy_summary": services.portfolio.get_financial_year_realized_summary(),
            },
        })

    @app.get("/api/portfolio/intelligence-suite")
    def get_portfolio_intelligence_suite():
        holdings = services.portfolio.get_portfolio()
        intelligence = services.runtime.compute_portfolio_intelligence(holdings)
        return jsonify({"status": "ok", "data": {"generated_at": datetime.now().isoformat(), **intelligence}})

    @app.post("/api/portfolio/sell/simulate")
    def simulate_portfolio_sell():
        try:
            data = validate_sell_order(request.get_json(silent=True), normalize_symbol=normalize_symbol)
            result = services.portfolio.compare_sell_methods(
                data["symbol"],
                data["quantity"],
                data["sell_price"],
                sell_date=data["sell_date"],
                fees=data["fees"],
                methods=data["methods"],
            )
            return jsonify({"status": "ok", "data": result})
        except ValidationError as exc:
            return jsonify(validation_error_payload(exc)), 400

    @app.get("/api/predictions")
    def get_predictions():
        rows = list((services.ai_engine_state.get("predictions") or {}).values())
        return jsonify({"success": True, "rows": rows, "predictions": rows, "stocks": rows, "timestamp": services.ai_engine_state.get("last_update")})

    @app.get("/api/predictions/intelligence")
    def get_prediction_intelligence():
        rows = list((services.ai_engine_state.get("predictions") or {}).values())
        return jsonify({"success": True, "rows": rows, "predictions": rows, "stocks": rows, "opportunities": rows})

    @app.get("/api/predictions/live/<symbol>")
    def get_live_prediction(symbol: str):
        base_symbol = normalize_symbol(symbol) or str(symbol).upper()
        return jsonify({
            "success": True,
            "data": {
                "symbol": base_symbol,
                "current_price": None,
                "predictions": {},
                "confidences": {},
                "market_conditions": {"status": "unavailable_without_market_provider"},
                "data_quality": "unavailable",
            },
        })

    @app.get("/api/news")
    @app.get("/api/news/market")
    def get_news():
        return jsonify({"success": True, "articles": [], "data": [], "source": "unavailable"})

    @app.get("/api/news/symbol/<symbol>")
    def get_symbol_news(symbol: str):
        return jsonify({"success": True, "symbol": normalize_symbol(symbol), "articles": [], "data": []})

    @app.get("/api/alerts")
    def get_alerts():
        return jsonify({"success": True, "alerts": [], "data": []})

    @app.get("/api/research")
    def get_research():
        return jsonify({"success": True, "reports": [], "data": []})

    @app.get("/api/emotional-state/<symbol>")
    def get_emotional_state(symbol: str):
        return jsonify({"success": True, "symbol": normalize_symbol(symbol), "data_quality": "unavailable", "state": None})

    @app.get("/api/futures-analysis/<symbol>")
    def get_futures_analysis(symbol: str):
        return jsonify({"success": True, "symbol": normalize_symbol(symbol), "data_quality": "unavailable", "futures": []})


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

    return app


def run_dev(app: Flask | None = None) -> None:
    flask_app = app or create_app()
    settings: Settings = flask_app.config["STOCKSENSE_SETTINGS"]
    startup(flask_app)
    socketio.run(flask_app, debug=settings.debug, host=settings.host, port=settings.port)


__all__ = ["Settings", "create_app", "run_dev", "shutdown", "socketio", "startup"]
