from __future__ import annotations

import pytest


pytestmark = pytest.mark.integration


def test_system_status_is_available(client):
    response = client.get("/api/system/status")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "OPERATIONAL"
    assert payload["startup_checks"]["database"]["ok"] is True


def test_search_returns_a_json_result_collection(client):
    response = client.get("/api/search", query_string={"q": "INFY", "limit": 5})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert isinstance(payload["results"], list)


def test_predictions_endpoint_has_a_stable_top_level_shape(client):
    response = client.get("/api/predictions")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert isinstance(payload["predictions"], list)
    assert payload["stocks"] == payload["predictions"]


def test_portfolio_reads_from_the_isolated_database(client):
    response = client.get("/api/portfolio")

    assert response.status_code == 200
    assert response.get_json() == []


def test_live_dashboard_route_is_registered_without_starting_workers(client, app_module):
    assert app_module.app.config["TESTING"] is True

    response = client.get("/api/dashboard-data/live")

    assert response.status_code == 200
    assert isinstance(response.get_json(), dict)
    assert getattr(app_module.app, "_runtime_services_started", False) is False
