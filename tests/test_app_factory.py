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

    assert "news.get_news" in endpoints
    assert "news.get_symbol_news" in endpoints
    assert "news.get_research" in endpoints
    assert "research.get_emotional_state" in endpoints
