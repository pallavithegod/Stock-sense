"""Thin prediction query API routes."""

from __future__ import annotations

from flask import Blueprint, jsonify

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
    def get_live_prediction(symbol: str):
        return jsonify(prediction_service.live_prediction_payload(symbol))

    return blueprint

