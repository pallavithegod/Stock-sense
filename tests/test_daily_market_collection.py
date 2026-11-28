from __future__ import annotations

from typing import Any

import pytest

from backend.services.daily_market_collection import (
    DailyMarketCollector,
    PartialCollectionError,
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

    assert market_data.requests == [("INFY", "1y", "1d", False)]
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


class PerSymbolMarketData:
    def __init__(self, responses: dict[str, ProviderResponse]):
        self.responses = responses

    def history(self, symbol: str, *, period: str, interval: str, allow_stale: bool = False):
        return self.responses[symbol]


def _live_bar(close: float = 108) -> ProviderResponse:
    return ProviderResponse.live(
        "fixture",
        {
            "prices": [
                {
                    "timestamp": "2026-11-24",
                    "open": 100,
                    "high": 110,
                    "low": 95,
                    "close": close,
                    "volume": 1234,
                }
            ]
        },
        fetched_at="2026-11-25T10:00:00+00:00",
    )


def test_daily_collector_partial_failure_persists_valid_bars_then_raises():
    store = FakeStore()
    collector = DailyMarketCollector(
        market_data=PerSymbolMarketData(
            {
                "INFY": _live_bar(),
                "RELIANCE": ProviderResponse.unavailable("none", error_code="ALL_PROVIDERS_UNAVAILABLE"),
                "SBIN": _live_bar(),
                "TCS": ProviderResponse.unavailable("yfinance", error_code="CURRENCY_MISMATCH"),
            }
        ),
        store=store,
        symbols=["INFY", "RELIANCE", "SBIN", "TCS"],
    )

    with pytest.raises(PartialCollectionError) as raised:
        collector.collect()

    assert sorted(row["symbol"] for row in store.rows) == ["INFY", "SBIN"]
    assert raised.value.result == {"symbols_requested": 4, "symbols_failed": 2, "bars_upserted": 2}
    assert raised.value.failures == [
        {"symbol": "RELIANCE", "error_code": "ALL_PROVIDERS_UNAVAILABLE"},
        {"symbol": "TCS", "error_code": "CURRENCY_MISMATCH"},
    ]
    assert "RELIANCE=ALL_PROVIDERS_UNAVAILABLE" in str(raised.value)
    assert "TCS=CURRENCY_MISMATCH" in str(raised.value)


def _universe_market_data(*, failing: dict[str, str]) -> PerSymbolMarketData:
    return PerSymbolMarketData(
        {
            symbol: (
                ProviderResponse.unavailable("none", error_code=failing[symbol])
                if symbol in failing
                else _live_bar()
            )
            for symbol in ("INFY", "RELIANCE", "SBIN", "TCS")
        }
    )


@pytest.mark.parametrize(
    ("failing", "expected_exit"),
    [({"TCS": "EMPTY_RESPONSE"}, 1), ({}, 0)],
    ids=["partial-failure", "complete"],
)
def test_daily_snapshot_cli_exit_code_reflects_partial_failure(app_module, monkeypatch, capsys, failing, expected_exit):
    from backend.workers import scheduler_cli

    services = app_module.services
    store = FakeStore()
    monkeypatch.setattr(services, "market_data", _universe_market_data(failing=failing))
    monkeypatch.setitem(services.system_cache, "daily_bar_store", store)

    class App:
        extensions = {"stocksense_services": services}

    monkeypatch.setattr(scheduler_cli, "create_app", lambda settings: App())
    monkeypatch.setattr(scheduler_cli, "startup", lambda app: None)

    exit_code = scheduler_cli.main(["--once", "--job", "daily_market_snapshot"])

    output = capsys.readouterr().out
    assert exit_code == expected_exit
    assert {row["symbol"] for row in store.rows} == {"INFY", "RELIANCE", "SBIN", "TCS"} - set(failing)
    if failing:
        assert "daily_market_snapshot: failed:" in output
        assert "TCS=EMPTY_RESPONSE" in output
    else:
        assert "daily_market_snapshot: ok" in output


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
        secret_key="sb_secret_test",
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
    assert kwargs["headers"]["apikey"] == "sb_secret_test"
    assert "Authorization" not in kwargs["headers"]
    assert kwargs["headers"]["Prefer"] == "resolution=merge-duplicates,return=minimal"
    assert kwargs["json"] == [row]


def test_supabase_store_requires_server_credentials():
    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        SupabaseDailyBarStore.from_env({})


def test_supabase_store_requires_secret_key():
    with pytest.raises(RuntimeError, match="SUPABASE_SECRET_KEY"):
        SupabaseDailyBarStore.from_env({"SUPABASE_URL": "https://project.supabase.co"})


def test_supabase_retention_report_monitors_without_deleting_rows():
    class Response:
        def __init__(self, data, content_range=""):
            self.data = data
            self.headers = {"Content-Range": content_range}

        def raise_for_status(self):
            return None

        def json(self):
            return self.data

    class Session:
        def __init__(self):
            self.calls = []

        def get(self, url, **kwargs):
            self.calls.append((url, kwargs))
            if len(self.calls) == 1:
                return Response([{"trading_date": "2021-01-04"}], "0-0/245")
            return Response([{"trading_date": "2026-11-25"}])

    session = Session()
    store = SupabaseDailyBarStore(
        supabase_url="https://project.supabase.co",
        secret_key="sb_secret_test",
        session=session,
    )

    report = store.retention_report()

    assert report == {
        "policy": "retain_indefinitely_monitor_only",
        "row_count": 245,
        "oldest_trading_date": "2021-01-04",
        "newest_trading_date": "2026-11-25",
        "automatic_deletion": False,
    }
    assert len(session.calls) == 2
    assert all(call[1]["headers"]["apikey"] == "sb_secret_test" for call in session.calls)


def _ist(year, month, day, hour, minute=0):
    from datetime import datetime, timedelta, timezone

    return datetime(year, month, day, hour, minute, tzinfo=timezone(timedelta(hours=5, minutes=30)))


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (_ist(2026, 11, 27, 17), "2026-11-27"),  # Friday after data is ready
        (_ist(2026, 11, 27, 15, 45), "2026-11-26"),  # Friday before 16:00: today's bar not expected yet
        (_ist(2026, 11, 28, 12), "2026-11-27"),  # Saturday -> Friday
        (_ist(2026, 11, 29, 20), "2026-11-27"),  # Sunday -> Friday
        (_ist(2026, 11, 30, 9), "2026-11-27"),  # Monday morning -> Friday
        (_ist(2026, 11, 30, 17), "2026-11-30"),  # Monday evening
    ],
)
def test_latest_expected_session_is_weekday_and_ist_aware(now, expected):
    from backend.services.daily_market_collection import latest_expected_session

    assert latest_expected_session(now).isoformat() == expected


def test_trading_day_lag_counts_only_weekdays():
    from datetime import date

    from backend.services.daily_market_collection import trading_day_lag

    friday_evening = _ist(2026, 11, 27, 17)
    assert trading_day_lag(date(2026, 11, 27), friday_evening) == 0
    assert trading_day_lag(date(2026, 11, 26), friday_evening) == 1
    assert trading_day_lag(date(2026, 11, 20), friday_evening) == 5  # one full week
    # Saturday/Sunday add no lag: Friday's bar is current on a weekend.
    assert trading_day_lag(date(2026, 11, 27), _ist(2026, 11, 29, 20)) == 0
    # A bar newer than the expected session is never negative.
    assert trading_day_lag(date(2026, 11, 27), _ist(2026, 11, 27, 10)) == 0


def test_assess_symbol_coverage_flags_missing_and_stale_but_tolerates_one_holiday():
    from backend.services.daily_market_collection import assess_symbol_coverage

    now = _ist(2026, 11, 27, 17)
    coverage = {
        "INFY": {"row_count": 496, "newest_trading_date": "2026-11-27"},
        "TCS": {"row_count": 496, "newest_trading_date": "2026-11-25"},  # lag 2: tolerated
        "SBIN": {"row_count": 496, "newest_trading_date": "2026-11-24"},  # lag 3: stale
        "RELIANCE": {"row_count": 0, "newest_trading_date": None},
    }

    result = assess_symbol_coverage(coverage, ["INFY", "TCS", "SBIN", "RELIANCE", "WIPRO"], now=now)

    assert {symbol: info["status"] for symbol, info in result.items()} == {
        "INFY": "fresh",
        "TCS": "fresh",
        "SBIN": "stale",
        "RELIANCE": "missing",
        "WIPRO": "missing",  # absent from the store entirely
    }
    assert result["SBIN"]["lag_trading_days"] == 3
    assert result["SBIN"]["newest_trading_date"] == "2026-11-24"


class CoverageResponse:
    def __init__(self, rows, content_range):
        self.rows = rows
        self.headers = {"Content-Range": content_range}

    def raise_for_status(self):
        return None

    def json(self):
        return self.rows


class ReadOnlySession:
    """Serves GETs and fails the test on any write or delete."""

    def __init__(self, data):
        self.data = data
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        symbol = kwargs["params"]["symbol"].removeprefix("eq.")
        rows, total = self.data.get(symbol, ([], 0))
        return CoverageResponse(rows, f"0-0/{total}" if rows else "*/0")

    def post(self, *args, **kwargs):
        raise AssertionError("monitoring must not write")

    def delete(self, *args, **kwargs):
        raise AssertionError("monitoring must never delete market history")

    patch = put = delete


def test_supabase_symbol_coverage_reads_count_and_newest_date_per_symbol():
    session = ReadOnlySession(
        {"INFY": ([{"trading_date": "2026-11-27"}], 496), "TCS": ([{"trading_date": "2026-11-26"}], 247)}
    )
    store = SupabaseDailyBarStore(
        supabase_url="https://project.supabase.co", secret_key="sb_secret_test", session=session
    )

    coverage = store.symbol_coverage(["infy.ns", "TCS", "SBIN", ""])

    assert coverage == {
        "INFY": {"row_count": 496, "newest_trading_date": "2026-11-27"},
        "TCS": {"row_count": 247, "newest_trading_date": "2026-11-26"},
        "SBIN": {"row_count": 0, "newest_trading_date": None},
    }
    assert len(session.calls) == 3
    for _, kwargs in session.calls:
        assert kwargs["headers"]["Prefer"] == "count=exact"
        assert kwargs["params"]["order"] == "trading_date.desc"
        assert kwargs["params"]["limit"] == "1"


def _retention_job_store(rows_by_symbol):
    session = ReadOnlySession(rows_by_symbol)
    return SupabaseDailyBarStore(
        supabase_url="https://project.supabase.co", secret_key="sb_secret_test", session=session
    ), session


def _stub_retention_report(monkeypatch, store):
    monkeypatch.setattr(
        store,
        "retention_report",
        lambda: {
            "policy": "retain_indefinitely_monitor_only",
            "row_count": 1984,
            "oldest_trading_date": "2024-11-27",
            "newest_trading_date": "2026-11-27",
            "automatic_deletion": False,
        },
    )


FRESH = {
    symbol: ([{"trading_date": "2026-11-27"}], 496) for symbol in ("INFY", "RELIANCE", "SBIN", "TCS")
}


@pytest.mark.parametrize(
    ("data", "expected_exit", "expected_text", "expected_unhealthy"),
    [
        (FRESH, 0, "retention_report: ok", []),
        (
            {**FRESH, "TCS": ([{"trading_date": "2026-11-18"}], 490)},
            1,
            "TCS=stale(newest 2026-11-18, 7 trading days behind)",
            ["TCS"],
        ),
        ({**FRESH, "SBIN": ([], 0)}, 1, "SBIN=missing", ["SBIN"]),
    ],
    ids=["healthy", "stale-symbol", "missing-symbol"],
)
def test_retention_report_job_fails_run_for_stale_or_missing_symbols(
    app_module, monkeypatch, capsys, data, expected_exit, expected_text, expected_unhealthy
):
    from backend.workers import jobs, scheduler_cli

    services = app_module.services
    store, session = _retention_job_store(data)
    _stub_retention_report(monkeypatch, store)
    monkeypatch.setitem(services.system_cache, "daily_bar_store", store)
    monkeypatch.setattr(jobs, "_now", lambda: _ist(2026, 11, 27, 17))

    class App:
        extensions = {"stocksense_services": services}

    monkeypatch.setattr(scheduler_cli, "create_app", lambda settings: App())
    monkeypatch.setattr(scheduler_cli, "startup", lambda app: None)

    exit_code = scheduler_cli.main(["--once", "--job", "retention_report"])

    output = capsys.readouterr().out
    assert exit_code == expected_exit
    assert expected_text in output
    report = services.system_cache["retention_report"]
    assert report["automatic_deletion"] is False
    assert set(report["symbols"]) == {"INFY", "RELIANCE", "SBIN", "TCS"}
    assert report["unhealthy_symbols"] == expected_unhealthy
    # Only reads happened (ReadOnlySession fails the test on any write or delete).
    assert all("market_daily_bars" in url for url, _ in session.calls)


def test_supabase_history_read_returns_oldest_first_and_bounds_rows():
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return [
                {"symbol": "INFY", "trading_date": "2026-11-25", "close": 120},
                {"symbol": "INFY", "trading_date": "2026-11-24", "close": 110},
            ]

    class Session:
        def get(self, url, **kwargs):
            self.call = (url, kwargs)
            return Response()

    session = Session()
    store = SupabaseDailyBarStore(
        supabase_url="https://project.supabase.co",
        secret_key="sb_secret_test",
        session=session,
    )

    rows = store.read_history("infy.ns", limit=5000)

    assert [row["trading_date"] for row in rows] == ["2026-11-24", "2026-11-25"]
    assert session.call[1]["params"]["limit"] == "1000"
    assert session.call[1]["params"]["symbol"] == "eq.INFY"
