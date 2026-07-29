from __future__ import annotations

from backend.domain.market import MarketService, MarketUniverse, normalize_symbol


def test_normalize_symbol_removes_exchange_suffixes():
    assert normalize_symbol("infy.ns") == "INFY"
    assert normalize_symbol(" tcs.bo ") == "TCS"


def test_market_service_searches_symbol_and_company_name():
    service = MarketService(MarketUniverse())

    symbol_rows = service.search("INFY")
    name_rows = service.search("infosys")

    assert symbol_rows[0]["symbol"] == "INFY"
    assert name_rows[0]["symbol"] == "INFY"
    assert symbol_rows[0]["data_quality"] == "unavailable"


def test_market_routes_are_registered_by_blueprint(app_module):
    endpoints = {rule.endpoint for rule in app_module.app.url_map.iter_rules()}

    assert "market.api_search" in endpoints
    assert "market.api_stocks" in endpoints
    assert "market.api_stock" in endpoints
    assert "market.api_stock_history" in endpoints
    assert "market.api_stock_analysis" in endpoints
    assert "market.api_market_trends" in endpoints


def test_stock_detail_returns_known_stock(client):
    response = client.get("/api/stock/INFY")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["symbol"] == "INFY"
    assert payload["data_quality"] == "unavailable"


def test_market_compatibility_routes_return_honest_unavailable_payloads(client):
    history = client.get("/api/stock/INFY/history")
    analysis = client.get("/api/stock/analysis/INFY")
    sectors = client.get("/api/analytics/sectors")
    risk_return = client.get("/api/analytics/risk-return")
    trends = client.get("/api/analytics/market-trends")

    assert history.status_code == 200
    assert history.get_json()["data_quality"] == "unavailable"
    assert analysis.status_code == 200
    assert analysis.get_json()["symbol"] == "INFY"
    assert sectors.status_code == 200
    assert sectors.get_json()["data_quality"] == "unavailable"
    assert risk_return.status_code == 200
    assert risk_return.get_json()["points"] == []
    assert trends.status_code == 200
    assert trends.get_json()["datasets"] == []
