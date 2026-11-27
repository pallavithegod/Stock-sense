"""Backtest-gated statistical forecast using persisted daily close prices."""

from __future__ import annotations

import math
from typing import Any

from backend.domain.predictions.entities import CanonicalPrediction, canonicalize_prediction


MODEL_VERSION = "momentum-20d-v1"
FEATURE_VERSION = "daily-close-20d-v1"
LOOKBACK_BARS = 20
FORECAST_HORIZON_BARS = 5
MIN_HISTORY_BARS = 400
MIN_VALIDATION_SAMPLES = 60
MIN_BASELINE_IMPROVEMENT = 0.05


def _ordered_closes(bars: list[dict[str, Any]]) -> list[tuple[str, float]]:
    by_date: dict[str, float] = {}
    for row in bars:
        try:
            trading_date = str(row["trading_date"])[:10]
            close = float(row["close"])
        except (KeyError, TypeError, ValueError):
            continue
        if close > 0 and math.isfinite(close):
            by_date[trading_date] = close
    return sorted(by_date.items())


def evaluate_momentum_model(
    bars: list[dict[str, Any]],
    *,
    lookback_bars: int = LOOKBACK_BARS,
    horizon_bars: int = FORECAST_HORIZON_BARS,
    min_history_bars: int = MIN_HISTORY_BARS,
    min_validation_samples: int = MIN_VALIDATION_SAMPLES,
) -> dict[str, Any]:
    closes = _ordered_closes(bars)
    if len(closes) < min_history_bars:
        return {
            "status": "insufficient_history",
            "history_bars": len(closes),
            "required_history_bars": min_history_bars,
            "release_eligible": False,
        }

    examples: list[tuple[float, float]] = []
    for end_index in range(lookback_bars, len(closes) - horizon_bars):
        start_close = closes[end_index - lookback_bars][1]
        current_close = closes[end_index][1]
        target_close = closes[end_index + horizon_bars][1]
        predicted_log_return = math.log(current_close / start_close) * horizon_bars / lookback_bars
        actual_log_return = math.log(target_close / current_close)
        examples.append((predicted_log_return, actual_log_return))

    split_at = int(len(examples) * 0.8)
    training_count = split_at
    validation = examples[split_at:]
    if training_count == 0 or len(validation) < min_validation_samples:
        return {
            "status": "insufficient_validation",
            "history_bars": len(closes),
            "pre_validation_samples": training_count,
            "validation_samples": len(validation),
            "required_validation_samples": min_validation_samples,
            "release_eligible": False,
        }

    model_mae = sum(abs(actual - predicted) for predicted, actual in validation) / len(validation)
    baseline_mae = sum(abs(actual) for _, actual in validation) / len(validation)
    directional_accuracy = sum(
        (predicted > 0 and actual > 0) or (predicted < 0 and actual < 0) or (predicted == 0 and actual == 0)
        for predicted, actual in validation
    ) / len(validation)
    release_eligible = (
        baseline_mae > 0
        and model_mae <= baseline_mae * (1 - MIN_BASELINE_IMPROVEMENT)
        and directional_accuracy > 0.5
    )
    return {
        "status": "validated" if release_eligible else "below_baseline",
        "model_version": MODEL_VERSION,
        "feature_version": FEATURE_VERSION,
        "history_bars": len(closes),
        "pre_validation_samples": training_count,
        "validation_samples": len(validation),
        "model_mae": model_mae,
        "zero_return_baseline_mae": baseline_mae,
        "baseline_improvement": (baseline_mae - model_mae) / baseline_mae if baseline_mae else None,
        "directional_accuracy": directional_accuracy,
        "validation_scheme": "chronological_last_20_percent",
        "release_eligible": release_eligible,
    }


def forecast_if_validated(
    symbol: str,
    bars: list[dict[str, Any]],
    *,
    as_of: str | None = None,
) -> CanonicalPrediction | None:
    evaluation = evaluate_momentum_model(bars)
    if not evaluation["release_eligible"]:
        return None
    closes = _ordered_closes(bars)
    trailing = closes[-(LOOKBACK_BARS + 1):]
    if len(trailing) < LOOKBACK_BARS + 1:
        return None
    current_price = trailing[-1][1]
    log_return = math.log(trailing[-1][1] / trailing[0][1])
    expected_log_return = log_return * FORECAST_HORIZON_BARS / LOOKBACK_BARS
    target_price = current_price * math.exp(expected_log_return)
    expected_return = (target_price / current_price - 1) * 100
    signal = "BUY" if expected_return > 0.5 else "SELL" if expected_return < -0.5 else "WATCH"
    return canonicalize_prediction(
        {
            "symbol": symbol,
            "horizon": "5d",
            "as_of": as_of or trailing[-1][0],
            "current_price": current_price,
            "target_price": target_price,
            "expected_return": expected_return,
            "signal": signal,
            "confidence": None,
            "source_type": "statistical",
            "provider": "stocksense_validated_momentum",
            "data_quality": "historical_backtest_gated",
            "model_version": MODEL_VERSION,
            "feature_version": FEATURE_VERSION,
            "trained_at": None,
        }
    )
