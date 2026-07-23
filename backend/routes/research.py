"""Research and foresight API routes."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify

from backend.services.research_service import (
    build_emotional_state_payload,
    build_futures_analysis_payload,
)


def create_research_blueprint(
    *,
    normalize_symbol: Any,
    fetch_price_history: Any,
    foresight_system: Any,
    logger: Any,
) -> Blueprint:
    blueprint = Blueprint("research", __name__)

    @blueprint.get("/api/emotional-state/<symbol>")
    def get_emotional_state(symbol: str):
        """Get emotional market-state analysis for a symbol."""
        return jsonify(build_emotional_state_payload(
            symbol,
            normalize_symbol=normalize_symbol,
            fetch_price_history=fetch_price_history,
            foresight_system=foresight_system,
            logger=logger,
        ))

    @blueprint.get("/api/futures-analysis/<symbol>")
    def get_futures_analysis(symbol: str):
        """Get probabilistic futures analysis for a symbol."""
        return jsonify(build_futures_analysis_payload(
            symbol,
            normalize_symbol=normalize_symbol,
            fetch_price_history=fetch_price_history,
            foresight_system=foresight_system,
            logger=logger,
        ))

    return blueprint
