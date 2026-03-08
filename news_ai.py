# news_ai.py
import os
import math
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
import requests
import numpy as np

logger = logging.getLogger(__name__)

class QuantumNewsAI:
    """
    Canonical News + Sentiment Intelligence Layer
    Fully compatible with:
    - app.py
    - IntegratedForesightSystem
    - IntelligenceCore (Emotion + Sentiment dynamics)
    """

    def __init__(self, news_api_key: Optional[str] = None):
        self.news_api_key = news_api_key or os.getenv("NEWS_API_KEY")
        self.foresight_system = None

        self.news_cache: List[Dict] = []
        self.sector_cache: Dict[str, List[Dict]] = {}
        self.cache_time: Optional[datetime] = None
        self.cache_ttl: int = 300  # seconds

        self.SECTOR_KEYWORDS = {
            "BANKING": ["bank", "loan", "nbfc", "credit", "finance"],
            "IT": ["software", "tech", "cloud", "digital"],
            "ENERGY": ["oil", "gas", "power", "energy"],
            "METALS": ["steel", "aluminium", "copper"],
            "PHARMA": ["pharma", "drug", "medicine"],
            "AUTO": ["auto", "vehicle", "ev"],
        }

        logger.info("[OK] QuantumNewsAI initialized")

    # ----------------------------------------------------
    # 🔗 SYSTEM BIND
    # ----------------------------------------------------
    def bind_foresight_system(self, foresight_system):
        """
        Late binding to prevent circular imports.
        """
        self.foresight_system = foresight_system
        logger.info("🧠 QuantumNewsAI bound to foresight system")

        # Initialize memory if not already present
        if not hasattr(self, 'symbol_sentiment_memory'):
            self.symbol_sentiment_memory: Dict[str, List[float]] = {}
    
    def sentiment_reliability_score(self, symbol, sentiment_value, news_volume, market_volatility):
        """
        Calculate reliability based on volume, volatility and sentiment stability.
        """
        base_reliability = 0.5
        
        # Volume boost
        if news_volume > 5:
            base_reliability += 0.2
        elif news_volume > 2:
            base_reliability += 0.1
            
        # Volatility penalty
        if market_volatility and market_volatility > 20:
            base_reliability -= 0.1
            
        return min(max(base_reliability, 0.1), 0.95)

    # ----------------------------------------------------
    # 🧠 SENTIMENT — AUTO ADAPTIVE
    # ----------------------------------------------------
    def analyze_sentiment(self, text: str):
        """
        Universal sentiment adapter.
        Works even if SentimentDynamicsEngine has NO text API.
        """
        try:
            fs = self.foresight_system
            engine = getattr(fs, "sentiment_dynamics", None)

            # CASE 1: Explicit callable APIs
            for method in ("analyze", "get_sentiment", "sentiment", "evaluate"):
                if hasattr(engine, method):
                    r = getattr(engine, method)(text)
                    break
            else:
                r = None  # fallthrough

            # Normalize dict output
            if isinstance(r, dict):
                score = float(r.get("score", 0.0))
                return {
                    "score": score,
                    "label": r.get("label", "neutral"),
                    "confidence": float(r.get("confidence", abs(score))),
                }

            # Normalize scalar output
            if isinstance(r, (int, float)):
                return {
                    "score": float(r),
                    "label": "positive" if r > 0 else "negative" if r < 0 else "neutral",
                    "confidence": abs(float(r)),
                }

            # CASE 2: ENGINE HAS NO TEXT INTERFACE → REGIME-BASED SENTIMENT
            regime = getattr(fs, "current_regime", "BALANCED")
            mapping = {
                "GREED": 0.35,
                "FEAR": -0.35,
                "PANIC": -0.6,
                "EUPHORIA": 0.6,
                "BALANCED": 0.0,
            }
            score = mapping.get(regime, 0.0)

            return {
                "score": score,
                "label": regime,
                "confidence": abs(score),
            }

        except Exception as e:
            logger.warning(f"Sentiment analysis fallback used: {e}")
            return {"score": 0.0, "label": "neutral", "confidence": 0.0}

    # ----------------------------------------------------
    # 📰 RSS NEWS
    # ----------------------------------------------------
    def fetch_rss_news(self) -> List[Dict]:
        articles = []
        try:
            import feedparser
            feeds = [
                ("https://feeds.finance.yahoo.com/rss/2.0/headline", "Yahoo Finance"),
                ("https://www.moneycontrol.com/rss/latestnews.xml", "MoneyControl"),
                ("https://www.livemint.com/rss/markets", "LiveMint"),
            ]

            for url, source in feeds:
                try:
                    feed = feedparser.parse(url)
                    for e in feed.entries[:6]:
                        title = e.get("title", "")
                        desc = e.get("summary", "") or e.get("description", "")
                        if not title:
                            continue

                        s = self.analyze_sentiment(f"{title} {desc}")

                        articles.append({
                            "title": title,
                            "description": desc[:300] if desc else "",
                            "url": e.get("link", ""),
                            "source": source,
                            "published": e.get("published"),
                            "normalized_time": self._normalize_time(e),
                            "sentiment": s["label"],
                            "sentiment_score": s["score"],   # 🔑 FLOAT ONLY
                            "confidence": s["confidence"],
                            "why_it_matters": self._why_it_matters(s),
                            "relevance": self._relevance(f"{title} {desc}"),
                            "sector": self._infer_sector({"title": title, "description": desc}),
                        })
                except Exception as ex:
                    logger.warning(f"Failed to parse feed {url}: {ex}")

        except Exception as e:
            logger.warning(f"RSS fetch cycle failed: {e}")
        return articles

    # ----------------------------------------------------
    # 📰 NEWS API (SYMBOL SPECIFIC)
    # ----------------------------------------------------
    def fetch_symbol_news(self, symbol: str) -> List[Dict]:
        articles = []
        try:
            if not self.news_api_key:
                return []

            from newsapi import NewsApiClient
            client = NewsApiClient(api_key=self.news_api_key)

            # Clean symbol for search
            search_query = symbol.replace(".NS", "").replace(".BO", "")
            
            resp = client.get_everything(
                q=search_query,
                language="en",
                page_size=10,
                sort_by="publishedAt",
            )

            for a in resp.get("articles", []):
                title = a.get("title", "")
                desc = a.get("description") or ""
                if not title:
                    continue

                s = self.analyze_sentiment(f"{title} {desc}")

                articles.append({
                    "title": title,
                    "description": desc[:300] if desc else "",
                    "url": a.get("url"),
                    "source": a.get("source", {}).get("name"),
                    "published": a.get("publishedAt"),
                    "normalized_time": a.get("publishedAt"),
                    "sentiment": s["label"],
                    "sentiment_score": s["score"],
                    "confidence": s["confidence"],
                    "why_it_matters": self._why_it_matters(s),
                    "relevance": self._relevance(f"{title} {desc}", search_query),
                    "sector": self._infer_sector({"title": title, "description": desc}),
                })
                
            # Update Sentiment Memory
            if symbol not in self.symbol_sentiment_memory:
                self.symbol_sentiment_memory[symbol] = []
            
            # Store last 50 sentiment scores
            scores = [a["sentiment_score"] for a in articles]
            if scores:
                self.symbol_sentiment_memory[symbol].extend(scores)
                self.symbol_sentiment_memory[symbol] = self.symbol_sentiment_memory[symbol][-50:]
                
        except Exception as e:
            logger.warning(f"Symbol news fetch failed for {symbol}: {e}")
            if symbol not in self.symbol_sentiment_memory:
                 self.symbol_sentiment_memory[symbol] = []
        return articles

    # ----------------------------------------------------
    # 🧩 AGGREGATION & CACHING
    # ----------------------------------------------------
    def get_aggregated_news(self, force_refresh: bool = False) -> Dict:
        cache_time = self.cache_time
        if cache_time and getattr(cache_time, "tzinfo", None) is None:
            cache_time = cache_time.replace(tzinfo=timezone.utc)
        if (
            not force_refresh
            and self.news_cache
            and cache_time
            and (datetime.now(timezone.utc) - cache_time).seconds < self.cache_ttl
        ):
            return {"articles": self.news_cache, "sectorwise": self.sector_cache}

        articles = self.fetch_rss_news()
        
        # Optionally add some general NewsAPI articles if key exists
        if self.news_api_key:
            try:
                articles.extend(self._fetch_general_newsapi())
            except:
                pass

        # Deduplicate by title
        unique = {}
        for a in articles:
            key = str(a.get("title", "")).lower()[:80]
            if key and key not in unique:
                unique[key] = a

        final = list(unique.values())
        final.sort(key=lambda x: x.get("normalized_time") or "", reverse=True)

        from collections import defaultdict
        sectorwise = defaultdict(list)
        for a in final:
            sectorwise[a["sector"]].append(a)

        self.news_cache = final[:25]
        self.sector_cache = dict(sectorwise)
        self.cache_time = datetime.now(timezone.utc)

        return {"articles": self.news_cache, "sectorwise": self.sector_cache}

    def _fetch_general_newsapi(self) -> List[Dict]:
        if not self.news_api_key: return []
        r = requests.get(
            "https://newsapi.org/v2/top-headlines",
            params={
                "language": "en",
                "category": "business",
                "pageSize": 20,
                "apiKey": self.news_api_key,
            },
            timeout=10,
        )
        raw = r.json().get("articles", [])
        
        articles = []
        for a in raw:
            title = a.get("title") or ""
            desc = a.get("description") or ""
            if not title: continue
            
            s = self.analyze_sentiment(f"{title} {desc}")
            articles.append({
                "title": title,
                "description": desc[:300],
                "url": a.get("url"),
                "source": a.get("source", {}).get("name"),
                "published": a.get("publishedAt"),
                "normalized_time": a.get("publishedAt"),
                "sentiment": s["label"],
                "sentiment_score": s["score"],
                "confidence": s["confidence"],
                "why_it_matters": self._why_it_matters(s),
                "relevance": self._relevance(f"{title} {desc}"),
                "sector": self._infer_sector({"title": title, "description": desc}),
            })
        return articles

    # ----------------------------------------------------
    # 📊 MARKET SENTIMENT (COMPREHENSIVE CONTRACT)
    # ----------------------------------------------------
    def get_market_sentiment_analysis(self) -> Dict:
        """
        Calculates market-wide sentiment from aggregated news memory.
        """
        bundle = self.get_aggregated_news()
        articles = bundle.get("articles", [])

        if not articles:
            return self._empty_market_sentiment()

        scores = [a.get("sentiment_score", 0.0) for a in articles]
        avg = float(np.mean(scores))

        return {
            "overall_score": round(avg * 100, 1),
            "confidence": round(float(np.mean([a.get("confidence", 0.5) for a in articles])), 2),
            "label": "POSITIVE" if avg > 0.05 else "NEGATIVE" if avg < -0.05 else "NEUTRAL",
            "heatmap": self._confidence_heatmap(articles),
            "bullish_count": sum(1 for s in scores if s > 0.05),
            "bearish_count": sum(1 for s in scores if s < -0.05),
            "neutral_count": sum(1 for s in scores if -0.05 <= s <= 0.05),
            "total_articles": len(articles),
        }

    # ----------------------------------------------------
    # 📊 SYMBOL SENTIMENT (COMPATIBILITY)
    # ----------------------------------------------------
    def get_sentiment(self, symbol: str) -> Dict:
        articles = self.fetch_symbol_news(symbol)
        if not articles:
            return {"overall_score": 0.0, "confidence": 0.0, "label": "neutral"}

        scores = [a.get("sentiment_score", 0.0) for a in articles]
        avg = float(np.mean(scores))
        
        return {
            "overall_score": round(avg * 100, 2),
            "confidence": round(float(np.mean([a.get("confidence", 0.5) for a in articles])), 2),
            "label": "positive" if avg > 0 else "negative" if avg < 0 else "neutral",
        }

    def get_symbol_reliability_score(self, symbol: str) -> float:
        articles = self.fetch_symbol_news(symbol)
        if not articles:
            return 0.0
        return float(np.mean([a.get("confidence", 0.0) for a in articles]))

    # ----------------------------------------------------
    # 🧠 HELPERS
    # ----------------------------------------------------
    def _why_it_matters(self, s: Dict) -> str:
        score = s.get("score", 0.0)
        if score > 0.2:
            return "Strong positive sentiment may support upward price momentum."
        if score < -0.2:
            return "Negative sentiment could increase downside risk."
        return "Neutral sentiment suggests limited immediate market impact."

    def _confidence_heatmap(self, articles: List[Dict]) -> List[Dict]:
        return [
            {
                "title": a.get("title", ""),
                "confidence": round(a.get("confidence", 0.0), 2),
                "sentiment": a.get("sentiment", "neutral"),
            }
            for a in articles[:10]
        ]

    def _relevance(self, text: str, symbol: Optional[str] = None) -> float:
        text = str(text).lower()
        score = len(text) / 500
        if symbol:
            score += text.count(symbol.lower()) * 2.0
        return min(1.0, score)

    def _normalize_time(self, entry: Dict) -> Optional[str]:
        for k in ("published", "pubDate", "updated"):
            if entry.get(k):
                return entry[k]
        return None

    def _infer_sector(self, article: Dict) -> str:
        text = (str(article.get("title", "")) + " " + str(article.get("description", ""))).lower()
        for sector, keys in self.SECTOR_KEYWORDS.items():
            if any(k in text for k in keys):
                return sector
        return "GENERAL"

    def _empty_market_sentiment(self) -> Dict:
        return {
            "overall_score": 0.0,
            "confidence": 0.0,
            "label": "NEUTRAL",
            "heatmap": [],
            "bullish_count": 0,
            "bearish_count": 0,
            "neutral_count": 0,
            "total_articles": 0,
        }
