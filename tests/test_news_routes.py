from __future__ import annotations


def test_market_news_returns_explicit_unavailable_state(client):
    response = client.get("/api/news/market")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["articles"] == []
    assert payload["data_quality"] == "unavailable"


def test_symbol_news_normalizes_symbol(client):
    response = client.get("/api/news/symbol/infy.ns")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["symbol"] == "INFY"
    assert payload["articles"] == []


def test_research_payload_matches_frontend_shape(client):
    response = client.get("/api/research")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["researchreports"] == []
    assert payload["aiinsights"] == []
    assert payload["data_quality"] == "unavailable"


def test_foresight_research_routes_are_registered_without_live_provider(client):
    emotional = client.get("/api/emotional-state/INFY")
    futures = client.get("/api/futures-analysis/INFY")

    assert emotional.status_code == 200
    assert emotional.get_json()["success"] is True
    assert emotional.get_json()["available"] is False
    assert futures.status_code == 200
    assert futures.get_json()["success"] is True
    assert futures.get_json()["available"] is False
