"""System and health routes for the Flask backend."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable

from flask import Blueprint, jsonify

from backend.services.startup_checks import collect_startup_checks


def create_system_blueprint(
    *,
    project_root: Path,
    system_config: Dict[str, Any],
    feature_flags: Dict[str, Any],
    quantum_ai: Any,
    optional_modules: Iterable[str],
) -> Blueprint:
    blueprint = Blueprint("system", __name__)

    @blueprint.get("/api/system/status")
    def system_status():
        """Return backend health without requiring the frontend to know internals."""
        try:
            startup_checks = collect_startup_checks(
                project_root=project_root,
                db_path=Path(system_config.get("DB_PATH", "data/nexus.db")),
                optional_modules=optional_modules,
            )
            prediction_history = getattr(quantum_ai, "prediction_history", []) or []
            models = getattr(quantum_ai, "models", {}) or {}
            cache = getattr(quantum_ai, "cache", {}) or {}
            cache_ttl = getattr(quantum_ai, "cache_ttl", 0) or 0

            return jsonify({
                "status": "OPERATIONAL",
                "timestamp": datetime.now().isoformat(),
                "version": "NEXUS AI QUANTUM ULTIMATE V7",
                "ai_features": {
                    "machine_learning": feature_flags.get("machine_learning", False),
                    "deep_learning": feature_flags.get("deep_learning", False),
                    "technical_analysis": feature_flags.get("technical_analysis", False),
                    "sentiment_analysis": feature_flags.get("sentiment_analysis", False),
                    "reinforcement_learning": True,
                    "live_predictions": True,
                    "ensemble_models": True,
                    "zero_hardcoding": True,
                },
                "models_loaded": list(models.keys()) if models else ["Technical"],
                "data_sources": ["Yahoo Finance", "Technical Analysis", "News Feeds", "AI Models"],
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
                "startup_checks": startup_checks,
            })
        except Exception as exc:
            return jsonify({
                "success": False,
                "status": "DEGRADED",
                "error": str(exc),
                "code": "SYSTEM_STATUS_FAILED",
                "timestamp": datetime.now().isoformat(),
            }), 500

    return blueprint
