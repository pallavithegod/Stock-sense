"""Thin prediction query API routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from backend.domain.predictions import PredictionQueryService


def create_prediction_api_blueprint(*, prediction_service: PredictionQueryService) -> Blueprint:
    blueprint = Blueprint("prediction_api", __name__)

    @blueprint.get("/api/predictions")
    def get_predictions():
        return jsonify(prediction_service.predictions_payload())

    @blueprint.get("/api/predictions/intelligence")
    def get_prediction_intelligence():
        return jsonify(prediction_service.intelligence_payload())

    @blueprint.get("/api/predictions/live/<symbol>")
    @blueprint.get("/api/predictions/quick/<symbol>")
    def get_live_prediction(symbol: str):
        return jsonify(prediction_service.live_prediction_payload(symbol))

    @blueprint.get("/api/evolved-prediction/<symbol>")
    def get_evolved_prediction(symbol: str):
        return jsonify(prediction_service.evolved_prediction_payload(symbol))

    @blueprint.post("/api/governance-decision")
    def get_governance_decision():
        payload = request.get_json(silent=True) or {}
        return jsonify(prediction_service.governance_decision_payload(payload))

    @blueprint.post("/api/execute-prediction/<symbol>")
    def execute_prediction(symbol: str):
        payload = request.get_json(silent=True) or {}
        return jsonify(prediction_service.execute_prediction_payload(symbol, payload)), 503

    @blueprint.get("/api/prediction/audit/<symbol>")
    def get_prediction_audit(symbol: str):
        limit = request.args.get("limit", 100, type=int) or 100
        return jsonify(prediction_service.audit_payload(symbol, limit=limit))

    @blueprint.post("/api/feedback")
    def submit_feedback():
        payload = request.get_json(silent=True) or {}
        return jsonify(prediction_service.feedback_payload(payload))

    @blueprint.get("/api/predictions/confidence-distribution")
    def get_confidence_distribution():
        return jsonify(prediction_service.confidence_distribution_payload())

    @blueprint.get("/api/learning/stats")
    def get_learning_stats():
        return jsonify(prediction_service.learning_stats_payload())

    @blueprint.get("/api/model/accuracy")
    def get_model_accuracy():
        return jsonify(prediction_service.model_accuracy_payload())

    @blueprint.get("/api/symbol/accuracy/<symbol>")
    def get_symbol_accuracy(symbol: str):
        return jsonify(prediction_service.symbol_accuracy_payload(symbol))

    return blueprint
