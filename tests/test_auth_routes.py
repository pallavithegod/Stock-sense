from __future__ import annotations

from dataclasses import replace
import uuid

from backend.domain.portfolio.exceptions import PortfolioFeatureUnavailable
from backend.services.supabase_auth import (
    AuthenticatedUser,
    AuthProviderUnavailable,
    InvalidAccessToken,
)


def test_portfolio_read_requires_a_validated_access_token(client, app_module, monkeypatch):
    services = app_module.services
    monkeypatch.setattr(services, "settings", replace(services.settings, require_auth=True))

    class FakeAuth:
        def get_user(self, token):
            if token == "unavailable":
                raise AuthProviderUnavailable("Supabase is unavailable")
            if token == "expired":
                raise InvalidAccessToken("Access token has expired")
            return AuthenticatedUser(str(uuid.uuid4()), None, token)

    monkeypatch.setattr(services, "supabase_auth", FakeAuth())

    missing = client.get("/api/v1/portfolio")
    unavailable = client.get(
        "/api/v1/portfolio",
        headers={"Authorization": "Bearer unavailable"},
    )
    expired = client.get(
        "/api/v1/portfolio",
        headers={"Authorization": "Bearer expired"},
    )
    authenticated = client.get(
        "/api/v1/portfolio",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert missing.status_code == 401
    assert missing.get_json()["code"] == "AUTH_REQUIRED"
    assert unavailable.status_code == 503
    assert unavailable.get_json()["code"] == "AUTH_UNAVAILABLE"
    assert expired.status_code == 401
    assert expired.get_json()["code"] == "INVALID_TOKEN"
    assert authenticated.status_code == 200


def test_public_dashboard_does_not_include_private_portfolio_without_auth(
    client,
    app_module,
    monkeypatch,
):
    services = app_module.services
    monkeypatch.setattr(services, "settings", replace(services.settings, require_auth=True))

    def unexpected_portfolio_read(*args, **kwargs):
        raise AssertionError("Anonymous dashboard requested private portfolio data")

    monkeypatch.setattr(services.portfolio, "list_positions", unexpected_portfolio_read)

    response = client.get("/api/v1/dashboard")

    assert response.status_code == 200
    assert response.get_json()["data"]["positions"] == []
    assert response.get_json()["data"]["portfolio"]["positions"] == []


def test_unsupported_tax_features_return_an_explicit_not_implemented_response(
    client,
    app_module,
    monkeypatch,
):
    services = app_module.services
    monkeypatch.setattr(services, "settings", replace(services.settings, require_auth=True))

    class FakeAuth:
        def get_user(self, token):
            return AuthenticatedUser(str(uuid.uuid4()), None, token)

    def unavailable(*args, **kwargs):
        raise PortfolioFeatureUnavailable("Realized gains are not available without trade history.")

    monkeypatch.setattr(services, "supabase_auth", FakeAuth())
    monkeypatch.setattr(services.portfolio, "realized_gains", unavailable)

    response = client.get(
        "/api/v1/portfolio/realized-gains",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 501
    assert response.get_json()["code"] == "FEATURE_UNAVAILABLE"
