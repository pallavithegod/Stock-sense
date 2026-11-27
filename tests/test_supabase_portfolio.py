from __future__ import annotations

from backend.domain.portfolio.supabase_repository import SupabasePortfolioRepository
from backend.services.supabase_auth import AuthenticatedUser


class FakeResponse:
    def __init__(self, value):
        self.value = value
        self.status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return self.value


class FakeSession:
    def __init__(self):
        self.requests = []
        self.posts = []

    def request(self, method, url, **kwargs):
        self.requests.append((method, url, kwargs))
        return FakeResponse(
            [
                {
                    "id": "lot-1",
                    "symbol": "INFY",
                    "buy_date": "2025-01-01",
                    "buy_price": 100,
                    "original_quantity": 2,
                    "remaining_quantity": 2,
                    "remaining_fees": 0,
                }
            ]
        )

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        return FakeResponse({"status": "ok", "realized_gain": 24})


def test_supabase_buy_uses_authenticated_rpc_and_idempotency_key():
    session = FakeSession()
    repository = SupabasePortfolioRepository(
        supabase_url="https://project.supabase.co",
        publishable_key="sb_publishable_test",
        secret_key="sb_secret_test",
        local_db_path="unused.db",
        session=session,
        verify_remote_schema=False,
    )
    user = AuthenticatedUser(
        user_id="00000000-0000-0000-0000-000000000001",
        email="user@example.com",
        access_token="user-access-token",
    )

    result = repository.add_to_portfolio(
        "INFY",
        2,
        100,
        purchase_date="2025-01-01",
        principal=user,
        idempotency_key="buy-key",
    )

    assert result is None
    url, request = session.posts[0]
    assert url.endswith("/rest/v1/rpc/record_portfolio_buy")
    assert request["headers"]["apikey"] == "sb_publishable_test"
    assert request["headers"]["Authorization"] == "Bearer user-access-token"
    assert request["json"]["p_idempotency_key"] == "buy-key"
    assert request["json"]["p_trade_date"] == "2025-01-01"


def test_supabase_sell_validates_lots_then_calls_authenticated_atomic_rpc():
    session = FakeSession()
    repository = SupabasePortfolioRepository(
        supabase_url="https://project.supabase.co",
        publishable_key="sb_publishable_test",
        secret_key="sb_secret_test",
        local_db_path="unused.db",
        session=session,
        verify_remote_schema=False,
    )
    user = AuthenticatedUser(
        user_id="00000000-0000-0000-0000-000000000001",
        email="user@example.com",
        access_token="user-access-token",
    )

    result = repository.record_sell(
        "INFY",
        1,
        125,
        sell_date="2025-02-01",
        fees=1,
        method="FIFO",
        principal=user,
    )

    assert result["realized_gain"] == 24
    assert session.requests[0][1].endswith("/rest/v1/portfolio_lots")
    url, request = session.posts[0]
    assert url.endswith("/rest/v1/rpc/record_portfolio_sell")
    assert request["headers"]["Authorization"] == "Bearer user-access-token"
    assert request["json"]["p_method"] == "FIFO"
    assert request["json"]["p_idempotency_key"] is None


def test_supabase_idempotent_sell_retry_reaches_rpc_without_open_lots():
    session = FakeSession()
    session.request = lambda *args, **kwargs: FakeResponse([])
    repository = SupabasePortfolioRepository(
        supabase_url="https://project.supabase.co",
        publishable_key="sb_publishable_test",
        secret_key="sb_secret_test",
        local_db_path="unused.db",
        session=session,
        verify_remote_schema=False,
    )
    user = AuthenticatedUser(
        user_id="00000000-0000-0000-0000-000000000001",
        email="user@example.com",
        access_token="user-access-token",
    )

    result = repository.record_sell(
        "INFY",
        2,
        125,
        sell_date="2025-02-01",
        method="FIFO",
        principal=user,
        idempotency_key="retry-key",
    )

    assert result["status"] == "ok"
    assert session.posts[0][1]["json"]["p_idempotency_key"] == "retry-key"
