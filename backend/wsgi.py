"""Production WSGI entry point for StockSense."""

from __future__ import annotations

from backend.app import create_app, startup


app = create_app()
startup(app)
