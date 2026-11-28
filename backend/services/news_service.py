"""GNews-backed article read models with a stale in-memory fallback."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import os
import threading
import time
from typing import Any, Callable

import requests


NormalizeSymbol = Callable[[Any], str | None]
logger = logging.getLogger("stocksense.news")
GNEWS_SEARCH_URL = "https://gnews.io/api/v4/search"
DEFAULT_CACHE_TTL_SECONDS = 300
DEFAULT_MIN_INTERVAL_SECONDS = 1.1


class NewsService:
    def __init__(
        self,
        *,
        normalize_symbol: NormalizeSymbol,
        api_key: str | None = None,
        session: requests.Session | None = None,
        cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
        min_interval_seconds: float = DEFAULT_MIN_INTERVAL_SECONDS,
    ):
        self._normalize_symbol = normalize_symbol
        # GNews limits request rate (free plans allow about one request per
        # second), so upstream calls from this process are spaced out.
        self._min_interval_seconds = max(0.0, min_interval_seconds)
        self._upstream_lock = threading.Lock()
        self._last_upstream_call: float | None = None
        self._api_key = (
            os.getenv("GNEWS_API_KEY", "").strip() if api_key is None else api_key.strip()
        )
        self._session = session or requests.Session()
        self._cache_ttl_seconds = max(0, cache_ttl_seconds)
        self._cache: dict[str, tuple[float, str, list[dict[str, Any]]]] = {}
        # Reason for the most recent fallback; None after a live success.
        self.last_error_code: str | None = None

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _fetch_articles(self, query: str) -> dict[str, Any]:
        cache_key = query.strip().lower()
        cached = self._cache.get(cache_key)
        now = time.monotonic()
        if cached and cached[0] > now:
            return self._response(
                articles=cached[2],
                source="gnews_cache",
                data_quality="cached",
                timestamp=cached[1],
            )
        if not self._api_key:
            return self._fallback(cached, error_code="KEY_MISSING")

        try:
            response = self._throttled_get(query)
            if response.status_code == 429:
                # One retry after the spacing interval covers a per-second limit.
                response = self._throttled_get(query)
            if response.status_code == 429:
                return self._fallback(cached, error_code="RATE_LIMITED")
            if response.status_code in (401, 403):
                return self._fallback(cached, error_code="KEY_REJECTED")
            response.raise_for_status()
            payload = response.json()
        except requests.HTTPError as exc:
            status = getattr(exc.response, "status_code", None)
            return self._fallback(cached, error_code=f"HTTP_{status}" if status else "HTTP_ERROR")
        except requests.RequestException as exc:
            return self._fallback(cached, error_code=f"REQUEST_{type(exc).__name__.upper()}")
        except ValueError:
            return self._fallback(cached, error_code="MALFORMED_RESPONSE")

        if not isinstance(payload, dict) or not isinstance(payload.get("articles"), list):
            return self._fallback(cached, error_code="MALFORMED_RESPONSE")
        self.last_error_code = None

        articles = [
            normalized
            for article in payload["articles"]
            if (normalized := _normalize_article(article)) is not None
        ]
        fetched_at = self._timestamp()
        self._cache[cache_key] = (
            time.monotonic() + self._cache_ttl_seconds,
            fetched_at,
            articles,
        )
        return self._response(
            articles=articles, source="gnews", data_quality="live", timestamp=fetched_at
        )

    def _throttled_get(self, query: str) -> Any:
        with self._upstream_lock:
            if self._last_upstream_call is not None and self._min_interval_seconds > 0:
                wait = self._min_interval_seconds - (time.monotonic() - self._last_upstream_call)
                if wait > 0:
                    time.sleep(wait)
            try:
                return self._session.get(
                    GNEWS_SEARCH_URL,
                    params={
                        "q": query,
                        "lang": "en",
                        "apikey": self._api_key,
                        "max": 10,
                    },
                    timeout=8,
                )
            finally:
                self._last_upstream_call = time.monotonic()

    def _fallback(
        self,
        cached: tuple[float, str, list[dict[str, Any]]] | None,
        *,
        error_code: str,
    ) -> dict[str, Any]:
        # Log only a reason code: never the key, URL, or provider response body.
        self.last_error_code = error_code
        logger.warning("news_provider_fallback error_code=%s has_cache=%s", error_code, bool(cached))
        if cached:
            return self._response(
                articles=cached[2],
                source="gnews_cache",
                data_quality="cached_stale",
                timestamp=cached[1],
            )
        return self._response(articles=[], source="unavailable", data_quality="unavailable")

    def _response(
        self,
        *,
        articles: list[dict[str, Any]],
        source: str,
        data_quality: str,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        return {
            "success": True,
            "articles": articles,
            "data": articles,
            "source": source,
            "data_quality": data_quality,
            "timestamp": timestamp or self._timestamp(),
        }

    def market_news(self) -> dict[str, Any]:
        return self._fetch_articles("stock market OR finance OR economy")

    def symbol_news(self, symbol: str) -> dict[str, Any]:
        normalized = self._normalize_symbol(symbol)
        if not normalized:
            return {
                **self._response(articles=[], source="unavailable", data_quality="unavailable"),
                "symbol": None,
            }
        return {
            **self._fetch_articles(f'"{normalized}" stock OR company'),
            "symbol": normalized,
        }

    def alerts(self) -> dict[str, Any]:
        return {
            "success": True,
            "active_alerts": 0,
            "triggered_today": 0,
            "alerts": [],
            "data": [],
            "timestamp": self._timestamp(),
        }

    def research(self) -> dict[str, Any]:
        return {
            "success": True,
            "researchreports": [],
            "aiinsights": [],
            "model_performance": {},
            "live_stats": {},
            "data": [],
            "message": "Research providers are unavailable in the lightweight factory runtime.",
            "data_quality": "unavailable",
            "timestamp": self._timestamp(),
        }


def _normalize_article(article: Any) -> dict[str, Any] | None:
    if not isinstance(article, dict):
        return None
    title = article.get("title")
    url = article.get("url")
    if not isinstance(title, str) or not isinstance(url, str):
        return None
    source = article.get("source")
    if isinstance(source, dict):
        source = source.get("name")
    return {
        "title": title,
        "summary": article.get("description"),
        "url": url,
        "published_at": article.get("publishedAt"),
        "source": source if isinstance(source, str) else None,
    }
