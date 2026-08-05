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

    assert "api_v1.search" in endpoints
    assert "api_v1.stocks" in endpoints
    assert "api_v1.stock" in endpoints


def test_stock_detail_returns_known_stock(client):
    response = client.get("/api/v1/stocks/INFY")

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["symbol"] == "INFY"
    assert payload["data_quality"] == "unavailable"


def test_market_compatibility_routes_are_removed(client):
    assert client.get("/api/stock/INFY").status_code == 404
    assert client.get("/api/stock/INFY/history").status_code == 404
    assert client.get("/api/stock/analysis/INFY").status_code == 404
    assert client.get("/api/analytics/sectors").status_code == 404
    assert client.get("/api/analytics/risk-return").status_code == 404
    assert client.get("/api/analytics/market-trends").status_code == 404
