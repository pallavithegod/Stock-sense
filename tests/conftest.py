from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def isolated_db_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("stocksense-db") / "test_nexus.db"


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

    module = importlib.import_module("app")
    module.app.config.update(TESTING=True)
    assert Path(module.dynamic_db.db_path).resolve() == isolated_db_path.resolve()
    return module


@pytest.fixture()
def client(app_module):
    with app_module.app.test_client() as test_client:
        yield test_client
