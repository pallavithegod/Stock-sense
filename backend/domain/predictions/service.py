"""Prediction read-model services."""

from __future__ import annotations

from typing import Any

from backend.domain.market import normalize_symbol


class PredictionQueryService:
    def __init__(self, *, ai_engine_state: dict[str, Any]):
        self.ai_engine_state = ai_engine_state

    def rows(self) -> list[dict[str, Any]]:
        values = self.ai_engine_state.get("predictions") or {}
        return [row for row in values.values() if isinstance(row, dict)]

    def predictions_payload(self) -> dict[str, Any]:
        rows = self.rows()
        return {
            "success": True,
            "rows": rows,
            "predictions": rows,
            "stocks": rows,
            "timestamp": self.ai_engine_state.get("last_update"),
        }

    def intelligence_payload(self) -> dict[str, Any]:
        rows = self.rows()
        return {
            "success": True,
            "rows": rows,
            "predictions": rows,
            "stocks": rows,
            "opportunities": rows,
        }

    def live_prediction_payload(self, symbol: str) -> dict[str, Any]:
        base_symbol = normalize_symbol(symbol) or str(symbol).upper()
        return {
            "success": True,
            "data": {
                "symbol": base_symbol,
                "current_price": None,
                "predictions": {},
                "confidences": {},
                "market_conditions": {"status": "unavailable_without_market_provider"},
                "data_quality": "unavailable",
            },
        }

