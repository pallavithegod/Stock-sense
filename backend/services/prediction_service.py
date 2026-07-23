"""Prediction service helpers.

The legacy app still owns model execution and state caches. This module keeps
read-side prediction API logic independent from Flask so it can be tested and
later reused by FastAPI without carrying route decorators along.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Mapping
from zoneinfo import ZoneInfo

from backend.services.prediction_presenter import normalize_prediction_rows


NormalizeSymbol = Callable[[Any], str | None]
RealtimeStateBuilder = Callable[[list[dict[str, Any]]], Mapping[str, Any] | None]


def get_prediction_rows(
    *,
    ai_engine_state: Mapping[str, Any],
    system_cache: Mapping[str, Any],
    quantum_ai: Any,
    dynamic_db: Any,
    logger: Any,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return latest non-synthetic prediction rows from all known sources."""
    rows = list((ai_engine_state.get("predictions") or {}).values())

    if not rows:
        try:
            recent = system_cache.get("recent_predictions", []) or []
            rows = [row for row in recent if isinstance(row, dict) and row.get("symbol")]
        except Exception:
            rows = []

    if not rows:
        try:
            history = list(getattr(quantum_ai, "prediction_history", []) or [])
            rows = [row for row in history[-limit:] if isinstance(row, dict) and row.get("symbol")]
        except Exception:
            rows = []

    if not rows:
        for db_source in (getattr(quantum_ai, "db", None), dynamic_db):
            if not db_source or not hasattr(db_source, "get_recent_predictions"):
                continue
            try:
                recent_db_rows = db_source.get_recent_predictions(limit=limit) or []
                rows = [row for row in recent_db_rows if isinstance(row, dict) and row.get("symbol")]
                if rows:
                    break
            except Exception as exc:
                logger.debug("SQLite prediction fallback skipped: %s", exc)

    return [
        row
        for row in rows[:limit]
        if isinstance(row, dict)
        and row.get("symbol")
        and str(row.get("data_source") or "").lower() != "synthetic"
    ]


def merge_prediction_rows_with_intelligence(
    rows: list[dict[str, Any]] | None,
    opportunities: list[dict[str, Any]] | None,
    *,
    normalize_symbol: NormalizeSymbol,
) -> list[dict[str, Any]]:
    """Enrich prediction rows with allocation/edge data when available."""
    valid_rows = [row for row in (rows or []) if isinstance(row, dict) and row.get("symbol")]
    valid_opportunities = [
        row for row in (opportunities or []) if isinstance(row, dict) and row.get("symbol")
    ]
    opportunity_map = {
        normalize_symbol(item.get("symbol")): item
        for item in valid_opportunities
        if normalize_symbol(item.get("symbol"))
    }

    merged: list[dict[str, Any]] = []
    for row in valid_rows:
        base_symbol = normalize_symbol(row.get("symbol"))
        intelligence = opportunity_map.get(base_symbol, {})
        enriched = dict(row)
        if intelligence:
            enriched.update({
                "action": intelligence.get("action", enriched.get("action")),
                "allocation_pct": intelligence.get("allocation_pct", enriched.get("allocation_pct")),
                "weight_pct": intelligence.get("allocation_pct", enriched.get("weight_pct")),
                "ai_size": intelligence.get("allocation_pct", enriched.get("ai_size")),
                "kelly_fraction": intelligence.get("kelly_fraction", enriched.get("kelly_fraction")),
                "edge_score": intelligence.get("edge_score", enriched.get("edge_score")),
                "recommended_position_size": intelligence.get(
                    "allocation_pct",
                    enriched.get("recommended_position_size"),
                ),
            })
        merged.append(enriched)

    used_symbols = {
        normalize_symbol(item.get("symbol"))
        for item in merged
        if normalize_symbol(item.get("symbol"))
    }
    for intelligence in valid_opportunities:
        base_symbol = normalize_symbol(intelligence.get("symbol"))
        if base_symbol and base_symbol not in used_symbols:
            merged.append(dict(intelligence))
    return merged


def build_predictions_payload(
    *,
    ai_engine_state: Mapping[str, Any],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized_rows = normalize_prediction_rows(rows)
    return {
        "success": True,
        "stocks": normalized_rows,
        "predictions": normalized_rows,
        "timestamp": ai_engine_state.get("last_update"),
    }


def build_prediction_intelligence_payload(
    *,
    ai_engine_state: Mapping[str, Any],
    state_cache: Mapping[str, Any],
    rows: list[dict[str, Any]],
    top_n: int,
    normalize_symbol: NormalizeSymbol,
    realtime_state_builder: RealtimeStateBuilder,
    logger: Any,
) -> dict[str, Any]:
    state = ai_engine_state.get("cognitive_state", {}) or {}
    opportunities = [row for row in (state.get("opportunities") or []) if isinstance(row, dict)]

    if not opportunities and rows:
        try:
            state = realtime_state_builder(rows) or {}
            opportunities = [row for row in (state.get("opportunities") or []) if isinstance(row, dict)]
        except Exception as exc:
            logger.debug("Predictions intelligence fallback used: %s", exc)

    enriched_rows = normalize_prediction_rows(
        merge_prediction_rows_with_intelligence(
            rows,
            opportunities,
            normalize_symbol=normalize_symbol,
        )
    )
    performance = (
        (state_cache.get("PREDICTION_STATE", {}) or {})
        .get("system_cache", {})
        .get("ai_performance", {})
        or {}
    )

    return {
        "success": True,
        "opportunities": opportunities[:top_n],
        "rows": enriched_rows[:top_n],
        "stocks": enriched_rows[:top_n],
        "predictions": enriched_rows[:top_n],
        "market_regime": (
            state.get("current_regime")
            or ((state.get("market_state") or {}).get("regime"))
            or performance.get("regime")
            or "UNKNOWN"
        ),
        "global_accuracy": performance.get("accuracy", 0.0),
        "models_active": performance.get("active_models", 0),
        "timestamp": ai_engine_state.get("last_update") or datetime.now(ZoneInfo("UTC")).isoformat(),
    }
