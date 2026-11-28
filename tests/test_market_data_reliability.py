from __future__ import annotations

import time
from typing import Any

import pandas as pd
import pytest

from backend.services.market_data import (
    ApiKeyMarketDataProvider,
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


def test_yfinance_history_includes_validated_daily_ohlcv_rows():
    class HistoryFrame:
        empty = False
        columns = ["Open", "High", "Low", "Close", "Volume"]

        def tail(self, count):
            assert count == 250
            return self

        def iterrows(self):
            return iter(
                [
                    (
                        "2026-11-24 00:00:00+05:30",
                        {"Open": 100, "High": 110, "Low": 95, "Close": 108, "Volume": 1234},
                    ),
                    (
                        "2026-11-25 00:00:00+05:30",
                        {"Open": 100, "High": 90, "Low": 95, "Close": 108, "Volume": 1234},
                    ),
                ]
            )

    response = YFinanceMarketDataProvider()._history_payload_from_frame("INFY", HistoryFrame())

    assert response.state == "live"
    assert response.data["prices"] == [
        {
            "timestamp": "2026-11-24 00:00:00+05:30",
            "open": 100.0,
            "high": 110.0,
            "low": 95.0,
            "close": 108.0,
            "volume": 1234,
        }
    ]


def test_yfinance_history_parses_multiindex_timezone_aware_dataframe(monkeypatch):
    frame = pd.DataFrame(
        [
            [100, 110, 95, 108, 1234],
            [float("nan"), float("nan"), float("nan"), float("nan"), float("nan")],
        ],
        index=pd.DatetimeIndex(
            ["2026-11-25 00:00:00+05:30", "2026-11-26 00:00:00+05:30"]
        ),
        columns=pd.MultiIndex.from_product(
            [["Open", "High", "Low", "Close", "Volume"], ["INFY.NS"]]
        ),
    )
    calls = []

    class FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, *, period, interval):
            calls.append((self.symbol, period, interval))
            return frame if self.symbol == "INFY.NS" else pd.DataFrame()

    class FakeYFinance:
        @staticmethod
        def Ticker(symbol):
            return FakeTicker(symbol)

    adapter = YFinanceMarketDataProvider()
    monkeypatch.setattr(adapter, "_yf", lambda: FakeYFinance)

    response = adapter.history("INFY", period="1y", interval="1d")

    assert calls == [("INFY.NS", "1y", "1d")]
    assert response.state == "live"
    assert response.data["prices"] == [
        {
            "timestamp": "2026-11-25T00:00:00+05:30",
            "open": 100.0,
            "high": 110.0,
            "low": 95.0,
            "close": 108.0,
            "volume": 1234,
        }
    ]


def test_yfinance_history_retries_bse_when_nse_lookup_raises(monkeypatch, caplog):
    class HistoryFrame:
        empty = False
        columns = ["Open", "High", "Low", "Close", "Volume"]

        def tail(self, count):
            return self

        def iterrows(self):
            return iter(
                [
                    (
                        "2026-11-25 00:00:00+05:30",
                        {"Open": 100, "High": 110, "Low": 95, "Close": 108, "Volume": 1234},
                    )
                ]
            )

    calls = []

    class FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, *, period, interval):
            calls.append(self.symbol)
            if self.symbol == "INFY.NS":
                raise RuntimeError("Authorization=unit-test-secret")
            return HistoryFrame()

    class FakeYFinance:
        @staticmethod
        def Ticker(symbol):
            return FakeTicker(symbol)

    adapter = YFinanceMarketDataProvider()
    monkeypatch.setattr(adapter, "_yf", lambda: FakeYFinance)

    response = adapter.history("INFY", period="5d", interval="1d")

    assert calls == ["INFY.NS", "INFY.BO"]
    assert response.state == "live"
    assert response.data["prices"][0]["close"] == 108
    assert "Authorization=[REDACTED]" in caplog.text
    assert "unit-test-secret" not in caplog.text


def test_yfinance_history_tries_bse_when_nse_returns_empty_frame(monkeypatch):
    class EmptyFrame:
        empty = True

    class HistoryFrame:
        empty = False
        columns = ["Open", "High", "Low", "Close", "Volume"]

        def tail(self, count):
            return self

        def iterrows(self):
            return iter(
                [
                    (
                        "2026-11-25 00:00:00+05:30",
                        {"Open": 100, "High": 110, "Low": 95, "Close": 108, "Volume": 1234},
                    )
                ]
            )

    calls = []

    class FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, *, period, interval):
            calls.append(self.symbol)
            return EmptyFrame() if self.symbol == "RELIANCE.NS" else HistoryFrame()

    class FakeYFinance:
        @staticmethod
        def Ticker(symbol):
            return FakeTicker(symbol)

    adapter = YFinanceMarketDataProvider()
    monkeypatch.setattr(adapter, "_yf", lambda: FakeYFinance)

    response = adapter.history("RELIANCE", period="5d", interval="1d")

    assert calls == ["RELIANCE.NS", "RELIANCE.BO"]
    assert response.state == "live"
    assert response.data["prices"][0]["close"] == 108


def test_yfinance_history_never_falls_back_to_bare_ticker(monkeypatch):
    # The bare "INFY" ticker resolves to the USD NYSE ADR on Yahoo; it must
    # never be requested for an Indian symbol.
    class EmptyFrame:
        empty = True

    calls = []

    class FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, *, period, interval):
            calls.append(self.symbol)
            return EmptyFrame()

    class FakeYFinance:
        @staticmethod
        def Ticker(symbol):
            return FakeTicker(symbol)

    adapter = YFinanceMarketDataProvider()
    monkeypatch.setattr(adapter, "_yf", lambda: FakeYFinance)

    response = adapter.history("SBIN", period="5d", interval="1d")
    explicit = adapter.history("INFY.NS", period="5d", interval="1d")

    assert calls == ["SBIN.NS", "SBIN.BO", "INFY.NS", "INFY.BO"]
    assert response.state == "unavailable"
    assert response.error_code == "EMPTY_RESPONSE"
    assert explicit.state == "unavailable"


def _one_bar_frame():
    class HistoryFrame:
        empty = False
        columns = ["Open", "High", "Low", "Close", "Volume"]

        def tail(self, count):
            return self

        def iterrows(self):
            return iter(
                [
                    (
                        "2026-11-25 00:00:00+05:30",
                        {"Open": 100, "High": 110, "Low": 95, "Close": 108, "Volume": 1234},
                    )
                ]
            )

    return HistoryFrame()


def _currency_yfinance(currencies: dict[str, Any], calls: list[str]):
    class FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, *, period, interval):
            calls.append(self.symbol)
            return _one_bar_frame()

        def get_history_metadata(self):
            value = currencies.get(self.symbol)
            if isinstance(value, Exception):
                raise value
            return {} if value is None else {"currency": value}

    class FakeYFinance:
        @staticmethod
        def Ticker(symbol):
            return FakeTicker(symbol)

    return FakeYFinance


def test_yfinance_history_rejects_non_inr_listing_and_tries_next_exchange(monkeypatch, caplog):
    calls: list[str] = []
    adapter = YFinanceMarketDataProvider()
    fake = _currency_yfinance({"INFY.NS": "USD", "INFY.BO": "INR"}, calls)
    monkeypatch.setattr(adapter, "_yf", lambda: fake)

    response = adapter.history("INFY", period="5d", interval="1d")

    assert calls == ["INFY.NS", "INFY.BO"]
    assert response.state == "live"
    assert "yfinance_history_currency_mismatch symbol=INFY.NS currency=USD" in caplog.text


def test_yfinance_history_unavailable_when_every_listing_is_non_inr(monkeypatch):
    calls: list[str] = []
    adapter = YFinanceMarketDataProvider()
    fake = _currency_yfinance({"TCS.NS": "USD", "TCS.BO": "usd"}, calls)
    monkeypatch.setattr(adapter, "_yf", lambda: fake)

    response = adapter.history("TCS", period="1y", interval="1d")

    assert calls == ["TCS.NS", "TCS.BO"]
    assert response.state == "unavailable"
    assert response.error_code == "CURRENCY_MISMATCH"


@pytest.mark.parametrize(
    "metadata_currency",
    [None, RuntimeError("Authorization=unit-test-secret")],
    ids=["missing", "metadata-error"],
)
def test_yfinance_history_accepts_pinned_listing_when_currency_unknown(monkeypatch, caplog, metadata_currency):
    calls: list[str] = []
    adapter = YFinanceMarketDataProvider()
    fake = _currency_yfinance({"SBIN.NS": metadata_currency}, calls)
    monkeypatch.setattr(adapter, "_yf", lambda: fake)

    response = adapter.history("SBIN", period="5d", interval="1d")

    assert calls == ["SBIN.NS"]
    assert response.state == "live"
    assert "yfinance_history_currency_unknown symbol=SBIN.NS" in caplog.text
    assert "unit-test-secret" not in caplog.text


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


def test_finnhub_history_uses_alias_key_and_maps_daily_candles(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "s": "ok",
                "t": [1795478400],
                "o": [100],
                "h": [110],
                "l": [95],
                "c": [108],
                "v": [1234],
            }

    class FakeSession:
        def __init__(self):
            self.call = None

        def get(self, url, **kwargs):
            self.call = (url, kwargs)
            return FakeResponse()

    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    monkeypatch.setenv("FINNHUB_KEY", "rotated-test-key")
    session = FakeSession()
    provider = ApiKeyMarketDataProvider(
        name="finnhub",
        api_key_env="FINNHUB_API_KEY",
        api_key_aliases=("FINNHUB_KEY",),
        session=session,
    )

    result = provider.history("INFY", period="5d", interval="1d")

    assert provider.health() == {
        "configured": True,
        "status": "configured",
        "api_key_env": "FINNHUB_KEY",
    }
    assert session.call[0].endswith("/stock/candle")
    assert session.call[1]["params"]["symbol"] == "NSE:INFY"
    assert session.call[1]["params"]["token"] == "rotated-test-key"
    assert result.state == "live"
    assert result.data["prices"][0]["close"] == 108


def test_alpha_vantage_history_falls_back_to_compact_for_free_key(monkeypatch):
    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class FakeSession:
        def __init__(self):
            self.calls = []

        def get(self, url, **kwargs):
            self.calls.append(kwargs["params"])
            if kwargs["params"]["outputsize"] == "full":
                return FakeResponse({"Information": "Full outputsize is a premium endpoint"})
            return FakeResponse(
                {
                    "Time Series (Daily)": {
                        "2026-11-26": {
                            "1. open": "100",
                            "2. high": "110",
                            "3. low": "95",
                            "4. close": "108",
                            "5. volume": "1234",
                        }
                    }
                }
            )

    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
    monkeypatch.setenv("ALPHA_VANTAGE_KEY", "alpha-test-key")
    session = FakeSession()
    provider = ApiKeyMarketDataProvider(
        name="alpha_vantage",
        api_key_env="ALPHA_VANTAGE_API_KEY",
        api_key_aliases=("ALPHA_VANTAGE_KEY",),
        session=session,
    )

    result = provider.history("INFY", period="5d", interval="1d")

    assert [call["outputsize"] for call in session.calls] == ["full", "compact"]
    assert result.state == "live"
    assert result.data["prices"][0]["close"] == 108


def test_twelve_data_legacy_alias_is_detected_but_provider_is_not_implemented(monkeypatch):
    monkeypatch.delenv("TWELVE_DATA_API_KEY", raising=False)
    monkeypatch.setenv("TWELVE_DATA_KEY", "twelve-test-key")
    provider = ApiKeyMarketDataProvider(
        name="twelve_data",
        api_key_env="TWELVE_DATA_API_KEY",
        api_key_aliases=("TWELVE_DATA_KEY",),
    )

    assert provider.health() == {
        "configured": True,
        "status": "configured",
        "api_key_env": "TWELVE_DATA_KEY",
    }
    response = provider.history("INFY", period="5d", interval="1d")
    assert response.error_code == "PROVIDER_NOT_IMPLEMENTED"


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
    search = client.get("/api/v1/search", query_string={"q": "INFY"})
    dashboard = client.get("/api/v1/dashboard/live")
    status = client.get("/api/v1/system/status")

    assert search.status_code == 200
    assert search.get_json()["data"]["results"][0]["symbol"] == "INFY"
    assert dashboard.status_code == 200
    assert dashboard.get_json()["data"]["data_quality"] == "unavailable"
    provider_health = status.get_json()["data"]["startup_checks"]["market_data_providers"]
    assert provider_health["unavailable"]["status"] == "disabled"
