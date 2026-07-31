"""Flask extension setup for the application factory."""

from __future__ import annotations

from flask_cors import CORS
from flask_socketio import SocketIO
from werkzeug.middleware.proxy_fix import ProxyFix

from backend.services.security import install_security_headers


socketio = SocketIO()


def init_extensions(app, settings) -> None:
    if settings.trust_proxy_headers:
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=settings.trusted_proxy_count,
            x_proto=settings.trusted_proxy_count,
            x_host=settings.trusted_proxy_count,
        )

    CORS(app, resources={r"/*": {"origins": settings.cors_allowed_origins}})
    socketio.init_app(
        app,
        cors_allowed_origins=settings.socketio_cors_allowed_origins,
        async_mode=settings.socketio_async_mode,
    )
    install_security_headers(app, settings)
