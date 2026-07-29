from __future__ import annotations


def test_portfolio_routes_are_registered_by_blueprint(app_module):
    endpoints = {rule.endpoint for rule in app_module.app.url_map.iter_rules()}

    assert "portfolio_api.api_get_portfolio" in endpoints
    assert "portfolio_api.api_portfolio_state" in endpoints
    assert "portfolio_api.create_portfolio" in endpoints
    assert "portfolio_api.simulate_portfolio_sell" in endpoints
    assert "portfolio_api.get_portfolio_forecast" in endpoints
    assert "portfolio_api.get_portfolio_governance" in endpoints
    assert "portfolio_api.get_portfolio_scorecard" in endpoints


def test_portfolio_create_and_state_use_domain_service(client):
    create_response = client.post(
        "/api/portfolio",
        json={"symbol": "INFY", "quantity": 2, "avg_price": 100},
    )
    assert create_response.status_code == 200
    assert create_response.get_json()["status"] == "ok"

    list_response = client.get("/api/portfolio")
    assert list_response.status_code == 200
    positions = list_response.get_json()
    assert positions[0]["symbol"] == "INFY"
    assert positions[0]["quantity"] == 2

    state_response = client.get("/api/portfolio/state")
    assert state_response.status_code == 200
    state = state_response.get_json()
    assert state["success"] is True
    assert state["account_metrics"]["total_value"] == 200


def test_portfolio_sell_simulation_is_read_only(client):
    response = client.post(
        "/api/portfolio/sell/simulate",
        json={"symbol": "INFY", "quantity": 1, "sell_price": 120, "methods": ["FIFO"]},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["data"]["recommended_method"] == "FIFO"


def test_portfolio_intelligence_slices_are_domain_service_payloads(client):
    client.post("/api/portfolio", json={"symbol": "INFY", "quantity": 2, "avg_price": 100})

    suite = client.get("/api/portfolio/intelligence-suite")
    forecast = client.get("/api/portfolio/forecast")
    governance = client.get("/api/portfolio/governance")
    allocation = client.get("/api/portfolio/allocation")

    assert suite.status_code == 200
    assert suite.get_json()["data"]["data_quality"] == "portfolio_only"
    assert forecast.status_code == 200
    assert forecast.get_json()["data"]["status"] == "unavailable_without_market_provider"
    assert governance.status_code == 200
    assert governance.get_json()["data"]["status"] == "WATCH"
    assert allocation.status_code == 200
    assert allocation.get_json()["data"]["labels"] == ["INFY"]
