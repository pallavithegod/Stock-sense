"""Prediction API routes."""

from __future__ import annotations

from typing import Any, Mapping

from flask import Blueprint, jsonify, request

from backend.services.prediction_service import (
    build_prediction_intelligence_payload,
    build_predictions_payload,
    get_prediction_rows,
)
from utils import encoding


def create_predictions_blueprint(
    *,
    ai_engine_state: Mapping[str, Any],
    state_cache: Mapping[str, Any],
    system_cache: Mapping[str, Any],
    quantum_ai: Any,
    dynamic_db: Any,
    normalize_symbol: Any,
    realtime_state_builder: Any,
    logger: Any,
) -> Blueprint:
    blueprint = Blueprint("predictions", __name__)

    def _prediction_rows(limit: int = 100) -> list[dict[str, Any]]:
        return get_prediction_rows(
            ai_engine_state=ai_engine_state,
            system_cache=system_cache,
            quantum_ai=quantum_ai,
            dynamic_db=dynamic_db,
            logger=logger,
            limit=limit,
        )

    @blueprint.get("/api/predictions")
    def api_predictions():
        """Read-only predictions from global AI state and database fallbacks."""
        payload = build_predictions_payload(
            ai_engine_state=ai_engine_state,
            rows=_prediction_rows(),
        )
        return jsonify(encoding.sanitize_json(payload))

    @blueprint.get("/api/predictions/intelligence")
    def api_predictions_intelligence():
        """Compatibility endpoint for the dashboard intelligence table."""
        try:
            top_n = max(1, min(int(request.args.get("top_n", 100) or 100), 250))
        except (TypeError, ValueError):
            top_n = 100

        payload = build_prediction_intelligence_payload(
            ai_engine_state=ai_engine_state,
            state_cache=state_cache,
            rows=_prediction_rows(limit=top_n),
            top_n=top_n,
            normalize_symbol=normalize_symbol,
            realtime_state_builder=realtime_state_builder,
            logger=logger,
        )
        return jsonify(encoding.sanitize_json(payload))

    return blueprint
