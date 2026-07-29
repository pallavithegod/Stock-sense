"""Prediction generation and persistence boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.domain.predictions.entities import CanonicalPrediction, PredictionModel


@dataclass
class PredictionPersistence:
    rows: dict[str, CanonicalPrediction] = field(default_factory=dict)

    def persist_once(self, prediction: CanonicalPrediction) -> bool:
        if prediction.fingerprint in self.rows:
            return False
        self.rows[prediction.fingerprint] = prediction
        return True


class UnavailablePredictionPipeline:
    status = "unavailable"

    def generate(self, features: dict[str, Any]) -> CanonicalPrediction | None:
        return None


class PredictionPipeline:
    def __init__(self, *, models: list[PredictionModel], persistence: PredictionPersistence):
        self.models = models
        self.persistence = persistence

    def generate_and_persist(self, features: dict[str, Any]) -> CanonicalPrediction | None:
        if not self.models:
            return None
        prediction = self.models[0].predict(features)
        self.persistence.persist_once(prediction)
        return prediction
