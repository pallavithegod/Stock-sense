from __future__ import annotations

import time
from typing import Any

import pytest

from backend.services.market_data import (
    FakeMarketDataProvider,
    MarketDataRequest,
    ProviderPolicy,
    ProviderResponse,
    ResilientMarketDataClient,
    YFinanceMarketDataProvider,
    exchange_candidates,
)


class SlowProvider(FakeMarketDataProvider):
    def quote(self, symbol: str) -> ProviderResponse:
        time.sleep(0.05)
        return super().quote(symbol)


def _client(provider: Any, **policy_overrides: Any) -> ResilientMarketDataClient:
    defaults = {
        "timeout_seconds": 0.01,
        "max_retries": 0,
        "retry_jitter_seconds": 0,
        "cache_ttl_seconds": 0.01,
        "stale_ttl_seconds": 60,
        "circuit_breaker_threshold": 2,
        "circuit_breaker_cooldown_seconds": 60,
    }
    defaults.update(policy_overrides)
    return ResilientMarketDataClient([provider], policy=ProviderPolicy(**defaults))


def test_provider_timeout_returns_sanitized_unavailable_state():
    client = _client(SlowProvider(quotes={"INFY": {"price": 100, "current_price": 100}}))

    response = client.quote("INFY")

    assert response.state == "unavailable"
    assert response.error_code == "ALL_PROVIDERS_UNAVAILABLE"
    assert response.quality_status == "unavailable"


def test_yfinance_adapter_marks_empty_frame_without_raw_exception_text():
    class EmptyFrame:
        empty = True

    adapter = YFinanceMarketDataProvider()

    response = adapter._history_payload_from_frame("INFY", EmptyFrame())

    assert response.state == "unavailable"
    assert response.error_code == "EMPTY_RESPONSE"
    assert response.data == []


def test_yfinance_adapter_marks_malformed_quote_and_history():
    class MalformedFrame:
        empty = False
        columns = ["Open"]

    adapter = YFinanceMarketDataProvider()

    quote = adapter._quote_payload_from_info("INFY", "INFY.NS", {"last_price": "not-a-number"})
    history = adapter._history_payload_from_frame("INFY", MalformedFrame())

    assert quote.state == "unavailable"
    assert quote.error_code == "MALFORMED_RESPONSE"
    assert history.state == "unavailable"
    assert history.error_code == "MALFORMED_RESPONSE"


def test_stale_while_revalidate_returns_cached_stale_during_provider_outage():
    provider = FakeMarketDataProvider(quotes={"INFY": {"price": 100, "current_price": 100}})
    client = _client(provider, cache_ttl_seconds=0.01, stale_ttl_seconds=60)

    live = client.quote("INFY")
    provider.failures["quote"] = "TOTAL_OUTAGE"
    time.sleep(0.02)
    stale = client.quote("INFY", allow_stale=True)

    assert live.state == "live"
    assert stale.state == "cached_stale"
    assert stale.data["price"] == 100
    assert stale.stale is True


def test_exchange_candidates_try_nse_before_bse_and_yfinance_falls_back(monkeypatch):
    class FakeTicker:
        def __init__(self, symbol: str):
            self.symbol = symbol
            self.fast_info = {} if symbol.endswith(".NS") else {"last_price": 123.45}

    class FakeYFinance:
        @staticmethod
        def Ticker(symbol: str) -> FakeTicker:
            return FakeTicker(symbol)

    adapter = YFinanceMarketDataProvider()
    monkeypatch.setattr(adapter, "_yf", lambda: FakeYFinance)

    response = adapter.quote("INFY")

    assert exchange_candidates("INFY") == ["INFY.NS", "INFY.BO"]
    assert response.state == "live"
    assert response.data["display"] == "INFY.BO"
    assert response.data["price"] == 123.45


def test_cache_key_includes_provider_symbol_interval_and_period():
    request = MarketDataRequest("history", symbol="INFY.NS", period="1y", interval="1d")

    assert request.cache_key("yfinance") == "yfinance|history|INFY|1y|1d||"


def test_total_provider_outage_is_explicit_and_circuit_health_is_sanitized():
    provider = FakeMarketDataProvider(failures={"quote": "TOTAL_OUTAGE"})
    client = _client(provider, circuit_breaker_threshold=1)

    response = client.quote("INFY")
    health = client.health()["fake"]

    assert response.state == "unavailable"
    assert response.error_code == "ALL_PROVIDERS_UNAVAILABLE"
    assert health["circuit"] == "open"
    assert health["last_error_code"] == "TOTAL_OUTAGE"


def test_dashboard_and_search_remain_usable_with_network_disabled(client):
    search = client.get("/api/search", query_string={"q": "INFY"})
    dashboard = client.get("/api/dashboard-data/live")
    status = client.get("/api/system/status")

    assert search.status_code == 200
    assert search.get_json()["results"][0]["symbol"] == "INFY"
    assert dashboard.status_code == 200
    assert dashboard.get_json()["data_quality"] == "unavailable"
    provider_health = status.get_json()["startup_checks"]["market_data_providers"]
    assert provider_health["unavailable"]["status"] == "disabled"
