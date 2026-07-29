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
    assert "prediction_api.get_governance_decision" in endpoints
    assert "prediction_api.execute_prediction" in endpoints
    assert "prediction_api.get_prediction_audit" in endpoints
    assert "prediction_api.submit_feedback" in endpoints
    assert "prediction_api.get_confidence_distribution" in endpoints
    assert "prediction_api.get_model_accuracy" in endpoints
    assert "prediction_api.get_symbol_accuracy" in endpoints


def test_live_prediction_route_labels_unavailable_data(client):
    response = client.get("/api/predictions/live/infy.ns")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["symbol"] == "INFY"
    assert payload["data"]["data_quality"] == "unavailable"


def test_prediction_execution_is_explicitly_unavailable(client):
    response = client.post("/api/execute-prediction/INFY", json={"current_price": 100})

    assert response.status_code == 503
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["status"] == "UNAVAILABLE"
    assert payload["data_quality"] == "unavailable"


def test_prediction_governance_feedback_and_audit_are_thin_boundaries(client):
    governance = client.post("/api/governance-decision", json={"symbol": "INFY"})
    feedback = client.post("/api/feedback", json={"symbol": "INFY"})
    audit = client.get("/api/prediction/audit/INFY")

    assert governance.status_code == 200
    assert governance.get_json()["decision"] == "PAUSE"
    assert feedback.status_code == 200
    assert feedback.get_json()["success"] is True
    assert audit.status_code == 200
    assert audit.get_json()["audits"] == []


def test_prediction_metric_routes_do_not_claim_accuracy(client):
    distribution = client.get("/api/predictions/confidence-distribution")
    learning = client.get("/api/learning/stats")
    model_accuracy = client.get("/api/model/accuracy")
    symbol_accuracy = client.get("/api/symbol/accuracy/INFY")
    evolved = client.get("/api/evolved-prediction/INFY")

    assert distribution.status_code == 200
    assert distribution.get_json()["values"] == [0, 0, 0, 0, 0]
    assert learning.status_code == 200
    assert learning.get_json()["accuracy"] is None
    assert model_accuracy.status_code == 200
    assert model_accuracy.get_json()["accuracy"] is None
    assert symbol_accuracy.status_code == 200
    assert symbol_accuracy.get_json()["basis"] == "unavailable_until_matured_predictions_are_evaluated"
    assert evolved.status_code == 200
    assert evolved.get_json()["data"]["evolution_status"] == "unavailable_without_prediction_pipeline"
