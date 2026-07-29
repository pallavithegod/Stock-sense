from __future__ import annotations


def test_dashboard_routes_are_registered_by_blueprint(app_module):
    endpoints = {rule.endpoint for rule in app_module.app.url_map.iter_rules()}

    assert "dashboard_api.dashboard_payload" in endpoints


def test_dashboard_snapshot_has_frontend_fields(client):
    response = client.get("/api/dashboard-data/live")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert isinstance(payload["live_indices"], list)
    assert isinstance(payload["top_stocks"], list)
    assert isinstance(payload["positions"], list)
    assert "portfolio" in payload
    assert payload["data_quality"] == "unavailable"
