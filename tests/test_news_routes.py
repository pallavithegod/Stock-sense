from __future__ import annotations


def test_market_news_returns_explicit_unavailable_state(client):
    response = client.get("/api/v1/news/market")

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["articles"] == []
    assert payload["data_quality"] == "unavailable"


def test_symbol_news_normalizes_symbol(client):
    response = client.get("/api/v1/news/symbol/infy.ns")

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["success"] is True
    assert payload["symbol"] == "INFY"
    assert payload["articles"] == []


def test_research_payload_matches_frontend_shape(client):
    response = client.get("/api/v1/research")

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["research_reports"] == []
    assert payload["ai_insights"] == []
    assert payload["data_quality"] == "unavailable"


def test_foresight_research_routes_are_registered_without_live_provider(client):
    emotional = client.get("/api/v1/emotional-state/INFY")
    futures = client.get("/api/v1/futures-analysis/INFY")

    assert emotional.status_code == 200
    assert emotional.get_json()["data"]["success"] is True
    assert emotional.get_json()["data"]["available"] is False
    assert futures.status_code == 200
    assert futures.get_json()["data"]["success"] is True
    assert futures.get_json()["data"]["available"] is False


def test_legacy_news_and_research_aliases_are_removed(client):
    assert client.get("/api/news/market").status_code == 404
    assert client.get("/api/news/symbol/INFY").status_code == 404
    assert client.get("/api/research").status_code == 404
