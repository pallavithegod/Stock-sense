"""Thin system, analytics, and diagnostic routes."""

from flask import Blueprint, jsonify

from backend.domain.system import SystemService


def create_system_blueprint(*, system_service: SystemService) -> Blueprint:
    blueprint = Blueprint("system", __name__)

    @blueprint.get("/api/system/status")
    def system_status():
        return jsonify(system_service.status_payload())

    @blueprint.get("/api/analytics")
    def analytics():
        return jsonify(system_service.analytics_payload())

    @blueprint.get("/api/system/cognition")
    def cognition():
        return jsonify(system_service.cognition_payload())

    @blueprint.get("/api/diagnostics")
    def diagnostics():
        return jsonify(system_service.diagnostics_payload())

    @blueprint.get("/api/bootstrap/status")
    def bootstrap_status():
        return jsonify(system_service.bootstrap_payload())

    @blueprint.get("/api/intelligence/status")
    def intelligence_status():
        return jsonify(system_service.intelligence_status_payload())

    return blueprint
