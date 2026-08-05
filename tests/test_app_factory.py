from __future__ import annotations

import importlib
import sys
import uuid
from pathlib import Path

from backend.app.config import Settings


def test_default_dev_host_is_loopback():
    settings = Settings.from_env(environ={})

    assert settings.host == "127.0.0.1"


def test_create_app_uses_factory_without_importing_root_app(isolated_db_path, monkeypatch):
    runtime_dir = isolated_db_path.parent
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("TESTING", "True")
    monkeypatch.setenv("SOCKETIO_ASYNC_MODE", "threading")
    monkeypatch.setenv("STOCKSENSE_DB_PATH", str(isolated_db_path))
    monkeypatch.setenv("STOCKSENSE_MARKET_DB_PATH", str(runtime_dir / "market_intelligence.db"))
    monkeypatch.setenv("STOCKSENSE_ADAPTIVE_DB_PATH", str(runtime_dir / "adaptive_thresholds.db"))
    monkeypatch.setenv("STOCKSENSE_AUDIT_LOG_PATH", str(runtime_dir / "prediction_audit.jsonl"))
    monkeypatch.setenv("DISABLE_STARTUP_NETWORK", "True")

    sys.modules.pop("app", None)

    from backend.app import create_app

    flask_app = create_app()

    assert "app" not in sys.modules
    assert flask_app.url_map is not None
    services = flask_app.extensions["stocksense_services"]
    assert Path(services.portfolio.db_path).resolve() == isolated_db_path.resolve()


def test_legacy_runtime_bridge_modules_are_removed(isolated_db_path, monkeypatch):
    runtime_dir = isolated_db_path.parent
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("TESTING", "True")
    monkeypatch.setenv("SOCKETIO_ASYNC_MODE", "threading")
    monkeypatch.setenv("STOCKSENSE_DB_PATH", str(isolated_db_path))
    monkeypatch.setenv("STOCKSENSE_MARKET_DB_PATH", str(runtime_dir / "market_intelligence.db"))
    monkeypatch.setenv("STOCKSENSE_ADAPTIVE_DB_PATH", str(runtime_dir / "adaptive_thresholds.db"))
    monkeypatch.setenv("STOCKSENSE_AUDIT_LOG_PATH", str(runtime_dir / "prediction_audit.jsonl"))

    legacy_modules = {
        "backend.legacy.app_monolith": Path("backend/legacy/app_monolith.py"),
        "backend.legacy.quantum_ai": Path("backend/legacy/quantum_ai.py"),
        "backend.app.compatibility": Path("backend/app/compatibility.py"),
        "backend.routes.dashboard_api": Path("backend/routes/dashboard_api.py"),
        "backend.routes.market": Path("backend/routes/market.py"),
        "backend.routes.news": Path("backend/routes/news.py"),
        "backend.routes.portfolio_api": Path("backend/routes/portfolio_api.py"),
        "backend.routes.prediction_api": Path("backend/routes/prediction_api.py"),
        "backend.routes.research": Path("backend/routes/research.py"),
        "backend.routes.system": Path("backend/routes/system.py"),
        "backend.routes.dashboard": Path("backend/routes/dashboard.py"),
        "backend.routes.market_routes": Path("backend/routes/market_routes.py"),
        "backend.routes.portfolio": Path("backend/routes/portfolio.py"),
        "backend.routes.predictions": Path("backend/routes/predictions.py"),
        "backend.services.dashboard_builder": Path("backend/services/dashboard_builder.py"),
        "backend.services.runtime": Path("backend/services/runtime.py"),
    }
    for module_name in legacy_modules:
        sys.modules.pop(module_name, None)

    from backend.app import create_app

    create_app()

    assert set(legacy_modules).isdisjoint(sys.modules)
    for path in legacy_modules.values():
        assert not path.exists()


def test_create_app_does_not_create_database_until_lifecycle_or_request(monkeypatch):
    db_path = Path.cwd() / ".pytest-runtime" / f"factory-no-startup-{uuid.uuid4().hex}" / "factory.db"
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("TESTING", "True")
    monkeypatch.setenv("SOCKETIO_ASYNC_MODE", "threading")
    monkeypatch.setenv("STOCKSENSE_DB_PATH", str(db_path))
    monkeypatch.setenv("DISABLE_STARTUP_NETWORK", "True")

    from backend.app import create_app

    create_app()

    assert not db_path.exists()


def test_run_dev_allows_local_werkzeug_server(isolated_db_path, monkeypatch):
    runtime_dir = isolated_db_path.parent
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("TESTING", "True")
    monkeypatch.setenv("SOCKETIO_ASYNC_MODE", "threading")
    monkeypatch.setenv("STOCKSENSE_DB_PATH", str(isolated_db_path))
    monkeypatch.setenv("STOCKSENSE_MARKET_DB_PATH", str(runtime_dir / "market_intelligence.db"))
    monkeypatch.setenv("STOCKSENSE_ADAPTIVE_DB_PATH", str(runtime_dir / "adaptive_thresholds.db"))
    monkeypatch.setenv("STOCKSENSE_AUDIT_LOG_PATH", str(runtime_dir / "prediction_audit.jsonl"))

    from backend import app as app_module

    calls = {}

    def fake_run(flask_app, **kwargs):
        calls["kwargs"] = kwargs

    monkeypatch.setattr(app_module.socketio, "run", fake_run)
    app_module.run_dev(app_module.create_app())

    assert calls["kwargs"]["allow_unsafe_werkzeug"] is True
    assert calls["kwargs"]["host"] == "127.0.0.1"


def test_wsgi_entrypoint_imports_factory_app(isolated_db_path, monkeypatch):
    db_path = isolated_db_path.parent / "wsgi.db"
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("TESTING", "True")
    monkeypatch.setenv("SOCKETIO_ASYNC_MODE", "threading")
    monkeypatch.setenv("STOCKSENSE_DB_PATH", str(db_path))
    monkeypatch.setenv("DISABLE_STARTUP_NETWORK", "True")

    sys.modules.pop("app", None)
    sys.modules.pop("backend.wsgi", None)
    wsgi = importlib.import_module("backend.wsgi")

    assert "app" not in sys.modules
    assert wsgi.app.name == "backend.app"


def test_news_routes_are_registered_by_blueprint(app_module):
    endpoints = {rule.endpoint for rule in app_module.app.url_map.iter_rules()}

    assert "api_v1.news" in endpoints
    assert "api_v1.symbol_news" in endpoints
    assert "api_v1.research" in endpoints
    assert "api_v1.emotional_state" in endpoints
