from __future__ import annotations

import pytest

from backend.domain.market import normalize_symbol
from backend.services.news_service import GNEWS_SEARCH_URL, NewsService


def test_market_news_returns_explicit_unavailable_state(client):
    response = client.get("/api/v1/news/market")

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["articles"] == []
    assert payload["data_quality"] == "unavailable"


def test_symbol_news_normalizes_symbol(client):
    response = client.get("/api/v1/news/symbol/infy.ns")

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["success"] is True
    assert payload["symbol"] == "INFY"
    assert payload["articles"] == []


def test_gnews_fetch_normalizes_article_and_uses_configured_search_params():
    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "articles": [
                    {
                        "title": "Company update",
                        "description": "A concise summary",
                        "url": "https://example.test/article",
                        "publishedAt": "2026-11-27T12:00:00Z",
                        "source": {"name": "Example News"},
                    }
                ]
            }

    class FakeSession:
        def __init__(self):
            self.call = None

        def get(self, url, **kwargs):
            self.call = (url, kwargs)
            return FakeResponse()

    session = FakeSession()
    service = NewsService(
        normalize_symbol=normalize_symbol,
        api_key="test-key",
        session=session,
    )

    payload = service.symbol_news("infy.ns")

    assert session.call[0] == GNEWS_SEARCH_URL
    assert session.call[1]["params"] == {
        "q": '"INFY" stock OR company',
        "lang": "en",
        "apikey": "test-key",
        "max": 10,
    }
    assert payload["data_quality"] == "live"
    assert payload["symbol"] == "INFY"
    assert payload["articles"] == [
        {
            "title": "Company update",
            "summary": "A concise summary",
            "url": "https://example.test/article",
            "published_at": "2026-11-27T12:00:00Z",
            "source": "Example News",
        }
    ]


def test_gnews_rate_limit_falls_back_to_cached_articles():
    class FakeResponse:
        def __init__(self, status_code, payload=None):
            self.status_code = status_code
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class FakeSession:
        def __init__(self):
            self.responses = [
                FakeResponse(
                    200, {"articles": [{"title": "Cached story", "url": "https://example.test"}]}
                ),
                FakeResponse(429),
            ]

        def get(self, url, **kwargs):
            return self.responses.pop(0)

    service = NewsService(
        normalize_symbol=normalize_symbol,
        api_key="test-key",
        session=FakeSession(),
        cache_ttl_seconds=0,
    )

    initial = service.market_news()
    limited = service.market_news()

    assert initial["data_quality"] == "live"
    assert limited["data_quality"] == "cached_stale"
    assert limited["articles"][0]["title"] == "Cached story"


def test_gnews_without_key_returns_empty_unavailable_state():
    class FakeSession:
        def get(self, url, **kwargs):
            raise AssertionError("GNews should not be called without a key")

    service = NewsService(normalize_symbol=normalize_symbol, api_key="", session=FakeSession())

    payload = service.market_news()

    assert payload["articles"] == []
    assert payload["data_quality"] == "unavailable"


def _news_service_with(response_or_exc, *, api_key="test-key"):
    import requests

    class FakeResponse:
        def __init__(self, status_code, payload=None, raise_error=False):
            self.status_code = status_code
            self.payload = payload
            self.raise_error = raise_error

        def raise_for_status(self):
            if self.raise_error:
                raise requests.HTTPError("boom", response=self)

        def json(self):
            if isinstance(self.payload, Exception):
                raise self.payload
            return self.payload

    class FakeSession:
        def get(self, url, **kwargs):
            if isinstance(response_or_exc, Exception):
                raise response_or_exc
            return response_or_exc(FakeResponse)

    return NewsService(normalize_symbol=normalize_symbol, api_key=api_key, session=FakeSession())


@pytest.mark.parametrize(
    ("make_response", "expected_code"),
    [
        (lambda R: R(429), "RATE_LIMITED"),
        (lambda R: R(401), "KEY_REJECTED"),
        (lambda R: R(403), "KEY_REJECTED"),
        (lambda R: R(500, raise_error=True), "HTTP_500"),
        (lambda R: R(200, payload=ValueError("bad json")), "MALFORMED_RESPONSE"),
        (lambda R: R(200, payload={"articles": "nope"}), "MALFORMED_RESPONSE"),
        (lambda R: R(200, payload=["not", "a", "dict"]), "MALFORMED_RESPONSE"),
    ],
)
def test_gnews_failures_report_distinct_reason_without_leaking_key(make_response, expected_code, caplog):
    service = _news_service_with(make_response)

    payload = service.market_news()

    assert payload["articles"] == []
    assert payload["data_quality"] == "unavailable"
    assert service.last_error_code == expected_code
    assert f"news_provider_fallback error_code={expected_code}" in caplog.text
    assert "test-key" not in caplog.text


def test_gnews_network_error_and_missing_key_reasons_and_success_resets():
    import requests

    network = _news_service_with(requests.ConnectionError("down"))
    network.market_news()
    assert network.last_error_code == "REQUEST_CONNECTIONERROR"

    missing = _news_service_with(lambda R: R(200, payload={"articles": []}), api_key="")
    missing.market_news()
    assert missing.last_error_code == "KEY_MISSING"

    ok = _news_service_with(lambda R: R(200, payload={"articles": []}))
    ok.last_error_code = "RATE_LIMITED"
    assert ok.market_news()["data_quality"] == "live"
    assert ok.last_error_code is None


def test_research_payload_matches_frontend_shape(client):
    response = client.get("/api/v1/research")

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["research_reports"] == []
    assert payload["ai_insights"] == []
    assert payload["data_quality"] == "unavailable"


def test_foresight_research_routes_are_registered_without_live_provider(client):
    emotional = client.get("/api/v1/emotional-state/INFY")
    futures = client.get("/api/v1/futures-analysis/INFY")

    assert emotional.status_code == 200
    assert emotional.get_json()["data"]["success"] is True
    assert emotional.get_json()["data"]["available"] is False
    assert futures.status_code == 200
    assert futures.get_json()["data"]["success"] is True
    assert futures.get_json()["data"]["available"] is False


def test_legacy_news_and_research_aliases_are_removed(client):
    assert client.get("/api/news/market").status_code == 404
    assert client.get("/api/news/symbol/INFY").status_code == 404
    assert client.get("/api/research").status_code == 404
