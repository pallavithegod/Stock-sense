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


def test_stock_detail_returns_known_stock(client):
    response = client.get("/api/stock/INFY")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["symbol"] == "INFY"
    assert payload["data_quality"] == "unavailable"
