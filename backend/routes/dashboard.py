"""Dashboard API route wiring."""

from __future__ import annotations

from typing import Callable

from flask import Blueprint


def create_dashboard_blueprint(
    *,
    dashboard_data_handler: Callable,
    live_dashboard_handler: Callable,
    debug_dashboard_handler: Callable,
) -> Blueprint:
    blueprint = Blueprint("dashboard", __name__)

    blueprint.add_url_rule(
        "/api/dashboard-data",
        view_func=dashboard_data_handler,
        methods=["GET"],
    )
    blueprint.add_url_rule(
        "/api/dashboard-data/live",
        view_func=live_dashboard_handler,
        methods=["GET"],
    )
    blueprint.add_url_rule(
        "/api/dashboard-data/debug",
        view_func=debug_dashboard_handler,
        methods=["GET"],
    )

    return blueprint
