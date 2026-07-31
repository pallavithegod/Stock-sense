"""Public health endpoints with sanitized readiness details."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify

from backend.app.services import AppServices


def create_health_blueprint() -> Blueprint:
    blueprint = Blueprint("health", __name__)

    @blueprint.get("/health/live")
    def live():
        return jsonify({"status": "ok", "service": "stocksense-api"})

    @blueprint.get("/health/ready")
    def ready():
        services: AppServices = current_app.extensions["stocksense_services"]
        checks = services.system.startup_checks()
        database_ok = bool(checks.get("database", {}).get("ok", False))
        startup_complete = bool(current_app.config.get("_STARTUP_COMPLETE", False))
        ready_ok = database_ok and startup_complete
        payload = {
            "status": "ready" if ready_ok else "not_ready",
            "checks": {
                "startup": startup_complete,
                "database": database_ok,
                "workers_optional": True,
                "providers_optional": True,
            },
        }
        return jsonify(payload), 200 if ready_ok else 503

    return blueprint
