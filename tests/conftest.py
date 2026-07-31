from __future__ import annotations

import os
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture(scope="session")
def isolated_db_path() -> Path:
    runtime_dir = Path.cwd() / ".pytest-runtime" / f"stocksense-db-{uuid.uuid4().hex}"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir / "test_stocksense.db"


@pytest.fixture(scope="session")
def app_module(isolated_db_path: Path):
    runtime_dir = isolated_db_path.parent
    test_environment = {
        "APP_ENV": "testing",
        "TESTING": "True",
        "DEBUG": "False",
        "DEBUG_ENDPOINTS": "False",
        "ENABLE_LEGACY_UI": "False",
        "OPEN_BROWSER": "False",
        "RATE_LIMIT_ENABLED": "False",
        "REQUIRE_MUTATION_TOKEN": "False",
        "SOCKETIO_ASYNC_MODE": "threading",
        "STOCKSENSE_DB_PATH": str(isolated_db_path),
        "STOCKSENSE_MARKET_DB_PATH": str(runtime_dir / "market_intelligence.db"),
        "STOCKSENSE_ADAPTIVE_DB_PATH": str(runtime_dir / "adaptive_thresholds.db"),
        "STOCKSENSE_AUDIT_LOG_PATH": str(runtime_dir / "prediction_audit.jsonl"),
        "DISABLE_STARTUP_NETWORK": "True",
        "TRUST_PROXY_HEADERS": "False",
    }
    os.environ.update(test_environment)

    from backend.app import create_app

    app = create_app()
    app.config.update(TESTING=True)
    services = app.extensions["stocksense_services"]
    assert Path(services.portfolio.db_path).resolve() == isolated_db_path.resolve()
    return SimpleNamespace(app=app, services=services)


@pytest.fixture()
def client(app_module):
    with app_module.app.test_client() as test_client:
        yield test_client
