"""Central HTTP error mapping for the Flask application factory."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import jsonify
from werkzeug.exceptions import HTTPException


class StockSenseError(Exception):
    status_code = 400
    code = "STOCKSENSE_ERROR"

    def __init__(self, message: str, *, status_code: int | None = None, code: str | None = None):
        super().__init__(message)
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


def _error_payload(*, message: str, code: str, status: int):
    return {
        "success": False,
        "error": message,
        "code": code,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def register_error_handlers(app) -> None:
    @app.errorhandler(StockSenseError)
    def handle_domain_error(exc: StockSenseError):
        return jsonify(_error_payload(message=str(exc), code=exc.code, status=exc.status_code)), exc.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(exc: HTTPException):
        status_code = int(exc.code or 500)
        return jsonify(_error_payload(message=exc.description, code=exc.name.upper().replace(" ", "_"), status=status_code)), status_code
