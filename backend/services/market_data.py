"""Market data provider boundary with cache and failure isolation."""

from __future__ import annotations

import os
import random
import time
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Protocol


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
    """Secondary provider shell that owns API-key configuration without exposing secrets."""

    def __init__(self, *, name: str, api_key_env: str):
        self.name = name
        self.api_key_env = api_key_env
        self._configured = bool(os.getenv(api_key_env))

    def _response(self) -> ProviderResponse:
        code = "PROVIDER_NOT_IMPLEMENTED" if self._configured else "PROVIDER_NOT_CONFIGURED"
        return ProviderResponse.unavailable(self.name, error_code=code)

    def quote(self, symbol: str) -> ProviderResponse:
        return self._response()

    def history(self, symbol: str, *, period: str, interval: str) -> ProviderResponse:
        return self._response()

    def search(self, query: str, *, limit: int) -> ProviderResponse:
        return self._response()

    def indices(self) -> ProviderResponse:
        return self._response()

    def health(self) -> dict[str, Any]:
        status = "configured" if self._configured else "missing_key"
        return {"configured": self._configured, "status": status, "api_key_env": self.api_key_env}


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

    def _history_payload_from_frame(self, symbol: str, frame: Any) -> ProviderResponse:
        if frame is None or getattr(frame, "empty", False):
            return ProviderResponse.unavailable(self.name, error_code="EMPTY_RESPONSE", data=[])
        required = {"Open", "High", "Low", "Close", "Volume"}
        columns = set(getattr(frame, "columns", []) or [])
        if not required.issubset(columns):
            return ProviderResponse.unavailable(self.name, error_code="MALFORMED_RESPONSE", data=[])
        rows = []
        for timestamp, row in frame.tail(250).iterrows():
            try:
                values = {
                    "open": float(row.get("Open")),
                    "high": float(row.get("High")),
                    "low": float(row.get("Low")),
                    "close": float(row.get("Close")),
                    "volume": int(row.get("Volume")),
                }
            except (TypeError, ValueError):
                continue
            if (
                min(values["open"], values["high"], values["low"], values["close"]) <= 0
                or values["high"] < max(values["open"], values["low"], values["close"])
                or values["low"] > min(values["open"], values["high"], values["close"])
                or values["volume"] < 0
            ):
                continue
            rows.append({"timestamp": str(timestamp), **values})
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
        for candidate in exchange_candidates(symbol, default_exchange=self.default_exchange):
            frame = yf.Ticker(candidate).history(period=period, interval=interval)
            response = self._history_payload_from_frame(symbol, frame)
            if response.state == "live":
                return response
        return ProviderResponse.unavailable(self.name, error_code="EMPTY_RESPONSE", data=[])

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
    providers: list[MarketDataProvider] = [
        YFinanceMarketDataProvider(),
        ApiKeyMarketDataProvider(name="alpha_vantage", api_key_env="ALPHA_VANTAGE_API_KEY"),
        ApiKeyMarketDataProvider(name="twelve_data", api_key_env="TWELVE_DATA_API_KEY"),
        ApiKeyMarketDataProvider(name="finnhub", api_key_env="FINNHUB_API_KEY"),
    ]
    return ResilientMarketDataClient(providers, policy=policy)
