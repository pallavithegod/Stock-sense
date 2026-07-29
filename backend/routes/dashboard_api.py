"""Thin dashboard API routes."""

from __future__ import annotations

from flask import Blueprint, jsonify

from backend.domain.dashboard import DashboardService


def create_dashboard_api_blueprint(*, dashboard_service: DashboardService) -> Blueprint:
    blueprint = Blueprint("dashboard_api", __name__)

    @blueprint.get("/api/dashboard-data")
    @blueprint.get("/api/dashboard-data/live")
    @blueprint.get("/api/dashboard-data/debug")
    def dashboard_payload():
        return jsonify(dashboard_service.snapshot())

    return blueprint

