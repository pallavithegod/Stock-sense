from __future__ import annotations

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
