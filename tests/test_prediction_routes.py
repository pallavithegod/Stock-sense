from __future__ import annotations

from backend.domain.predictions import PredictionQueryService


def test_prediction_query_service_builds_stable_payload():
    state = {
        "last_update": "2026-07-29T00:00:00+00:00",
        "predictions": {
            "INFY": {
                "symbol": "INFY",
                "signal": "WATCH",
                "as_of": "2026-07-29T00:00:00+00:00",
                "source_type": "heuristic",
            }
        },
    }
    service = PredictionQueryService(ai_engine_state=state)

    payload = service.predictions_payload()

    assert payload["success"] is True
    assert payload["predictions"][0]["symbol"] == "INFY"
    assert payload["predictions"][0]["signal"] == "WATCH"
    assert payload["predictions"][0]["source_type"] == "heuristic"
    assert payload["predictions"][0]["fingerprint"]
    assert payload["stocks"] == payload["predictions"]
    assert payload["timestamp"] == "2026-07-29T00:00:00+00:00"


def test_prediction_routes_are_registered_by_blueprint(app_module):
    endpoints = {rule.endpoint for rule in app_module.app.url_map.iter_rules()}

    assert "api_v1.predictions" in endpoints
    assert "api_v1.prediction_intelligence" in endpoints
    assert "api_v1.live_prediction" in endpoints
    assert "api_v1.prediction_governance_decision" in endpoints
    assert "api_v1.execute_prediction" in endpoints
    assert "api_v1.prediction_audit" in endpoints
    assert "api_v1.prediction_feedback" in endpoints
    assert "api_v1.prediction_confidence_distribution" in endpoints
    assert "api_v1.prediction_model_accuracy" in endpoints
    assert "api_v1.prediction_symbol_accuracy" in endpoints


def test_live_prediction_route_labels_unavailable_data(client):
    response = client.get("/api/v1/predictions/live/infy.ns")

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["symbol"] == "INFY"
    assert payload["data_quality"] == "unavailable"
    assert payload["source_type"] == "unavailable"
    assert payload["is_synthetic"] is False
    assert payload["is_demo"] is False


def test_prediction_execution_is_explicitly_unavailable(client):
    response = client.post("/api/v1/predictions/execute/INFY", json={"current_price": 100})

    assert response.status_code == 503
    payload = response.get_json()["data"]
    assert payload["success"] is False
    assert payload["status"] == "UNAVAILABLE"
    assert payload["persisted"] is False
    assert payload["source_type"] == "unavailable"
    assert payload["data_quality"] == "unavailable"


def test_prediction_governance_feedback_and_audit_are_thin_boundaries(client):
    governance = client.post("/api/v1/predictions/governance-decision", json={"symbol": "INFY"})
    feedback = client.post("/api/v1/predictions/feedback", json={"symbol": "INFY"})
    audit = client.get("/api/v1/predictions/audit/INFY")

    assert governance.status_code == 200
    assert governance.get_json()["data"]["decision"] == "PAUSE"
    assert feedback.status_code == 200
    assert feedback.get_json()["data"]["success"] is True
    assert audit.status_code == 200
    assert audit.get_json()["data"]["audits"] == []


def test_prediction_metric_routes_do_not_claim_accuracy(client):
    distribution = client.get("/api/v1/predictions/confidence-distribution")
    learning = client.get("/api/v1/predictions/learning/stats")
    model_accuracy = client.get("/api/v1/predictions/model/accuracy")
    symbol_accuracy = client.get("/api/v1/predictions/symbol/accuracy/INFY")
    evolved = client.get("/api/v1/predictions/evolved/INFY")

    assert distribution.status_code == 200
    assert distribution.get_json()["data"]["values"] == [0, 0, 0, 0, 0]
    assert learning.status_code == 200
    assert learning.get_json()["data"]["accuracy"] is None
    assert learning.get_json()["data"]["coverage"] == 0
    assert model_accuracy.status_code == 200
    assert model_accuracy.get_json()["data"]["accuracy"] is None
    assert model_accuracy.get_json()["data"]["directional_accuracy"] is None
    assert model_accuracy.get_json()["data"]["calibration_error"] is None
    assert symbol_accuracy.status_code == 200
    assert symbol_accuracy.get_json()["data"]["basis"] == "unavailable_until_matured_predictions_are_evaluated"
    assert evolved.status_code == 200
    assert evolved.get_json()["data"]["evolution_status"] == "unavailable_without_prediction_pipeline"


def test_legacy_prediction_aliases_are_removed(client):
    assert client.get("/api/predictions/live/INFY").status_code == 404
    assert client.post("/api/execute-prediction/INFY", json={"current_price": 100}).status_code == 404
    assert client.post("/api/governance-decision", json={"symbol": "INFY"}).status_code == 404
