from __future__ import annotations

from typing import Any

import pytest

from backend.services.daily_market_collection import (
    DailyMarketCollector,
    SupabaseDailyBarStore,
)
from backend.services.market_data import ProviderResponse


class FakeMarketData:
    def __init__(self, response: ProviderResponse):
        self.response = response
        self.requests: list[tuple[str, str, str, bool]] = []

    def history(self, symbol: str, *, period: str, interval: str, allow_stale: bool = False):
        self.requests.append((symbol, period, interval, allow_stale))
        return self.response


class FakeStore:
    def __init__(self):
        self.rows: list[dict[str, Any]] = []

    def upsert(self, rows: list[dict[str, Any]]) -> None:
        self.rows.extend(rows)


def test_daily_collector_persists_only_live_valid_bars():
    market_data = FakeMarketData(
        ProviderResponse.live(
            "fixture",
            {
                "prices": [
                    {
                        "timestamp": "2026-11-24 00:00:00+05:30",
                        "open": 100,
                        "high": 110,
                        "low": 95,
                        "close": 108,
                        "volume": 1234,
                    },
                    {
                        "timestamp": "not-a-date",
                        "open": 100,
                        "high": 110,
                        "low": 95,
                        "close": 108,
                        "volume": 1234,
                    },
                    {
                        "timestamp": "2026-11-25",
                        "open": 100,
                        "high": 90,
                        "low": 95,
                        "close": 108,
                        "volume": 1234,
                    },
                ]
            },
            fetched_at="2026-11-25T10:00:00+00:00",
        )
    )
    store = FakeStore()
    collector = DailyMarketCollector(
        market_data=market_data,
        store=store,
        symbols=["INFY.NS"],
    )

    result = collector.collect()

    assert market_data.requests == [("INFY", "5d", "1d", False)]
    assert result == {"symbols_requested": 1, "symbols_failed": 0, "bars_upserted": 1}
    assert store.rows == [
        {
            "symbol": "INFY",
            "trading_date": "2026-11-24",
            "open": 100.0,
            "high": 110.0,
            "low": 95.0,
            "close": 108.0,
            "volume": 1234,
            "provider": "fixture",
            "fetched_at": "2026-11-25T10:00:00+00:00",
        }
    ]


@pytest.mark.parametrize(
    "response",
    [
        ProviderResponse.unavailable("fixture", error_code="OUTAGE"),
        ProviderResponse.demo_data(
            "fixture",
            {
                "prices": [
                    {
                        "timestamp": "2026-11-24",
                        "open": 100,
                        "high": 110,
                        "low": 95,
                        "close": 108,
                        "volume": 1234,
                    }
                ]
            },
        ),
    ],
)
def test_daily_collector_does_not_store_unavailable_or_demo_prices(response):
    store = FakeStore()
    collector = DailyMarketCollector(
        market_data=FakeMarketData(response),
        store=store,
        symbols=["INFY"],
    )

    with pytest.raises(RuntimeError, match="no valid live bars"):
        collector.collect()

    assert store.rows == []


def test_supabase_store_upserts_by_symbol_and_trading_date():
    class Response:
        def raise_for_status(self):
            return None

    class Session:
        def __init__(self):
            self.call = None

        def post(self, url, **kwargs):
            self.call = (url, kwargs)
            return Response()

    session = Session()
    store = SupabaseDailyBarStore(
        supabase_url="https://project.supabase.co/",
        service_role_key="server-only-key",
        session=session,
    )
    row = {
        "symbol": "INFY",
        "trading_date": "2026-11-24",
        "open": 100.0,
        "high": 110.0,
        "low": 95.0,
        "close": 108.0,
        "volume": 1234,
        "provider": "fixture",
        "fetched_at": "2026-11-25T10:00:00+00:00",
    }

    store.upsert([row])

    assert session.call is not None
    url, kwargs = session.call
    assert url == "https://project.supabase.co/rest/v1/market_daily_bars"
    assert kwargs["params"] == {"on_conflict": "symbol,trading_date"}
    assert kwargs["headers"]["Prefer"] == "resolution=merge-duplicates,return=minimal"
    assert kwargs["json"] == [row]


def test_supabase_store_requires_server_credentials():
    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        SupabaseDailyBarStore.from_env({})
