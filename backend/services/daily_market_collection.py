"""Persist daily market bars collected from the configured provider."""

from __future__ import annotations

from datetime import date, datetime
import logging
import os
from typing import Any, Protocol

import requests

from backend.services.market_data import ProviderResponse, ResilientMarketDataClient, normalize_symbol


class DailyBarStore(Protocol):
    def upsert(self, rows: list[dict[str, Any]]) -> None:
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

    def collect(self) -> dict[str, int]:
        collected: list[dict[str, Any]] = []
        failed_symbols = 0
        for raw_symbol in self.symbols:
            symbol = normalize_symbol(raw_symbol)
            if not symbol:
                failed_symbols += 1
                continue
            response = self.market_data.history(
                symbol,
                period="5d",
                interval="1d",
                allow_stale=False,
            )
            bars = _daily_bar_rows(symbol, response)
            if not bars:
                failed_symbols += 1
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
        return {
            "symbols_requested": len(self.symbols),
            "symbols_failed": failed_symbols,
            "bars_upserted": len(collected),
        }


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
