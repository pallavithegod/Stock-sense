"""Presentation helpers for prediction API rows.

This module is intentionally pure: no Flask imports, no cache writes, and no
network calls. Routes can use it to expose a stable frontend contract without
changing prediction generation or dashboard state.
"""

from __future__ import annotations

from typing import Any, Mapping


PredictionMapping = Mapping[str, Any]
DISPLAY_HORIZON = "6m"


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    if hasattr(value, "size") and hasattr(value, "tolist"):
        try:
            if value.size == 0:
                return False
            if value.size == 1:
                return _is_present(value.tolist())
        except Exception:
            return False
    return True


def _first_present(*values: Any) -> Any:
    for value in values:
        if _is_present(value):
            return value
    return None


def _to_float(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    if hasattr(value, "size") and hasattr(value, "tolist"):
        try:
            if value.size == 0:
                return default
            value = value.tolist()
            while isinstance(value, list) and len(value) == 1:
                value = value[0]
        except Exception:
            return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _horizon_value(row: PredictionMapping, *keys: str, preferred_horizon: str = DISPLAY_HORIZON) -> Any:
    predictions = row.get("predictions")
    if not isinstance(predictions, Mapping):
        return None

    horizons = (preferred_horizon, "1y", "3m", "15d", "1d")
    for horizon in dict.fromkeys(horizons):
        item = predictions.get(horizon)
        if not isinstance(item, Mapping):
            continue
        value = _first_present(*(item.get(key) for key in keys))
        if _is_present(value):
            return value
    return None


def _positive_float(*values: Any, default: float = 0.0) -> float:
    fallback = default
    for value in values:
        numeric = _to_float(value, None)
        if numeric is None:
            continue
        fallback = numeric
        if numeric > 0:
            return numeric
    return fallback


def normalize_prediction_row(row: PredictionMapping | None) -> dict[str, Any]:
    """Return a stable display contract for prediction tables.

    Required display fields:
    symbol, signal, current_price, target_price, expected_return, confidence,
    allocation_pct, risk_level.
    """

    source = dict(row or {})
    prediction = source.get("prediction") if isinstance(source.get("prediction"), Mapping) else {}

    current_price = _to_float(
        _first_present(
            source.get("current_price"),
            source.get("price"),
            source.get("actual_price"),
            prediction.get("current_price"),
        ),
        None,
    )
    target_price = _to_float(
        _first_present(
            source.get("target_6m"),
            prediction.get("target_6m"),
            _horizon_value(source, "target_price", "target"),
            _horizon_value(prediction, "target_price", "target"),
            source.get("target_price"),
            prediction.get("target_price"),
            source.get("target"),
            source.get("target_1y"),
            prediction.get("target_1y"),
        ),
        None,
    )
    expected_return = _to_float(
        _first_present(
            _horizon_value(source, "return_percent", "return_pct", "expected_return"),
            _horizon_value(prediction, "return_percent", "return_pct", "expected_return"),
            source.get("expected_return"),
            source.get("expectedReturn"),
            prediction.get("expected_return"),
            source.get("predicted_return"),
            prediction.get("predicted_return"),
            source.get("return_percent"),
            source.get("return_pct"),
        ),
        None,
    )

    if expected_return is None and current_price not in (None, 0) and target_price is not None:
        expected_return = ((target_price - current_price) / current_price) * 100

    confidence = _positive_float(
        source.get("confidence"),
        source.get("confidence_score"),
        prediction.get("confidence"),
        source.get("probability"),
        source.get("certainty"),
        default=0.0,
    )
    allocation = _to_float(
        _first_present(
            source.get("allocation_pct"),
            source.get("ai_size"),
            source.get("weight_pct"),
            source.get("recommended_position_size"),
            source.get("kelly_fraction"),
            source.get("allocation"),
        ),
        0.0,
    )
    risk_level = _first_present(
        source.get("risk_level"),
        source.get("risk"),
        prediction.get("risk_level"),
        prediction.get("risk"),
        source.get("no_trade_reason"),
        "DEGRADED"
        if "FAILED" in f"{source.get('models_used', '')} {prediction.get('models_used', '')}".upper()
        else None,
        "LOW",
    )

    source.update(
        {
            "symbol": str(_first_present(source.get("symbol"), "UNKNOWN")),
            "signal": str(_first_present(source.get("signal"), source.get("action"), source.get("direction"), "WATCH")),
            "current_price": current_price,
            "price": current_price,
            "target_price": target_price,
            "target": target_price,
            "expected_return": expected_return,
            "return_percent": expected_return,
            "predicted_return": expected_return,
            "confidence": confidence,
            "allocation_pct": allocation,
            "ai_size": allocation,
            "weight_pct": allocation,
            "risk_level": str(risk_level).upper() if risk_level is not None else "LOW",
            "risk": str(risk_level).upper() if risk_level is not None else "LOW",
            "display_horizon": DISPLAY_HORIZON,
        }
    )
    return source


def normalize_prediction_rows(rows: list[PredictionMapping] | tuple[PredictionMapping, ...] | None) -> list[dict[str, Any]]:
    return [normalize_prediction_row(row) for row in (rows or [])]
