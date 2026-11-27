from __future__ import annotations

import uuid

import pytest

from backend.domain.portfolio.supabase_repository import SupabasePortfolioRepository
from backend.services.supabase_auth import (
    AuthenticatedUser,
    AuthProviderUnavailable,
    InvalidAccessToken,
    SupabaseAuthClient,
)


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | list):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self.payload = payload

    def json(self):
        return self.payload

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(f"Unexpected HTTP status: {self.status_code}")


def test_supabase_auth_resolves_verified_user_identity():
    user_id = str(uuid.uuid4())

    class FakeSession:
        def get(self, url, **kwargs):
            assert url == "https://project.supabase.co/auth/v1/user"
            assert kwargs["headers"]["apikey"] == "sb_publishable_test"
            assert kwargs["headers"]["Authorization"] == "Bearer valid-token"
            return FakeResponse(200, {"id": user_id, "email": "user@example.com"})

    user = SupabaseAuthClient(
        supabase_url="https://project.supabase.co",
        publishable_key="sb_publishable_test",
        session=FakeSession(),
    ).get_user("valid-token")

    assert user == AuthenticatedUser(user_id, "user@example.com", "valid-token")


def test_supabase_auth_distinguishes_invalid_token_from_provider_outage():
    class FakeSession:
        def __init__(self, status_code):
            self.status_code = status_code

        def get(self, url, **kwargs):
            return FakeResponse(self.status_code, {})

    auth_client = SupabaseAuthClient(
        supabase_url="https://project.supabase.co",
        publishable_key="sb_publishable_test",
        session=FakeSession(401),
    )
    with pytest.raises(InvalidAccessToken):
        auth_client.get_user("expired-token")

    auth_client.session = FakeSession(503)
    with pytest.raises(AuthProviderUnavailable):
        auth_client.get_user("valid-token")


def test_supabase_portfolio_queries_are_scoped_to_the_verified_user(tmp_path):
    user_id = str(uuid.uuid4())

    class FakeSession:
        def __init__(self):
            self.calls = []
            self.posts = []

        def request(self, method, url, **kwargs):
            self.calls.append((method, url, kwargs))
            return FakeResponse(200, [])

        def post(self, url, **kwargs):
            self.posts.append((url, kwargs))
            return FakeResponse(200, {"status": "ok"})

    session = FakeSession()
    repository = SupabasePortfolioRepository(
        supabase_url="https://project.supabase.co",
        publishable_key="sb_publishable_test",
        secret_key="sb_secret_test",
        local_db_path=tmp_path / "stocksense.db",
        session=session,
        verify_remote_schema=False,
    )
    user = AuthenticatedUser(user_id, "user@example.com", "user-access-token")

    repository.get_portfolio(user)
    repository.add_to_portfolio("INFY", 3, 1250, principal=user)

    (get_call,) = session.calls
    assert get_call[0] == "GET"
    assert get_call[2]["params"]["user_id"] == f"eq.{user_id}"
    assert get_call[2]["headers"]["apikey"] == "sb_publishable_test"
    assert get_call[2]["headers"]["Authorization"] == "Bearer user-access-token"
    url, rpc_call = session.posts[0]
    assert url.endswith("/rest/v1/rpc/record_portfolio_buy")
    assert rpc_call["json"]["p_symbol"] == "INFY"
    assert rpc_call["headers"]["apikey"] == "sb_publishable_test"
    assert rpc_call["headers"]["Authorization"] == "Bearer user-access-token"


def test_supabase_portfolio_repository_rejects_missing_user(tmp_path):
    repository = SupabasePortfolioRepository(
        supabase_url="https://project.supabase.co",
        publishable_key="sb_publishable_test",
        secret_key="sb_secret_test",
        local_db_path=tmp_path / "stocksense.db",
        verify_remote_schema=False,
    )

    with pytest.raises(RuntimeError, match="verified user"):
        repository.get_portfolio()


def test_supabase_schema_check_uses_secret_key_only_as_apikey(tmp_path):
    class FakeSession:
        def __init__(self):
            self.headers = None

        def get(self, url, **kwargs):
            self.headers = kwargs["headers"]
            return FakeResponse(200, [])

    session = FakeSession()
    repository = SupabasePortfolioRepository(
        supabase_url="https://project.supabase.co",
        publishable_key="sb_publishable_test",
        secret_key="sb_secret_test",
        local_db_path=tmp_path / "stocksense.db",
        session=session,
    )

    repository.ensure_schema()

    assert session.headers == {"apikey": "sb_secret_test"}
