"""Compatibility launcher for the StockSense Flask application."""

from __future__ import annotations

from backend.app import create_app, run_dev, socketio


app = create_app()


if __name__ == "__main__":
    run_dev(app)
