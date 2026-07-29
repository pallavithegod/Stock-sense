from __future__ import annotations

from backend.domain.predictions import PredictionQueryService


def test_prediction_query_service_builds_stable_payload():
    state = {
        "last_update": "2026-07-29T00:00:00",
        "predictions": {"INFY": {"symbol": "INFY", "signal": "WATCH"}},
    }
    service = PredictionQueryService(ai_engine_state=state)

    payload = service.predictions_payload()

    assert payload["success"] is True
    assert payload["predictions"] == [{"symbol": "INFY", "signal": "WATCH"}]
    assert payload["stocks"] == payload["predictions"]
    assert payload["timestamp"] == "2026-07-29T00:00:00"


def test_prediction_routes_are_registered_by_blueprint(app_module):
    endpoints = {rule.endpoint for rule in app_module.app.url_map.iter_rules()}

    assert "prediction_api.get_predictions" in endpoints
    assert "prediction_api.get_prediction_intelligence" in endpoints
    assert "prediction_api.get_live_prediction" in endpoints


def test_live_prediction_route_labels_unavailable_data(client):
    response = client.get("/api/predictions/live/infy.ns")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["symbol"] == "INFY"
    assert payload["data"]["data_quality"] == "unavailable"
