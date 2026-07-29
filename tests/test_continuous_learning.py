from __future__ import annotations

import pytest

from continuous_learning import ContinuousLearningEngine, parse_models_used


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('["rf", "gb"]', ["rf", "gb"]),
        ("['rf', 'gb']", ["rf", "gb"]),
        ("rf, gb", ["rf", "gb"]),
        (["rf", "gb"], ["rf", "gb"]),
        (None, []),
        ("", []),
    ],
)
def test_parse_models_used_accepts_safe_legacy_formats(raw, expected):
    assert parse_models_used(raw) == expected


def test_parse_models_used_does_not_execute_database_text():
    raw = "__import__('os').system('echo unsafe')"

    assert parse_models_used(raw) == [raw]


class FakeLearningDatabase:
    def __init__(self, rows):
        self.rows = rows

    def get_recent_predictions(self, limit=500):
        return self.rows[:limit]

    def log_prediction(self, prediction):
        self.rows.append(prediction)


def test_update_model_weights_uses_safe_model_parser():
    rows = [
        {
            "models_used": '["rf", "gb"]' if index % 2 == 0 else "['rf', 'technical']",
            "actual_price": 100,
            "prediction_error": 0.1 + (index * 0.001),
        }
        for index in range(12)
    ]
    engine = ContinuousLearningEngine(FakeLearningDatabase(rows))

    engine.update_model_weights()

    weights = engine.get_model_weights()
    assert "rf" in weights
    assert "gb" in weights
    assert "technical" in weights
    assert pytest.approx(sum(weights.values()), rel=1e-6) == 1.0
