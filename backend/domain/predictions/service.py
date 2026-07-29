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

    def evolved_prediction_payload(self, symbol: str) -> dict[str, Any]:
        payload = self.live_prediction_payload(symbol)
        payload["data"]["evolution_status"] = "unavailable_without_prediction_pipeline"
        return payload

    def governance_decision_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        symbol = normalize_symbol(payload.get("symbol")) if isinstance(payload, dict) else None
        return {
            "success": True,
            "symbol": symbol,
            "decision": "PAUSE",
            "reason": "Prediction governance execution is unavailable in the lightweight factory runtime.",
            "source_type": "presentation_intelligence",
            "data_quality": "unavailable",
        }

    def execute_prediction_payload(self, symbol: str, payload: dict[str, Any]) -> dict[str, Any]:
        base_symbol = normalize_symbol(symbol) or str(symbol).upper()
        return {
            "success": False,
            "symbol": base_symbol,
            "status": "UNAVAILABLE",
            "error": "Prediction execution is disabled until the Phase 6 prediction pipeline is made idempotent and source-labelled.",
            "data_quality": "unavailable",
        }

    def audit_payload(self, symbol: str, limit: int = 100) -> dict[str, Any]:
        base_symbol = normalize_symbol(symbol) or str(symbol).upper()
        rows = [
            row for row in self.rows()
            if normalize_symbol(row.get("symbol")) == base_symbol
        ][: max(1, min(int(limit or 100), 500))]
        return {
            "success": True,
            "symbol": base_symbol,
            "count": len(rows),
            "audits": rows,
        }

    def feedback_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        symbol = normalize_symbol(payload.get("symbol")) if isinstance(payload, dict) else None
        return {
            "success": True,
            "symbol": symbol,
            "message": "Feedback accepted by the API boundary; model learning is deferred to the explicit prediction pipeline.",
            "data_quality": "unavailable",
        }

    def confidence_distribution_payload(self) -> dict[str, Any]:
        buckets = {"0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}
        for row in self.rows():
            try:
                confidence = float(row.get("confidence", row.get("confidence_score", 0)) or 0)
            except (TypeError, ValueError):
                confidence = 0
            if confidence < 20:
                buckets["0-20"] += 1
            elif confidence < 40:
                buckets["20-40"] += 1
            elif confidence < 60:
                buckets["40-60"] += 1
            elif confidence < 80:
                buckets["60-80"] += 1
            else:
                buckets["80-100"] += 1
        return {
            "success": True,
            "labels": list(buckets.keys()),
            "values": list(buckets.values()),
            "data_quality": "unavailable" if not self.rows() else "local_cache",
        }

    def learning_stats_payload(self) -> dict[str, Any]:
        return {
            "success": True,
            "total_predictions": len(self.rows()),
            "matured_predictions": 0,
            "accuracy": None,
            "accuracy_basis": "unavailable_until_matured_predictions_are_evaluated",
            "data_quality": "unavailable",
        }

    def model_accuracy_payload(self) -> dict[str, Any]:
        return {
            "success": True,
            "accuracy": None,
            "directional_accuracy": None,
            "target_error": None,
            "basis": "unavailable_until_matured_predictions_are_evaluated",
            "data_quality": "unavailable",
        }

    def symbol_accuracy_payload(self, symbol: str) -> dict[str, Any]:
        base_symbol = normalize_symbol(symbol) or str(symbol).upper()
        return {
            "success": True,
            "symbol": base_symbol,
            "accuracy": None,
            "basis": "unavailable_until_matured_predictions_are_evaluated",
            "data_quality": "unavailable",
        }
