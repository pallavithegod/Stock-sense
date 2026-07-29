"""Offline prediction evaluation helpers."""

from __future__ import annotations

from typing import Any

from backend.domain.predictions.entities import parse_utc


def chronological_train_validation_split(rows: list[dict[str, Any]], *, validation_fraction: float = 0.2) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered = sorted(rows, key=lambda row: parse_utc(row.get("as_of") or row.get("timestamp")) or parse_utc("1970-01-01T00:00:00+00:00"))
    if not ordered:
        return [], []
    validation_size = max(1, int(round(len(ordered) * validation_fraction)))
    validation_size = min(validation_size, len(ordered))
    split_at = len(ordered) - validation_size
    return ordered[:split_at], ordered[split_at:]


class FitOnTrainingOnlyScaler:
    """Small guard wrapper that makes validation/future fitting an explicit error."""

    def __init__(self, scaler: Any):
        self.scaler = scaler
        self._fit_complete = False

    def fit_training(self, rows: Any) -> "FitOnTrainingOnlyScaler":
        self.scaler.fit(rows)
        self._fit_complete = True
        return self

    def transform(self, rows: Any) -> Any:
        if not self._fit_complete:
            raise RuntimeError("Scaler must be fitted on training data before transform.")
        return self.scaler.transform(rows)

    def fit_validation(self, rows: Any) -> None:
        raise RuntimeError("Validation or future observations must not be used for scaler fitting.")
