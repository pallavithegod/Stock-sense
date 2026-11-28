"""Read-only live GNews check. Prints status, article counts and sources only.

Never prints the API key, request URL, or article text. Writes nothing.
Run from the repository root:

    .\\.venv\\Scripts\\python.exe -m scripts.check_news_provider
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from backend.domain.market import normalize_symbol
from backend.services.news_service import NewsService


def _load_local_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)


def _summarize(payload: dict, service: NewsService) -> dict:
    articles = payload.get("articles") or []
    return {
        "data_quality": payload.get("data_quality"),
        "source": payload.get("source"),
        "article_count": len(articles),
        "error_code": service.last_error_code,
        "sample_publishers": sorted({str(a.get("source")) for a in articles if a.get("source")})[:5],
        "has_title_and_url": bool(articles) and all(a.get("title") and a.get("url") for a in articles),
    }


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    _load_local_env()
    service = NewsService(normalize_symbol=normalize_symbol)
    result = {
        "key_configured": bool(service._api_key),
        "market": _summarize(service.market_news(), service),
        "symbol_INFY": _summarize(service.symbol_news("INFY"), service),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    live = result["market"]["data_quality"] == "live" and result["symbol_INFY"]["data_quality"] == "live"
    return 0 if live else 1


if __name__ == "__main__":
    raise SystemExit(main())
