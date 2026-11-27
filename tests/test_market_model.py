from __future__ import annotations

from datetime import date, timedelta
import math

from backend.domain.predictions.market_model import (
    evaluate_momentum_model,
    forecast_if_validated,
)
from backend.domain.predictions.service import PredictionQueryService


def trending_bars(count: int = 500) -> list[dict[str, object]]:
    rows = []
    current = 100.0
    trading_date = date(2024, 1, 1)
    for _ in range(count):
        rows.append({"trading_date": trading_date.isoformat(), "close": current})
        current *= math.exp(0.001)
        trading_date += timedelta(days=1)
    return rows


def test_momentum_model_requires_sufficient_history_and_beats_zero_return_baseline():
    assert evaluate_momentum_model(trending_bars(399))["status"] == "insufficient_history"

    evaluation = evaluate_momentum_model(trending_bars())

    assert evaluation["status"] == "validated"
    assert evaluation["release_eligible"] is True
    assert evaluation["validation_samples"] >= 60
    assert evaluation["model_mae"] < evaluation["zero_return_baseline_mae"]


def test_forecast_is_only_created_after_validation_gate_passes():
    bars = trending_bars()
    prediction = forecast_if_validated("INFY", bars)

    assert prediction is not None
    assert prediction.source_type == "statistical"
    assert prediction.confidence is None
    assert prediction.provenance.data_quality == "historical_backtest_gated"

    hidden = forecast_if_validated("INFY", trending_bars(399))
    assert hidden is None


def test_live_prediction_service_does_not_expose_unvalidated_forecasts():
    class HistoryStore:
        def read_history(self, symbol: str, *, limit: int = 500):
            return trending_bars(399)

    service = PredictionQueryService(ai_engine_state={}, market_history_store=HistoryStore())

    payload = service.live_prediction_payload("INFY")["data"]

    assert payload["predictions"] == {}
    assert payload["market_conditions"]["status"] == "insufficient_history"
    assert payload["data_quality"] == "unavailable"
    assert payload["is_synthetic"] is False
