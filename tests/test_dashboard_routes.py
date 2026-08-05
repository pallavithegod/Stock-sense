from __future__ import annotations


def test_dashboard_routes_are_registered_by_blueprint(app_module):
    endpoints = {rule.endpoint for rule in app_module.app.url_map.iter_rules()}

    assert "api_v1.dashboard" in endpoints
    assert "api_v1.dashboard_live" in endpoints


def test_dashboard_snapshot_has_frontend_fields(client):
    response = client.get("/api/v1/dashboard/live")

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert isinstance(payload["live_indices"], list)
    assert isinstance(payload["top_stocks"], list)
    assert isinstance(payload["positions"], list)
    assert "portfolio" in payload
    assert payload["data_quality"] == "unavailable"
    assert all(row["is_synthetic"] is False and row["is_demo"] is False for row in payload["top_stocks"])


def test_legacy_dashboard_aliases_are_removed(client):
    assert client.get("/api/dashboard-data/live").status_code == 404
