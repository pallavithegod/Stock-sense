"""System status, diagnostics, and lightweight analytics composition."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from backend.services.startup_checks import collect_startup_checks


class SystemService:
    def __init__(
        self,
        *,
        project_root: Path,
        db_path: Path,
        feature_flags: dict[str, Any],
        runtime: Any,
        optional_modules: Iterable[str],
        provider_health: Any | None = None,
    ):
        self.project_root = Path(project_root)
        self.db_path = Path(db_path)
        self.feature_flags = feature_flags
        self.runtime = runtime
        self.optional_modules = tuple(optional_modules)
        self.provider_health = provider_health

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def startup_checks(self) -> dict[str, Any]:
        return collect_startup_checks(
            project_root=self.project_root,
            db_path=self.db_path,
            optional_modules=self.optional_modules,
            provider_health=self.provider_health() if self.provider_health else {},
        )

    def status_payload(self) -> dict[str, Any]:
        prediction_history = getattr(self.runtime, "prediction_history", []) or []
        models = getattr(self.runtime, "models", {}) or {}
        cache = getattr(self.runtime, "cache", {}) or {}
        cache_ttl = getattr(self.runtime, "cache_ttl", 0) or 0
        return {
            "status": "OPERATIONAL",
            "timestamp": self._timestamp(),
            "version": "StockSense Flask Factory",
            "ai_features": {
                "machine_learning": bool(self.feature_flags.get("machine_learning", False)),
                "deep_learning": bool(self.feature_flags.get("deep_learning", False)),
                "technical_analysis": bool(self.feature_flags.get("technical_analysis", False)),
                "sentiment_analysis": bool(self.feature_flags.get("sentiment_analysis", False)),
                "reinforcement_learning": False,
                "live_predictions": False,
                "ensemble_models": False,
                "zero_hardcoding": True,
            },
            "models_loaded": list(models.keys()) if models else ["Technical"],
            "data_sources": ["Local SQLite", "Static market universe"],
            "performance": {
                "uptime": None,
                "prediction_accuracy": None,
                "accuracy_basis": "unavailable_until_matured_predictions_are_evaluated",
                "cache_ttl_seconds": cache_ttl,
                "total_predictions": len(prediction_history),
                "mode": "local_demo",
            },
            "cache_status": {
                "entries": len(cache),
                "ttl_seconds": cache_ttl,
            },
            "startup_checks": self.startup_checks(),
        }

    def analytics_payload(self) -> dict[str, Any]:
        return {
            "success": True,
            "data_quality": "unavailable",
            "market_summary": {"total_analyzed": 0, "bullish": 0, "bearish": 0},
            "sectoranalysis": {},
            "sector_analysis": {},
            "volatility_metrics": {},
            "timestamp": self._timestamp(),
        }

    def cognition_payload(self) -> dict[str, Any]:
        return {
            "success": True,
            "data_quality": "unavailable",
            "cognitive_state": {},
            "status": "unavailable_without_active_cognition_worker",
            "timestamp": self._timestamp(),
        }

    def diagnostics_payload(self) -> dict[str, Any]:
        checks = self.startup_checks()
        return {
            "success": True,
            "status": "ok" if all(item.get("ok", False) for item in checks.values()) else "degraded",
            "checks": checks,
            "timestamp": self._timestamp(),
        }

    def bootstrap_payload(self) -> dict[str, Any]:
        return {
            "success": True,
            "workers_started": False,
            "message": "Runtime workers are not started by the Flask app factory.",
            "data_quality": "unavailable",
            "timestamp": self._timestamp(),
        }

    def intelligence_status_payload(self) -> dict[str, Any]:
        return {
            "success": True,
            "status": "available",
            "mode": "lightweight_factory_runtime",
            "data_quality": "unavailable",
            "features": self.feature_flags,
            "timestamp": self._timestamp(),
        }
