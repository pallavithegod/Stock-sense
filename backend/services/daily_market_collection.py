"""Persist daily market bars collected from the configured provider."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import logging
import os
from typing import Any, Iterable, Protocol

import requests

from backend.services.market_data import ProviderResponse, ResilientMarketDataClient, normalize_symbol

INDIA_TZ = timezone(timedelta(hours=5, minutes=30))
# The snapshot runs after the 15:30 IST close; before this time today's bar is not expected yet.
SESSION_DATA_READY_IST = time(16, 0)
# Weekdays a symbol's newest bar may trail the latest expected session before it is
# reported stale. Two tolerates one exchange holiday without a holiday calendar.
MAX_STALE_TRADING_DAYS = 2


class StaleMarketHistoryError(RuntimeError):
    """A configured symbol has no stored bars or its newest bar is too old."""

    def __init__(self, unhealthy: dict[str, dict[str, Any]]):
        self.unhealthy = unhealthy
        detail = ", ".join(
            f"{symbol}={info['status']}"
            + (
                f"(newest {info['newest_trading_date']}, {info['lag_trading_days']} trading days behind)"
                if info["status"] == "stale"
                else ""
            )
            for symbol, info in sorted(unhealthy.items())
        )
        super().__init__(f"Market history is unhealthy for {len(unhealthy)} symbol(s): {detail}")


def latest_expected_session(now: datetime) -> date:
    """Most recent weekday whose daily bar should already be stored (IST, weekday-only)."""
    now_ist = now.astimezone(INDIA_TZ)
    day = now_ist.date()
    if now_ist.time() < SESSION_DATA_READY_IST:
        day -= timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day


def trading_day_lag(newest: date, now: datetime) -> int:
    """Weekdays between the newest stored bar and the latest expected session."""
    expected = latest_expected_session(now)
    lag = 0
    day = newest
    while day < expected:
        day += timedelta(days=1)
        if day.weekday() < 5:
            lag += 1
    return lag


def assess_symbol_coverage(
    coverage: dict[str, dict[str, Any]],
    symbols: Iterable[str],
    *,
    now: datetime,
    max_stale_trading_days: int = MAX_STALE_TRADING_DAYS,
) -> dict[str, dict[str, Any]]:
    """Classify each configured symbol as fresh, stale or missing. Read-only."""
    result: dict[str, dict[str, Any]] = {}
    for symbol in symbols:
        info = coverage.get(symbol) or {}
        row_count = int(info.get("row_count") or 0)
        newest_raw = info.get("newest_trading_date")
        if row_count == 0 or not newest_raw:
            result[symbol] = {
                "status": "missing",
                "row_count": row_count,
                "newest_trading_date": None,
                "lag_trading_days": None,
            }
            continue
        lag = trading_day_lag(date.fromisoformat(str(newest_raw)[:10]), now)
        result[symbol] = {
            "status": "stale" if lag > max_stale_trading_days else "fresh",
            "row_count": row_count,
            "newest_trading_date": str(newest_raw)[:10],
            "lag_trading_days": lag,
        }
    return result


class DailyBarStore(Protocol):
    def upsert(self, rows: list[dict[str, Any]]) -> None:
        ...

    def retention_report(self) -> dict[str, Any]:
        ...

    def symbol_coverage(self, symbols: Iterable[str]) -> dict[str, dict[str, Any]]:
        ...

    def read_history(self, symbol: str, *, limit: int = 500) -> list[dict[str, Any]]:
        ...


class SupabaseDailyBarStore:
    def __init__(
        self,
        *,
        supabase_url: str,
        secret_key: str,
        session: requests.Session | None = None,
    ):
        self.supabase_url = supabase_url.rstrip("/")
        self.secret_key = secret_key
        self.session = session or requests.Session()

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> "SupabaseDailyBarStore":
        env = os.environ if environ is None else environ
        supabase_url = env.get("SUPABASE_URL", "").strip()
        secret_key = env.get("SUPABASE_SECRET_KEY", "").strip()
        if not supabase_url or not secret_key:
            raise RuntimeError(
                "Daily market collection requires SUPABASE_URL and "
                "SUPABASE_SECRET_KEY."
            )
        return cls(supabase_url=supabase_url, secret_key=secret_key)

    def upsert(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        response = self.session.post(
            f"{self.supabase_url}/rest/v1/market_daily_bars",
            params={"on_conflict": "symbol,trading_date"},
            headers={
                "apikey": self.secret_key,
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
            json=rows,
            timeout=20,
        )
        response.raise_for_status()

    def retention_report(self) -> dict[str, Any]:
        headers = {
            "apikey": self.secret_key,
            "Prefer": "count=exact",
            "Range": "0-0",
        }
        count_response = self.session.get(
            f"{self.supabase_url}/rest/v1/market_daily_bars",
            params={"select": "trading_date", "order": "trading_date.asc", "limit": "1"},
            headers=headers,
            timeout=20,
        )
        count_response.raise_for_status()
        content_range = count_response.headers.get("Content-Range", "")
        try:
            row_count = int(content_range.rsplit("/", 1)[1])
        except (IndexError, ValueError) as exc:
            raise RuntimeError("Supabase did not return an exact market-history row count.") from exc

        oldest_rows = count_response.json()
        oldest_date = oldest_rows[0].get("trading_date") if oldest_rows else None
        newest_response = self.session.get(
            f"{self.supabase_url}/rest/v1/market_daily_bars",
            params={"select": "trading_date", "order": "trading_date.desc", "limit": "1"},
            headers={"apikey": self.secret_key},
            timeout=20,
        )
        newest_response.raise_for_status()
        newest_rows = newest_response.json()
        newest_date = newest_rows[0].get("trading_date") if newest_rows else None
        return {
            "policy": "retain_indefinitely_monitor_only",
            "row_count": row_count,
            "oldest_trading_date": oldest_date,
            "newest_trading_date": newest_date,
            "automatic_deletion": False,
        }

    def symbol_coverage(self, symbols: Iterable[str]) -> dict[str, dict[str, Any]]:
        """Read-only per-symbol row count and newest trading date (two cheap GETs total per symbol)."""
        coverage: dict[str, dict[str, Any]] = {}
        for raw_symbol in symbols:
            symbol = normalize_symbol(raw_symbol)
            if not symbol:
                continue
            response = self.session.get(
                f"{self.supabase_url}/rest/v1/market_daily_bars",
                params={
                    "select": "trading_date",
                    "symbol": f"eq.{symbol}",
                    "order": "trading_date.desc",
                    "limit": "1",
                },
                headers={"apikey": self.secret_key, "Prefer": "count=exact", "Range": "0-0"},
                timeout=20,
            )
            response.raise_for_status()
            content_range = response.headers.get("Content-Range", "")
            try:
                row_count = int(content_range.rsplit("/", 1)[1])
            except (IndexError, ValueError) as exc:
                raise RuntimeError("Supabase did not return an exact market-history row count.") from exc
            rows = response.json()
            if not isinstance(rows, list):
                raise RuntimeError("Supabase returned an invalid market-history response.")
            coverage[symbol] = {
                "row_count": row_count,
                "newest_trading_date": rows[0].get("trading_date") if rows else None,
            }
        return coverage

    def read_history(self, symbol: str, *, limit: int = 500) -> list[dict[str, Any]]:
        normalized_symbol = normalize_symbol(symbol)
        if not normalized_symbol:
            raise ValueError("A valid symbol is required to read market history.")
        bounded_limit = max(1, min(int(limit), 1000))
        response = self.session.get(
            f"{self.supabase_url}/rest/v1/market_daily_bars",
            params={
                "select": "symbol,trading_date,close",
                "symbol": f"eq.{normalized_symbol}",
                "order": "trading_date.desc",
                "limit": str(bounded_limit),
            },
            headers={"apikey": self.secret_key},
            timeout=20,
        )
        response.raise_for_status()
        rows = response.json()
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise RuntimeError("Supabase returned an invalid market-history response.")
        return list(reversed(rows))


class PartialCollectionError(RuntimeError):
    """Some symbols yielded no valid bars; the valid bars were still upserted."""

    def __init__(self, *, result: dict[str, int], failures: list[dict[str, str]]):
        self.result = result
        self.failures = failures
        detail = ", ".join(f"{item['symbol']}={item['error_code']}" for item in failures)
        super().__init__(
            f"Daily market collection incomplete: {len(failures)} of "
            f"{result['symbols_requested']} symbols failed ({detail}); "
            f"{result['bars_upserted']} bars upserted for the rest."
        )


class DailyMarketCollector:
    def __init__(
        self,
        *,
        market_data: ResilientMarketDataClient,
        store: DailyBarStore,
        symbols: list[str],
        logger: logging.Logger | None = None,
    ):
        self.market_data = market_data
        self.store = store
        self.symbols = symbols
        self.logger = logger or logging.getLogger("stocksense.daily_market_collection")

    def collect(self, *, period: str = "1y") -> dict[str, int]:
        """Collect and upsert daily bars for every configured symbol.

        Valid bars are always persisted. If any symbol yields no valid bars the
        run raises ``PartialCollectionError`` after the upsert, so schedulers
        and CLIs report failure instead of a success-shaped partial snapshot.
        """
        collected: list[dict[str, Any]] = []
        failures: list[dict[str, str]] = []
        for raw_symbol in self.symbols:
            symbol = normalize_symbol(raw_symbol)
            if not symbol:
                failures.append({"symbol": str(raw_symbol), "error_code": "INVALID_SYMBOL"})
                continue
            response = self.market_data.history(
                symbol,
                period=period,
                interval="1d",
                allow_stale=False,
            )
            bars = _daily_bar_rows(symbol, response)
            if not bars:
                failures.append({"symbol": symbol, "error_code": response.error_code or "NO_VALID_BARS"})
                self.logger.warning(
                    "daily_market_collection_symbol_unavailable symbol=%s provider=%s error_code=%s",
                    symbol,
                    response.provider,
                    response.error_code,
                )
                continue
            collected.extend(bars)

        if not collected:
            raise RuntimeError("Daily market collection returned no valid live bars.")

        self.store.upsert(collected)
        result = {
            "symbols_requested": len(self.symbols),
            "symbols_failed": len(failures),
            "bars_upserted": len(collected),
        }
        if failures:
            raise PartialCollectionError(result=result, failures=failures)
        return result


def _daily_bar_rows(symbol: str, response: ProviderResponse) -> list[dict[str, Any]]:
    if response.state != "live" or response.synthetic or response.demo:
        return []
    data = response.data
    prices = data.get("prices") if isinstance(data, dict) else None
    if not isinstance(prices, list):
        return []

    rows = []
    for item in prices:
        if not isinstance(item, dict):
            continue
        try:
            timestamp = str(item["timestamp"])
            trading_date = _parse_trading_date(timestamp)
            open_price = float(item["open"])
            high_price = float(item["high"])
            low_price = float(item["low"])
            close_price = float(item["close"])
            volume = int(item["volume"])
        except (KeyError, TypeError, ValueError):
            continue
        if (
            min(open_price, high_price, low_price, close_price) <= 0
            or high_price < max(open_price, low_price, close_price)
            or low_price > min(open_price, high_price, close_price)
            or volume < 0
        ):
            continue
        rows.append(
            {
                "symbol": symbol,
                "trading_date": trading_date.isoformat(),
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
                "provider": response.provider,
                "fetched_at": response.fetched_at,
            }
        )
    return rows


def _parse_trading_date(value: str) -> date:
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
