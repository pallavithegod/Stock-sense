"""Canonical prediction entities and correctness helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Protocol

from backend.domain.market import normalize_symbol


PredictionSourceType = Literal[
    "ml_model",
    "statistical",
    "heuristic",
    "sentiment_llm",
    "synthetic_demo",
    "presentation_intelligence",
    "unavailable",
]

SOURCE_TYPES: set[str] = {
    "ml_model",
    "statistical",
    "heuristic",
    "sentiment_llm",
    "synthetic_demo",
    "presentation_intelligence",
    "unavailable",
}

HORIZON_DAYS = {
    "1d": 1,
    "5d": 5,
    "15d": 15,
    "1m": 30,
    "3m": 90,
    "6m": 182,
    "1y": 365,
}


class PredictionModel(Protocol):
    model_version: str
    feature_version: str
    trained_at: str | None
    evaluation_metrics: dict[str, Any]

    def predict(self, features: dict[str, Any]) -> "CanonicalPrediction":
        ...


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_utc(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def float_or_none(value: Any) -> float | None:
    if value is None or value == "" or value == "--":
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if numeric == numeric else None


def source_type_from(value: Any, *, is_synthetic: bool = False, is_demo: bool = False) -> PredictionSourceType:
    if is_synthetic or is_demo:
        return "synthetic_demo"
    normalized = str(value or "").strip().lower()
    aliases = {
        "ml": "ml_model",
        "model": "ml_model",
        "technical": "heuristic",
        "rule": "heuristic",
        "rules": "heuristic",
        "sentiment": "sentiment_llm",
        "presentation": "presentation_intelligence",
        "cache": "presentation_intelligence",
    }
    candidate = aliases.get(normalized, normalized)
    return candidate if candidate in SOURCE_TYPES else "unavailable"  # type: ignore[return-value]


def maturity_date(as_of: Any, horizon: str) -> str | None:
    parsed = parse_utc(as_of)
    days = HORIZON_DAYS.get(str(horizon or "").lower())
    if parsed is None or days is None:
        return None
    return (parsed + timedelta(days=days)).isoformat()


def is_matured(as_of: Any, horizon: str, *, evaluated_at: Any) -> bool:
    parsed = parse_utc(maturity_date(as_of, horizon))
    evaluation_time = parse_utc(evaluated_at)
    return bool(parsed and evaluation_time and evaluation_time >= parsed)


@dataclass(frozen=True)
class PredictionProvenance:
    source_type: PredictionSourceType
    provider: str
    data_quality: str
    model_version: str | None = None
    feature_version: str | None = None
    trained_at: str | None = None
    is_synthetic: bool = False
    is_demo: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "provider": self.provider,
            "data_quality": self.data_quality,
            "model_version": self.model_version,
            "feature_version": self.feature_version,
            "trained_at": self.trained_at,
            "is_synthetic": self.is_synthetic,
            "is_demo": self.is_demo,
        }


@dataclass(frozen=True)
class CanonicalPrediction:
    symbol: str
    horizon: str
    as_of: str
    current_price: float | None
    target_price: float | None
    expected_return: float | None
    signal: str
    confidence: float | None
    risk: str | None
    provenance: PredictionProvenance

    @property
    def model_version(self) -> str | None:
        return self.provenance.model_version

    @property
    def source_type(self) -> PredictionSourceType:
        return self.provenance.source_type

    @property
    def fingerprint(self) -> str:
        material = {
            "symbol": self.symbol,
            "horizon": self.horizon,
            "as_of": self.as_of,
            "current_price": self.current_price,
            "target_price": self.target_price,
            "signal": self.signal,
            "source_type": self.provenance.source_type,
            "provider": self.provenance.provider,
            "model_version": self.provenance.model_version,
            "feature_version": self.provenance.feature_version,
        }
        encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @property
    def matured_at(self) -> str | None:
        return maturity_date(self.as_of, self.horizon)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "symbol": self.symbol,
            "horizon": self.horizon,
            "as_of": self.as_of,
            "current_price": self.current_price,
            "target_price": self.target_price,
            "expected_return": self.expected_return,
            "signal": self.signal,
            "confidence": self.confidence,
            "risk": self.risk,
            "matured_at": self.matured_at,
            "fingerprint": self.fingerprint,
            **self.provenance.to_dict(),
        }
        payload["idempotency_key"] = self.fingerprint
        return payload


def canonicalize_prediction(row: dict[str, Any], *, default_horizon: str = "6m") -> CanonicalPrediction | None:
    symbol = normalize_symbol(row.get("symbol"))
    if not symbol:
        return None

    prediction = row.get("prediction") if isinstance(row.get("prediction"), dict) else {}
    horizon = str(row.get("horizon") or prediction.get("horizon") or default_horizon).lower()
    current_price = float_or_none(
        row.get("current_price")
        or row.get("price")
        or prediction.get("current_price")
        or prediction.get("price")
    )
    target_price = float_or_none(
        row.get("target_price")
        or row.get("target_6m")
        or prediction.get("target_price")
        or prediction.get("target_6m")
    )
    explicit_return = float_or_none(
        row.get("expected_return")
        or row.get("predicted_return")
        or row.get("return_percent")
        or prediction.get("expected_return")
        or prediction.get("predicted_return")
        or prediction.get("return_percent")
    )
    expected_return = explicit_return
    if expected_return is None and current_price not in (None, 0) and target_price is not None:
        expected_return = ((target_price - current_price) / current_price) * 100

    is_synthetic = bool(row.get("is_synthetic") or row.get("synthetic") or str(row.get("data_source") or "").lower() == "synthetic")
    is_demo = bool(row.get("is_demo") or row.get("demo"))
    source_type = source_type_from(row.get("source_type") or row.get("source"), is_synthetic=is_synthetic, is_demo=is_demo)
    data_quality = row.get("data_quality") or ("demo" if source_type == "synthetic_demo" else "unavailable")
    as_of = parse_utc(row.get("as_of") or row.get("timestamp") or row.get("created_at")) or datetime.now(timezone.utc)

    return CanonicalPrediction(
        symbol=symbol,
        horizon=horizon,
        as_of=as_of.isoformat(),
        current_price=current_price,
        target_price=target_price,
        expected_return=expected_return,
        signal=str(row.get("signal") or row.get("action") or row.get("direction") or "WATCH"),
        confidence=float_or_none(row.get("confidence") or row.get("confidence_score") or prediction.get("confidence")),
        risk=row.get("risk") or row.get("risk_level") or prediction.get("risk") or prediction.get("risk_level"),
        provenance=PredictionProvenance(
            source_type=source_type,
            provider=str(row.get("provider") or "local_prediction_cache"),
            data_quality=str(data_quality),
            model_version=row.get("model_version"),
            feature_version=row.get("feature_version"),
            trained_at=parse_utc(row.get("trained_at")).isoformat() if parse_utc(row.get("trained_at")) else None,
            is_synthetic=is_synthetic or source_type == "synthetic_demo",
            is_demo=is_demo or source_type == "synthetic_demo",
        ),
    )


def canonicalize_predictions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    canonical_rows = []
    seen: set[str] = set()
    for row in rows:
        canonical = canonicalize_prediction(row)
        if canonical is None:
            continue
        key = canonical.fingerprint
        if key in seen:
            continue
        seen.add(key)
        canonical_rows.append(canonical.to_dict())
    return canonical_rows


def evaluate_prediction(prediction: CanonicalPrediction, *, actual_price: float | None, evaluated_at: Any) -> dict[str, Any]:
    if not is_matured(prediction.as_of, prediction.horizon, evaluated_at=evaluated_at):
        return {
            "fingerprint": prediction.fingerprint,
            "matured": False,
            "directional_accuracy": None,
            "target_error": None,
            "calibration_error": None,
            "coverage": 0,
        }
    if actual_price is None or prediction.current_price is None or prediction.target_price is None:
        return {
            "fingerprint": prediction.fingerprint,
            "matured": True,
            "directional_accuracy": None,
            "target_error": None,
            "calibration_error": None,
            "coverage": 0,
        }
    predicted_direction = prediction.target_price - prediction.current_price
    actual_direction = actual_price - prediction.current_price
    directional_accuracy = 1.0 if predicted_direction == 0 and actual_direction == 0 else 1.0 if predicted_direction * actual_direction > 0 else 0.0
    target_error = abs(actual_price - prediction.target_price) / actual_price if actual_price else None
    confidence = (prediction.confidence or 0) / 100
    calibration_error = abs(confidence - directional_accuracy)
    return {
        "fingerprint": prediction.fingerprint,
        "matured": True,
        "directional_accuracy": directional_accuracy,
        "target_error": target_error,
        "calibration_error": calibration_error,
        "coverage": 1,
    }


def summarize_evaluations(evaluations: list[dict[str, Any]]) -> dict[str, Any]:
    matured = [row for row in evaluations if row.get("matured")]
    covered = [row for row in matured if row.get("coverage") == 1]

    def average(key: str) -> float | None:
        values = [float(row[key]) for row in covered if row.get(key) is not None]
        return sum(values) / len(values) if values else None

    return {
        "matured_predictions": len(matured),
        "evaluated_predictions": len(covered),
        "directional_accuracy": average("directional_accuracy"),
        "target_error": average("target_error"),
        "calibration_error": average("calibration_error"),
        "coverage": len(covered) / len(matured) if matured else 0,
    }


class HeuristicSignalService:
    provider = "heuristic_signal_service"
    model_version = None
    feature_version = "heuristic-v1"
    trained_at = None
    evaluation_metrics: dict[str, Any] = {}

    def predict(self, features: dict[str, Any]) -> CanonicalPrediction:
        symbol = normalize_symbol(features.get("symbol")) or "UNKNOWN"
        current_price = float_or_none(features.get("current_price"))
        target_price = float_or_none(features.get("target_price"))
        return canonicalize_prediction(
            {
                "symbol": symbol,
                "horizon": features.get("horizon") or "6m",
                "as_of": features.get("as_of") or utc_now_iso(),
                "current_price": current_price,
                "target_price": target_price,
                "signal": features.get("signal") or "WATCH",
                "confidence": features.get("confidence"),
                "risk": features.get("risk"),
                "source_type": "heuristic",
                "provider": self.provider,
                "data_quality": "heuristic",
                "feature_version": self.feature_version,
            }
        )


class DemoPredictionProvider:
    def __init__(self, *, enabled: bool = False):
        self.enabled = enabled

    def predict(self, features: dict[str, Any]) -> CanonicalPrediction | None:
        if not self.enabled:
            return None
        row = dict(features)
        row.update({
            "source_type": "synthetic_demo",
            "provider": "demo_prediction_provider",
            "data_quality": "demo",
            "is_synthetic": True,
            "is_demo": True,
        })
        return canonicalize_prediction(row)
