"""Market data provider boundary with cache and failure isolation."""

from __future__ import annotations

import logging
import math
import os
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal, Protocol

import requests


DataState = Literal["live", "cached_stale", "demo", "unavailable"]
RequestType = Literal["quote", "history", "search", "indices"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def configure_yfinance_cache(yfinance_module: Any, *, cache_dir: str | os.PathLike[str] = "cache/yfinance") -> Path:
    """Ensure yfinance can create its timezone cache on locked-down Windows setups."""
    path = Path(cache_dir)
    path.mkdir(parents=True, exist_ok=True)
    if hasattr(yfinance_module, "set_tz_cache_location"):
        yfinance_module.set_tz_cache_location(str(path.resolve()))
    return path


def normalize_symbol(value: Any) -> str | None:
    if value is None:
        return None
    symbol = str(value).strip().upper().replace(".NS", "").replace(".BO", "")
    cleaned = "".join(ch for ch in symbol if ch.isalnum() or ch in {"&", ".", "-"})
    return cleaned or None


def exchange_candidates(symbol: str, *, default_exchange: str = ".NS") -> list[str]:
    cleaned = str(symbol or "").strip().upper()
    if not cleaned:
        return []
    if cleaned.startswith("^") or cleaned.endswith((".NS", ".BO")):
        return [cleaned]
    suffixes = [default_exchange, ".BO" if default_exchange == ".NS" else ".NS"]
    return [f"{cleaned}{suffix}" for suffix in suffixes]


def to_yfinance_symbol(symbol: str, *, default_exchange: str = ".NS") -> str:
    candidates = exchange_candidates(symbol, default_exchange=default_exchange)
    return candidates[0] if candidates else str(symbol or "").upper().strip()


def _history_exchange_candidates(symbol: str, *, default_exchange: str = ".NS") -> list[str]:
    cleaned = str(symbol or "").strip().upper()
    if not cleaned:
        return []
    if cleaned.startswith("^"):
        return [cleaned]
    if cleaned.endswith(".NS"):
        base = cleaned[:-3]
        return [cleaned, f"{base}.BO", base]
    if cleaned.endswith(".BO"):
        base = cleaned[:-3]
        return [cleaned, f"{base}.NS", base]
    other_exchange = ".BO" if default_exchange == ".NS" else ".NS"
    return [
        f"{cleaned}{default_exchange}",
        f"{cleaned}{other_exchange}",
        cleaned,
    ]


_EXCEPTION_SECRET_RE = re.compile(
    r"""(?i)(["']?(?:api[_-]?key|token|secret|password|authorization)["']?\s*[=:]\s*["']?)[^"'&,\s}]+(["']?)"""
)
_URL_QUERY_RE = re.compile(r"(?i)(https?://[^\s?]+)\?[^\s]+")


def _sanitized_exception_message(error: Exception) -> str:
    message = " ".join(str(error).split())
    message = _EXCEPTION_SECRET_RE.sub(r"\1[REDACTED]\2", message)
    message = _URL_QUERY_RE.sub(r"\1?[REDACTED]", message)
    return message[:240] or type(error).__name__


@dataclass(frozen=True)
class ProviderResponse:
    provider: str
    state: DataState
    data: Any
    fetched_at: str = field(default_factory=utc_now_iso)
    stale: bool = False
    synthetic: bool = False
    demo: bool = False
    quality_status: str = "unavailable"
    error_code: str | None = None

    @classmethod
    def live(cls, provider: str, data: Any, *, fetched_at: str | None = None, quality_status: str = "live") -> "ProviderResponse":
        return cls(
            provider=provider,
            state="live",
            data=data,
            fetched_at=fetched_at or utc_now_iso(),
            stale=False,
            synthetic=False,
            demo=False,
            quality_status=quality_status,
        )

    @classmethod
    def demo_data(cls, provider: str, data: Any) -> "ProviderResponse":
        return cls(
            provider=provider,
            state="demo",
            data=data,
            stale=False,
            synthetic=False,
            demo=True,
            quality_status="demo",
        )

    @classmethod
    def unavailable(cls, provider: str, *, error_code: str = "PROVIDER_UNAVAILABLE", data: Any = None) -> "ProviderResponse":
        return cls(
            provider=provider,
            state="unavailable",
            data=data,
            stale=True,
            synthetic=False,
            demo=False,
            quality_status="unavailable",
            error_code=error_code,
        )

    def as_cached_stale(self) -> "ProviderResponse":
        return ProviderResponse(
            provider=self.provider,
            state="cached_stale",
            data=self.data,
            fetched_at=self.fetched_at,
            stale=True,
            synthetic=self.synthetic,
            demo=self.demo,
            quality_status="cached_stale",
            error_code=self.error_code,
        )


@dataclass(frozen=True)
class ProviderPolicy:
    timeout_seconds: float = 5.0
    max_retries: int = 1
    retry_jitter_seconds: float = 0.05
    max_workers: int = 4
    circuit_breaker_threshold: int = 3
    circuit_breaker_cooldown_seconds: float = 30.0
    cache_ttl_seconds: float = 60.0
    stale_ttl_seconds: float = 300.0


@dataclass(frozen=True)
class MarketDataRequest:
    request_type: RequestType
    symbol: str | None = None
    period: str | None = None
    interval: str | None = None
    query: str | None = None
    limit: int | None = None

    def cache_key(self, provider: str) -> str:
        return "|".join(
            [
                provider,
                self.request_type,
                normalize_symbol(self.symbol) or "",
                self.period or "",
                self.interval or "",
                (self.query or "").strip().upper(),
                str(self.limit or ""),
            ]
        )


@dataclass
class CacheEntry:
    response: ProviderResponse
    expires_at: float
    stale_until: float


class MarketDataCache:
    def __init__(self) -> None:
        self._entries: dict[str, CacheEntry] = {}

    def set(self, key: str, response: ProviderResponse, *, now: float, policy: ProviderPolicy) -> None:
        self._entries[key] = CacheEntry(
            response=response,
            expires_at=now + policy.cache_ttl_seconds,
            stale_until=now + policy.cache_ttl_seconds + policy.stale_ttl_seconds,
        )

    def get(self, key: str, *, now: float, allow_stale: bool) -> ProviderResponse | None:
        entry = self._entries.get(key)
        if not entry:
            return None
        if entry.expires_at >= now:
            return entry.response
        if allow_stale and entry.stale_until >= now:
            return entry.response.as_cached_stale()
        return None


class MarketDataProvider(Protocol):
    name: str

    def quote(self, symbol: str) -> ProviderResponse:
        ...

    def history(self, symbol: str, *, period: str, interval: str) -> ProviderResponse:
        ...

    def search(self, query: str, *, limit: int) -> ProviderResponse:
        ...

    def indices(self) -> ProviderResponse:
        ...

    def health(self) -> dict[str, Any]:
        ...


class UnavailableMarketDataProvider:
    name = "unavailable"

    def quote(self, symbol: str) -> ProviderResponse:
        return ProviderResponse.unavailable(self.name, error_code="PROVIDER_DISABLED")

    def history(self, symbol: str, *, period: str, interval: str) -> ProviderResponse:
        return ProviderResponse.unavailable(self.name, error_code="PROVIDER_DISABLED", data=[])

    def search(self, query: str, *, limit: int) -> ProviderResponse:
        return ProviderResponse.unavailable(self.name, error_code="PROVIDER_DISABLED", data=[])

    def indices(self) -> ProviderResponse:
        return ProviderResponse.unavailable(self.name, error_code="PROVIDER_DISABLED", data=[])

    def health(self) -> dict[str, Any]:
        return {"configured": False, "status": "disabled"}


class ApiKeyMarketDataProvider:
    """API-key provider for daily history, with other capabilities left explicit."""

    def __init__(
        self,
        *,
        name: str,
        api_key_env: str,
        api_key_aliases: tuple[str, ...] = (),
        session: requests.Session | None = None,
    ):
        self.name = name
        self.api_key_env = api_key_env
        self.api_key_envs = (api_key_env, *api_key_aliases)
        self.api_key = ""
        self.configured_env = None
        for key in self.api_key_envs:
            value = os.getenv(key, "").strip()
            if value:
                self.api_key = value
                self.configured_env = key
                break
        self._configured = bool(self.api_key)
        self.session = session or requests.Session()

    def _response(self) -> ProviderResponse:
        code = "PROVIDER_NOT_IMPLEMENTED" if self._configured else "PROVIDER_NOT_CONFIGURED"
        return ProviderResponse.unavailable(self.name, error_code=code)

    def quote(self, symbol: str) -> ProviderResponse:
        return self._response()

    def history(self, symbol: str, *, period: str, interval: str) -> ProviderResponse:
        if not self._configured:
            return ProviderResponse.unavailable(self.name, error_code="PROVIDER_NOT_CONFIGURED", data=[])
        if interval != "1d":
            return ProviderResponse.unavailable(self.name, error_code="UNSUPPORTED_INTERVAL", data=[])
        if self.name == "finnhub":
            return self._finnhub_history(symbol, period)
        if self.name == "alpha_vantage":
            return self._alpha_vantage_history(symbol, period)
        return self._response()

    def search(self, query: str, *, limit: int) -> ProviderResponse:
        return self._response()

    def indices(self) -> ProviderResponse:
        return self._response()

    def health(self) -> dict[str, Any]:
        status = "configured" if self._configured else "missing_key"
        result = {"configured": self._configured, "status": status}
        if self.configured_env:
            result["api_key_env"] = self.configured_env
        return result

    def _finnhub_history(self, symbol: str, period: str) -> ProviderResponse:
        start, end = _period_epoch_range(period)
        base_symbol = normalize_symbol(symbol)
        if not base_symbol:
            return ProviderResponse.unavailable(self.name, error_code="INVALID_SYMBOL", data=[])
        for candidate in (f"NSE:{base_symbol}", f"BSE:{base_symbol}", f"{base_symbol}.NS", f"{base_symbol}.BO"):
            try:
                response = self.session.get(
                    "https://finnhub.io/api/v1/stock/candle",
                    params={
                        "symbol": candidate,
                        "resolution": "D",
                        "from": start,
                        "to": end,
                        "token": self.api_key,
                    },
                    timeout=10,
                )
                response.raise_for_status()
                payload = response.json()
            except requests.HTTPError as exc:
                return ProviderResponse.unavailable(
                    self.name,
                    error_code=_request_error_code(exc),
                    data=[],
                )
            except requests.RequestException:
                return ProviderResponse.unavailable(self.name, error_code="API_REQUEST_FAILED", data=[])
            except ValueError:
                return ProviderResponse.unavailable(self.name, error_code="MALFORMED_RESPONSE", data=[])
            if not isinstance(payload, dict):
                return ProviderResponse.unavailable(self.name, error_code="MALFORMED_RESPONSE", data=[])
            if payload.get("s") == "no_data":
                continue
            if payload.get("s") != "ok":
                return ProviderResponse.unavailable(self.name, error_code="API_ERROR_RESPONSE", data=[])
            rows = _finnhub_bar_rows(payload)
            if rows:
                return ProviderResponse.live(self.name, {"symbol": base_symbol, "prices": rows})
        return ProviderResponse.unavailable(self.name, error_code="EMPTY_RESPONSE", data=[])

    def _alpha_vantage_history(self, symbol: str, period: str) -> ProviderResponse:
        base_symbol = normalize_symbol(symbol)
        if not base_symbol:
            return ProviderResponse.unavailable(self.name, error_code="INVALID_SYMBOL", data=[])
        start_date, _ = _period_date_range(period)
        last_error = "EMPTY_RESPONSE"
        for candidate in (f"{base_symbol}.BSE", f"{base_symbol}.NSE", base_symbol):
            try:
                response = self.session.get(
                    "https://www.alphavantage.co/query",
                    params={
                        "function": "TIME_SERIES_DAILY",
                        "symbol": candidate,
                        "outputsize": "full",
                        "apikey": self.api_key,
                    },
                    timeout=15,
                )
                response.raise_for_status()
                payload = response.json()
            except requests.HTTPError as exc:
                return ProviderResponse.unavailable(
                    self.name,
                    error_code=_request_error_code(exc),
                    data=[],
                )
            except requests.RequestException:
                return ProviderResponse.unavailable(self.name, error_code="API_REQUEST_FAILED", data=[])
            except ValueError:
                return ProviderResponse.unavailable(self.name, error_code="MALFORMED_RESPONSE", data=[])
            if not isinstance(payload, dict):
                return ProviderResponse.unavailable(self.name, error_code="MALFORMED_RESPONSE", data=[])
            series_key = next((key for key in payload if key.startswith("Time Series (")), None)
            if not series_key:
                note = " ".join(str(payload.get(key, "")).lower() for key in ("Note", "Information", "Error Message"))
                last_error = "API_LIMIT_OR_SYMBOL_UNAVAILABLE" if note else "EMPTY_RESPONSE"
                if "symbol" in note or "invalid" in note:
                    continue
                if "premium" in note or "outputsize" in note:
                    try:
                        compact_response = self.session.get(
                            "https://www.alphavantage.co/query",
                            params={
                                "function": "TIME_SERIES_DAILY",
                                "symbol": candidate,
                                "outputsize": "compact",
                                "apikey": self.api_key,
                            },
                            timeout=15,
                        )
                        compact_response.raise_for_status()
                        compact_payload = compact_response.json()
                    except requests.HTTPError as exc:
                        return ProviderResponse.unavailable(
                            self.name,
                            error_code=_request_error_code(exc),
                            data=[],
                        )
                    except requests.RequestException:
                        return ProviderResponse.unavailable(self.name, error_code="API_REQUEST_FAILED", data=[])
                    except ValueError:
                        return ProviderResponse.unavailable(self.name, error_code="MALFORMED_RESPONSE", data=[])
                    if isinstance(compact_payload, dict):
                        compact_key = next(
                            (key for key in compact_payload if key.startswith("Time Series (")),
                            None,
                        )
                        if compact_key:
                            rows = _alpha_vantage_bar_rows(compact_payload[compact_key], start_date)
                            if rows:
                                return ProviderResponse.live(
                                    self.name,
                                    {"symbol": base_symbol, "prices": rows},
                                )
                return ProviderResponse.unavailable(self.name, error_code=last_error, data=[])
            rows = _alpha_vantage_bar_rows(payload[series_key], start_date)
            if rows:
                return ProviderResponse.live(self.name, {"symbol": base_symbol, "prices": rows})
        return ProviderResponse.unavailable(self.name, error_code=last_error, data=[])


def _period_date_range(period: str, *, today: date | None = None) -> tuple[date, date]:
    end = today or datetime.now(timezone.utc).date()
    normalized = period.strip().lower()
    if normalized == "max":
        return date(1970, 1, 1), end
    if normalized.endswith("d"):
        days = int(normalized[:-1])
        return end - timedelta(days=days), end
    if normalized.endswith("mo"):
        months = int(normalized[:-2])
        return end - timedelta(days=months * 31), end
    if normalized.endswith("y"):
        years = int(normalized[:-1])
        try:
            start = end.replace(year=end.year - years)
        except ValueError:
            start = end.replace(year=end.year - years, day=28)
        return start, end
    raise ValueError(f"Unsupported history period: {period}")


def _period_epoch_range(period: str, *, today: date | None = None) -> tuple[int, int]:
    start, end = _period_date_range(period, today=today)
    return int(datetime.combine(start, datetime.min.time(), timezone.utc).timestamp()), int(
        datetime.combine(end, datetime.max.time(), timezone.utc).timestamp()
    )


def _request_error_code(exc: requests.HTTPError) -> str:
    status_code = exc.response.status_code if exc.response is not None else None
    if status_code in {401, 403}:
        return "API_AUTH_REJECTED"
    if status_code == 429:
        return "API_RATE_LIMITED"
    if status_code is not None and status_code >= 500:
        return "API_UNAVAILABLE"
    return "API_REQUEST_FAILED"


def _finnhub_bar_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        timestamps = payload["t"]
        opens, highs, lows = payload["o"], payload["h"], payload["l"]
        closes, volumes = payload["c"], payload["v"]
        if not all(len(values) == len(timestamps) for values in (opens, highs, lows, closes, volumes)):
            return []
    except (KeyError, TypeError):
        return []
    rows = []
    for index, timestamp in enumerate(timestamps):
        try:
            row = {
                "timestamp": datetime.fromtimestamp(int(timestamp), timezone.utc).isoformat(),
                "open": float(opens[index]),
                "high": float(highs[index]),
                "low": float(lows[index]),
                "close": float(closes[index]),
                "volume": int(volumes[index]),
            }
        except (OverflowError, TypeError, ValueError):
            continue
        if (
            min(row["open"], row["high"], row["low"], row["close"]) > 0
            and row["high"] >= max(row["open"], row["low"], row["close"])
            and row["low"] <= min(row["open"], row["high"], row["close"])
            and row["volume"] >= 0
        ):
            rows.append(row)
    return rows


def _alpha_vantage_bar_rows(series: Any, start_date: date) -> list[dict[str, Any]]:
    if not isinstance(series, dict):
        return []
    rows = []
    for day, values in series.items():
        try:
            trading_date = date.fromisoformat(str(day))
            if trading_date < start_date or not isinstance(values, dict):
                continue
            row = {
                "timestamp": trading_date.isoformat(),
                "open": float(values["1. open"]),
                "high": float(values["2. high"]),
                "low": float(values["3. low"]),
                "close": float(values["4. close"]),
                "volume": int(float(values["5. volume"])),
            }
        except (KeyError, TypeError, ValueError):
            continue
        if (
            min(row["open"], row["high"], row["low"], row["close"]) > 0
            and row["high"] >= max(row["open"], row["low"], row["close"])
            and row["low"] <= min(row["open"], row["high"], row["close"])
            and row["volume"] >= 0
        ):
            rows.append(row)
    return sorted(rows, key=lambda row: row["timestamp"])


class YFinanceMarketDataProvider:
    name = "yfinance"

    def __init__(self, *, default_exchange: str = ".NS"):
        self.default_exchange = default_exchange

    def _yf(self):
        import yfinance as yf

        configure_yfinance_cache(yf)
        return yf

    def _quote_payload_from_info(self, symbol: str, source_symbol: str, info: dict[str, Any]) -> ProviderResponse:
        price = info.get("last_price") or info.get("regularMarketPrice") or info.get("currentPrice") or info.get("previousClose")
        try:
            price_value = float(price)
        except (TypeError, ValueError):
            return ProviderResponse.unavailable(self.name, error_code="MALFORMED_RESPONSE")
        if price_value <= 0:
            return ProviderResponse.unavailable(self.name, error_code="MALFORMED_RESPONSE")
        previous_close = info.get("previous_close") or info.get("previousClose")
        change_value = None
        change_percent = None
        try:
            previous_value = float(previous_close)
            change_value = round(price_value - previous_value, 4)
            change_percent = round((change_value / previous_value) * 100, 4) if previous_value else None
        except (TypeError, ValueError):
            pass
        return ProviderResponse.live(
            self.name,
            {
                "symbol": normalize_symbol(symbol),
                "display": source_symbol,
                "price": price_value,
                "current_price": price_value,
                "change_value": change_value,
                "change_percent": change_percent,
            },
        )

    def _history_payload_from_frame(
        self, symbol: str, frame: Any, *, max_rows: int | None = 250
    ) -> ProviderResponse:
        if frame is None or getattr(frame, "empty", False):
            return ProviderResponse.unavailable(self.name, error_code="EMPTY_RESPONSE", data=[])
        required = {"open", "high", "low", "close", "volume"}
        columns = getattr(frame, "columns", None)
        if columns is None:
            return ProviderResponse.unavailable(self.name, error_code="MALFORMED_RESPONSE", data=[])
        column_map: dict[str, Any] = {}
        for column in columns:
            parts = column if isinstance(column, tuple) else (column,)
            for part in parts:
                field_name = str(part).strip().lower()
                if field_name in required:
                    column_map.setdefault(field_name, column)
        if not required.issubset(column_map):
            return ProviderResponse.unavailable(self.name, error_code="MALFORMED_RESPONSE", data=[])
        rows = []
        history_frame = frame if max_rows is None else frame.tail(max_rows)
        for timestamp, row in history_frame.iterrows():
            try:
                raw_values = {
                    field_name: float(row.get(column_map[field_name]))
                    for field_name in ("open", "high", "low", "close", "volume")
                }
                if not all(math.isfinite(value) for value in raw_values.values()):
                    continue
                timestamp_value = (
                    timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp)
                )
                date.fromisoformat(timestamp_value[:10])
                values = {
                    "open": raw_values["open"],
                    "high": raw_values["high"],
                    "low": raw_values["low"],
                    "close": raw_values["close"],
                    "volume": int(raw_values["volume"]),
                }
            except (TypeError, ValueError, OverflowError):
                continue
            if (
                min(values["open"], values["high"], values["low"], values["close"]) <= 0
                or values["high"] < max(values["open"], values["low"], values["close"])
                or values["low"] > min(values["open"], values["high"], values["close"])
                or values["volume"] < 0
            ):
                continue
            rows.append({"timestamp": timestamp_value, **values})
        if not rows:
            return ProviderResponse.unavailable(self.name, error_code="MALFORMED_RESPONSE", data=[])
        return ProviderResponse.live(self.name, {"symbol": normalize_symbol(symbol), "prices": rows})

    def quote(self, symbol: str) -> ProviderResponse:
        yf = self._yf()
        for candidate in exchange_candidates(symbol, default_exchange=self.default_exchange):
            ticker = yf.Ticker(candidate)
            try:
                fast_info = dict(getattr(ticker, "fast_info", {}) or {})
            except (TypeError, ValueError):
                fast_info = {}
            response = self._quote_payload_from_info(symbol, candidate, fast_info)
            if response.state == "live":
                return response
        return ProviderResponse.unavailable(self.name, error_code="EMPTY_RESPONSE")

    def history(self, symbol: str, *, period: str, interval: str) -> ProviderResponse:
        yf = self._yf()
        period_rows = {
            "1d": 5,
            "5d": 10,
            "1mo": 35,
            "3mo": 100,
            "6mo": 200,
            "1y": 300,
            "2y": 600,
            "5y": 1500,
            "10y": 3000,
            "ytd": 300,
            "max": None,
        }
        max_rows = period_rows.get(period.strip().lower())
        last_error = "EMPTY_RESPONSE"
        for candidate in _history_exchange_candidates(symbol, default_exchange=self.default_exchange):
            try:
                frame = yf.Ticker(candidate).history(period=period, interval=interval)
                response = self._history_payload_from_frame(symbol, frame, max_rows=max_rows)
            except Exception as exc:
                last_error = "PROVIDER_ERROR"
                logging.getLogger("stocksense.market_data").warning(
                    "yfinance_history_candidate_failed symbol=%s error_type=%s error=%s",
                    candidate,
                    type(exc).__name__,
                    _sanitized_exception_message(exc),
                )
                continue
            if response.state == "live":
                return response
            last_error = response.error_code or last_error
        return ProviderResponse.unavailable(self.name, error_code=last_error, data=[])

    def search(self, query: str, *, limit: int) -> ProviderResponse:
        return ProviderResponse.unavailable(self.name, error_code="SEARCH_NOT_SUPPORTED", data=[])

    def indices(self) -> ProviderResponse:
        index_symbols = ["^NSEI", "^BSESN"]
        rows = []
        yf = self._yf()
        for candidate in index_symbols:
            try:
                fast_info = dict(getattr(yf.Ticker(candidate), "fast_info", {}) or {})
            except (TypeError, ValueError):
                fast_info = {}
            response = self._quote_payload_from_info(candidate, candidate, fast_info)
            if response.state == "live":
                rows.append(response.data)
        if not rows:
            return ProviderResponse.unavailable(self.name, error_code="EMPTY_RESPONSE", data=[])
        return ProviderResponse.live(self.name, rows)

    def health(self) -> dict[str, Any]:
        return {"configured": True, "status": "available"}


class FakeMarketDataProvider:
    """Deterministic test provider for offline reliability tests."""

    def __init__(
        self,
        *,
        name: str = "fake",
        quotes: dict[str, dict[str, Any]] | None = None,
        histories: dict[tuple[str, str, str], list[dict[str, Any]]] | None = None,
        searches: dict[str, list[dict[str, Any]]] | None = None,
        indices: list[dict[str, Any]] | None = None,
        failures: dict[RequestType, str] | None = None,
    ):
        self.name = name
        self.quotes = {normalize_symbol(key) or key: value for key, value in (quotes or {}).items()}
        self.histories = histories or {}
        self.searches = {key.upper(): value for key, value in (searches or {}).items()}
        self.index_rows = indices or []
        self.failures = failures or {}

    def _failed(self, request_type: RequestType) -> ProviderResponse | None:
        code = self.failures.get(request_type)
        if not code:
            return None
        return ProviderResponse.unavailable(self.name, error_code=code)

    def quote(self, symbol: str) -> ProviderResponse:
        failed = self._failed("quote")
        if failed:
            return failed
        base_symbol = normalize_symbol(symbol) or ""
        row = self.quotes.get(base_symbol)
        if not row:
            return ProviderResponse.unavailable(self.name, error_code="EMPTY_RESPONSE")
        return ProviderResponse.live(self.name, {"symbol": base_symbol, **row})

    def history(self, symbol: str, *, period: str, interval: str) -> ProviderResponse:
        failed = self._failed("history")
        if failed:
            return failed
        rows = self.histories.get((normalize_symbol(symbol) or "", period, interval))
        if not rows:
            return ProviderResponse.unavailable(self.name, error_code="EMPTY_RESPONSE", data=[])
        return ProviderResponse.live(self.name, {"symbol": normalize_symbol(symbol), "prices": rows})

    def search(self, query: str, *, limit: int) -> ProviderResponse:
        failed = self._failed("search")
        if failed:
            return failed
        rows = self.searches.get(str(query or "").upper(), [])[:limit]
        return ProviderResponse.live(self.name, rows)

    def indices(self) -> ProviderResponse:
        failed = self._failed("indices")
        if failed:
            return failed
        if not self.index_rows:
            return ProviderResponse.unavailable(self.name, error_code="EMPTY_RESPONSE", data=[])
        return ProviderResponse.live(self.name, self.index_rows)

    def health(self) -> dict[str, Any]:
        return {"configured": True, "status": "fake", "failures": sorted(self.failures)}


class CircuitBreaker:
    def __init__(self, *, threshold: int, cooldown_seconds: float):
        self.threshold = threshold
        self.cooldown_seconds = cooldown_seconds
        self.failures = 0
        self.opened_until = 0.0
        self.last_error_code: str | None = None

    def allows_request(self, now: float) -> bool:
        return now >= self.opened_until

    def record_success(self) -> None:
        self.failures = 0
        self.opened_until = 0.0
        self.last_error_code = None

    def record_failure(self, *, now: float, error_code: str | None) -> None:
        self.failures += 1
        self.last_error_code = error_code or "PROVIDER_ERROR"
        if self.failures >= self.threshold:
            self.opened_until = now + self.cooldown_seconds

    def health(self, *, now: float) -> dict[str, Any]:
        return {
            "circuit": "open" if self.opened_until > now else "closed",
            "failure_count": self.failures,
            "last_error_code": self.last_error_code,
        }


class ResilientMarketDataClient:
    def __init__(self, providers: list[MarketDataProvider], *, policy: ProviderPolicy | None = None):
        self.providers = providers or [UnavailableMarketDataProvider()]
        self.policy = policy or ProviderPolicy()
        self.cache = MarketDataCache()
        self._executor = ThreadPoolExecutor(max_workers=self.policy.max_workers, thread_name_prefix="market-provider")
        self._breakers = {
            provider.name: CircuitBreaker(
                threshold=self.policy.circuit_breaker_threshold,
                cooldown_seconds=self.policy.circuit_breaker_cooldown_seconds,
            )
            for provider in self.providers
        }
        self.logger = logging.getLogger("stocksense")

    def quote(self, symbol: str, *, allow_stale: bool = False) -> ProviderResponse:
        return self._request(MarketDataRequest("quote", symbol=symbol), allow_stale=allow_stale)

    def history(self, symbol: str, *, period: str = "1y", interval: str = "1d", allow_stale: bool = False) -> ProviderResponse:
        return self._request(MarketDataRequest("history", symbol=symbol, period=period, interval=interval), allow_stale=allow_stale)

    def search(self, query: str, *, limit: int = 15, allow_stale: bool = False) -> ProviderResponse:
        return self._request(MarketDataRequest("search", query=query, limit=limit), allow_stale=allow_stale)

    def indices(self, *, allow_stale: bool = False) -> ProviderResponse:
        return self._request(MarketDataRequest("indices"), allow_stale=allow_stale)

    def health(self) -> dict[str, Any]:
        now = time.monotonic()
        return {
            provider.name: {
                **provider.health(),
                **self._breakers[provider.name].health(now=now),
            }
            for provider in self.providers
        }

    def _request(self, request: MarketDataRequest, *, allow_stale: bool) -> ProviderResponse:
        request_started = time.perf_counter()
        now = time.monotonic()
        stale_candidates: list[ProviderResponse] = []
        provider_failures: list[dict[str, str]] = []
        for provider in self.providers:
            key = request.cache_key(provider.name)
            cached = self.cache.get(key, now=now, allow_stale=allow_stale)
            if cached:
                self._log_market_data(
                    request=request,
                    provider=provider.name,
                    state=cached.state,
                    cache_outcome="hit_stale" if cached.state == "cached_stale" else "hit",
                    started_at=request_started,
                )
                if cached.state == "cached_stale":
                    stale_candidates.append(cached)
                else:
                    return cached

            breaker = self._breakers[provider.name]
            if not breaker.allows_request(now):
                provider_failures.append(
                    {"provider": provider.name, "error_code": breaker.last_error_code or "CIRCUIT_OPEN"}
                )
                continue

            response = self._call(provider, request)
            if response.state in {"live", "demo"}:
                breaker.record_success()
                self.cache.set(key, response, now=time.monotonic(), policy=self.policy)
                self._log_market_data(
                    request=request,
                    provider=provider.name,
                    state=response.state,
                    cache_outcome="miss_store",
                    started_at=request_started,
                )
                return response
            breaker.record_failure(now=time.monotonic(), error_code=response.error_code)
            provider_failures.append(
                {"provider": provider.name, "error_code": response.error_code or "PROVIDER_UNAVAILABLE"}
            )
            if allow_stale:
                cached_stale = self.cache.get(key, now=time.monotonic(), allow_stale=True)
                if cached_stale and cached_stale.state == "cached_stale":
                    stale_candidates.append(cached_stale)

        if stale_candidates:
            self._log_market_data(
                request=request,
                provider=stale_candidates[0].provider,
                state=stale_candidates[0].state,
                cache_outcome="fallback_stale",
                started_at=request_started,
            )
            return stale_candidates[0]
        self._log_market_data(
            request=request,
            provider="none",
            state="unavailable",
            cache_outcome="miss",
            started_at=request_started,
            provider_failures=provider_failures,
        )
        return ProviderResponse.unavailable("none", error_code="ALL_PROVIDERS_UNAVAILABLE")

    def _log_market_data(
        self,
        *,
        request: MarketDataRequest,
        provider: str,
        state: DataState,
        cache_outcome: str,
        started_at: float,
        provider_failures: list[dict[str, str]] | None = None,
    ) -> None:
        try:
            from backend.services.observability import log_event

            log_event(
                self.logger,
                "market_data_request",
                request_type=request.request_type,
                provider=provider,
                state=state,
                cache_outcome=cache_outcome,
                latency_ms=round((time.perf_counter() - started_at) * 1000, 2),
                provider_failures=provider_failures,
            )
        except Exception:
            self.logger.debug("market_data_observability_failed", exc_info=True)

    def _call(self, provider: MarketDataProvider, request: MarketDataRequest) -> ProviderResponse:
        for attempt in range(self.policy.max_retries + 1):
            future = self._executor.submit(self._dispatch, provider, request)
            try:
                response = future.result(timeout=self.policy.timeout_seconds)
            except TimeoutError:
                future.cancel()
                response = ProviderResponse.unavailable(provider.name, error_code="PROVIDER_TIMEOUT")
            except Exception:
                response = ProviderResponse.unavailable(provider.name, error_code="PROVIDER_ERROR")
            if isinstance(response, ProviderResponse) and response.state in {"live", "demo"}:
                return response
            if attempt < self.policy.max_retries and self.policy.retry_jitter_seconds > 0:
                time.sleep(random.uniform(0, self.policy.retry_jitter_seconds))
        return response if isinstance(response, ProviderResponse) else ProviderResponse.unavailable(provider.name)

    def _dispatch(self, provider: MarketDataProvider, request: MarketDataRequest) -> ProviderResponse:
        if request.request_type == "quote":
            return provider.quote(request.symbol or "")
        if request.request_type == "history":
            return provider.history(request.symbol or "", period=request.period or "1y", interval=request.interval or "1d")
        if request.request_type == "search":
            return provider.search(request.query or "", limit=request.limit or 15)
        return provider.indices()


def build_market_data_client(*, disabled: bool, timeout_seconds: int, cache_ttl_seconds: int) -> ResilientMarketDataClient:
    policy = ProviderPolicy(timeout_seconds=float(timeout_seconds), cache_ttl_seconds=float(cache_ttl_seconds))
    if disabled:
        return ResilientMarketDataClient([UnavailableMarketDataProvider()], policy=policy)
    try:
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)
    except ImportError:
        pass
    providers: list[MarketDataProvider] = [
        YFinanceMarketDataProvider(),
        ApiKeyMarketDataProvider(
            name="alpha_vantage",
            api_key_env="ALPHA_VANTAGE_API_KEY",
            api_key_aliases=("ALPHA_VANTAGE_KEY",),
        ),
        ApiKeyMarketDataProvider(
            name="twelve_data",
            api_key_env="TWELVE_DATA_API_KEY",
            api_key_aliases=("TWELVE_DATA_KEY",),
        ),
        ApiKeyMarketDataProvider(
            name="finnhub",
            api_key_env="FINNHUB_API_KEY",
            api_key_aliases=("FINNHUB_KEY",),
        ),
    ]
    return ResilientMarketDataClient(providers, policy=policy)
