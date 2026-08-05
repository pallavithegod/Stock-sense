from __future__ import annotations

import pytest

from backend.services.security import (
    clear_rate_limit_state,
    validate_security_configuration,
)


pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "path",
    [
        "/.env",
        "/app.py",
        "/database.py",
        "/data/stocksense.db",
        "/frontend/package.json",
        "/frontend/src/App.tsx",
        "/static/research/research_ui.js",
        "/not-a-real-project-file.txt",
    ],
)
def test_repository_files_are_not_public(client, path):
    response = client.get(path)

    assert response.status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        "/app.js",
        "/chart.js",
        "/style.css",
        "/stocksense-ai.js",
        "/stocksense-ai.css",
        "/dashboard/stocksense-ai.html",
    ],
)
def test_legacy_ui_assets_are_disabled_by_default(client, path):
    response = client.get(path)

    assert response.status_code == 404


def test_root_describes_api_only_development_mode(client):
    response = client.get("/")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["service"] == "StockSense API"
    assert "Vite" in payload["frontend"]


def test_oversized_json_body_is_rejected(client, monkeypatch):
    monkeypatch.setenv("MAX_JSON_BODY_BYTES", "32")

    response = client.post(
        "/api/v1/portfolio",
        data='{"symbol":"INFY","notes":"' + ("x" * 100) + '"}',
        content_type="application/json",
    )

    assert response.status_code == 413
    assert response.get_json()["status"] == "error"


def test_malformed_json_is_rejected(client, monkeypatch):
    monkeypatch.setenv("REQUIRE_MUTATION_TOKEN", "False")

    response = client.post(
        "/api/v1/portfolio",
        data='{"symbol":',
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.get_json()["status"] == "error"


def test_write_token_is_required_when_demo_protection_is_enabled(client, monkeypatch):
    monkeypatch.setenv("REQUIRE_MUTATION_TOKEN", "True")
    monkeypatch.setenv("DEMO_WRITE_TOKEN", "test-token-that-is-long-enough")

    response = client.post(
        "/api/v1/portfolio",
        json={"symbol": "INFY", "quantity": 1, "avg_price": 100},
    )

    assert response.status_code == 403
    assert response.get_json()["status"] == "error"


def test_invalid_portfolio_payload_is_rejected(client, monkeypatch):
    monkeypatch.setenv("REQUIRE_MUTATION_TOKEN", "False")

    response = client.post(
        "/api/v1/portfolio",
        json={"symbol": "###", "quantity": -1, "avg_price": 0},
    )

    assert response.status_code == 400
    assert response.get_json()["status"] == "error"


def test_rate_limit_returns_retry_metadata(client, monkeypatch):
    clear_rate_limit_state()
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "True")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    monkeypatch.setenv("API_RATE_LIMIT_PER_MINUTE", "1")

    assert client.get("/api/v1/system/status").status_code == 200
    response = client.get("/api/v1/system/status")

    assert response.status_code == 429
    assert response.headers["Retry-After"]
    assert response.get_json()["retry_after_seconds"] >= 1
    clear_rate_limit_state()


def test_production_rejects_placeholder_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("FLASK_SECRET_KEY", "change-me-local-dev-secret")

    with pytest.raises(RuntimeError, match="FLASK_SECRET_KEY"):
        validate_security_configuration()


def test_production_accepts_a_strong_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("FLASK_SECRET_KEY", "a-secure-random-value-with-more-than-32-characters")
    monkeypatch.setenv("REQUIRE_MUTATION_TOKEN", "False")

    validate_security_configuration()
