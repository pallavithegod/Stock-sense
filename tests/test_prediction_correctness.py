from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.domain.predictions.adaptive_thresholds import map_adaptive_threshold_row
from backend.domain.predictions.entities import (
    DemoPredictionProvider,
    HeuristicSignalService,
    canonicalize_prediction,
    evaluate_prediction,
    is_matured,
    summarize_evaluations,
)
from backend.domain.predictions.evaluation import FitOnTrainingOnlyScaler, chronological_train_validation_split
from backend.domain.predictions.pipeline import PredictionPersistence, PredictionPipeline
from scripts.evaluate_predictions import evaluate_fixture


def test_canonical_prediction_has_deterministic_fingerprint_and_no_zero_substitution():
    row = {
        "symbol": "infy.ns",
        "horizon": "1d",
        "as_of": "2026-07-01T00:00:00+00:00",
        "current_price": 100,
        "target_price": 110,
        "signal": "BUY",
        "source_type": "heuristic",
        "provider": "unit-test",
        "data_quality": "fixture",
    }

    first = canonicalize_prediction(row)
    second = canonicalize_prediction(dict(row))

    assert first is not None
    assert second is not None
    assert first.fingerprint == second.fingerprint
    assert first.to_dict()["idempotency_key"] == first.fingerprint
    assert first.to_dict()["confidence"] is None
    assert first.to_dict()["expected_return"] == pytest.approx(10.0)


def test_prediction_evaluation_waits_for_maturity_and_separates_metrics():
    prediction = canonicalize_prediction(
        {
            "symbol": "INFY",
            "horizon": "1d",
            "as_of": "2026-07-01T00:00:00+00:00",
            "current_price": 100,
            "target_price": 110,
            "confidence": 70,
            "signal": "BUY",
            "source_type": "heuristic",
        }
    )

    assert prediction is not None
    assert is_matured(prediction.as_of, prediction.horizon, evaluated_at="2026-07-01T12:00:00+00:00") is False
    early = evaluate_prediction(prediction, actual_price=112, evaluated_at="2026-07-01T12:00:00+00:00")
    matured = evaluate_prediction(prediction, actual_price=112, evaluated_at="2026-07-03T00:00:00+00:00")

    assert early["matured"] is False
    assert early["directional_accuracy"] is None
    assert matured["matured"] is True
    assert matured["directional_accuracy"] == 1.0
    assert matured["target_error"] == pytest.approx(2 / 112)
    assert matured["calibration_error"] == pytest.approx(0.3)


def test_offline_fixture_evaluation_is_reproducible():
    fixture = Path("tests/fixtures/predictions/evaluation_fixture.json")
    first = evaluate_fixture(fixture)
    second = evaluate_fixture(fixture)

    assert first == second
    assert first["matured_predictions"] == 2
    assert first["evaluated_predictions"] == 2
    assert first["directional_accuracy"] == 0.5


def test_pipeline_uses_one_persistence_call_and_blocks_duplicate_writes():
    service = HeuristicSignalService()
    persistence = PredictionPersistence()
    pipeline = PredictionPipeline(models=[service], persistence=persistence)
    features = {
        "symbol": "INFY",
        "as_of": "2026-07-01T00:00:00+00:00",
        "current_price": 100,
        "target_price": 105,
    }

    first = pipeline.generate_and_persist(features)
    second = pipeline.generate_and_persist(features)

    assert first is not None
    assert second is not None
    assert first.fingerprint == second.fingerprint
    assert len(persistence.rows) == 1


def test_demo_provider_is_disabled_by_default_and_labels_demo_when_enabled():
    disabled = DemoPredictionProvider()
    enabled = DemoPredictionProvider(enabled=True)

    assert disabled.predict({"symbol": "INFY"}) is None
    demo = enabled.predict({"symbol": "INFY", "current_price": 100, "target_price": 101})

    assert demo is not None
    payload = demo.to_dict()
    assert payload["source_type"] == "synthetic_demo"
    assert payload["is_synthetic"] is True
    assert payload["is_demo"] is True


def test_chronological_split_and_scaler_guard_prevent_future_leakage():
    rows = [
        {"symbol": "C", "as_of": "2026-07-03T00:00:00+00:00"},
        {"symbol": "A", "as_of": "2026-07-01T00:00:00+00:00"},
        {"symbol": "B", "as_of": "2026-07-02T00:00:00+00:00"},
    ]

    train, validation = chronological_train_validation_split(rows, validation_fraction=1 / 3)

    assert [row["symbol"] for row in train] == ["A", "B"]
    assert [row["symbol"] for row in validation] == ["C"]

    class FakeScaler:
        def fit(self, values):
            self.values = values

        def transform(self, values):
            return values

    scaler = FitOnTrainingOnlyScaler(FakeScaler())
    with pytest.raises(RuntimeError):
        scaler.fit_validation(validation)
    assert scaler.fit_training(train).transform(validation) == validation


def test_adaptive_threshold_row_mapping_uses_named_order():
    row = (2.0, 0.5, -2.0, -0.5, 0.05, 30, 70, 40, 25)

    mapped = map_adaptive_threshold_row(row).to_dict()

    assert mapped["strong_buy_threshold"] == 2.0
    assert mapped["buy_threshold"] == 0.5
    assert mapped["strong_sell_threshold"] == -2.0
    assert mapped["rsi_oversold"] == 30
    assert mapped["vol_medium_risk"] == 25


def test_fixture_file_contains_source_labels_for_every_row():
    rows = json.loads(Path("tests/fixtures/predictions/evaluation_fixture.json").read_text(encoding="utf-8"))

    assert rows
    assert all(row.get("source_type") in {"heuristic", "statistical"} for row in rows)
