# -*- coding: utf-8 -*-
# news_ai.py
from utils import encoding
import os
import math
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List, Dict, Optional, Any
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
        self.narrative_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

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
            feeds = self._get_feed_sources()

            for url, source in feeds:
                try:
                    feed = feedparser.parse(url)
                    # Process up to 20 entries per feed (increased from default)
                    entries_to_process = feed.entries[:20] if len(feed.entries) > 20 else feed.entries
                    
                    for e in entries_to_process:
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
                    continue  # Continue with other feeds even if one fails

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
                # Add targeted financial news
                articles.extend(self._fetch_targeted_newsapi())
            except:
                pass

        # Deduplicate by title
        unique = {}
        for a in articles:
            key = str(a.get("title", "")).lower()[:80]
            if key and key not in unique:
                unique[key] = a

        final = list(unique.values())
        if final:
            source_profiles = defaultdict(list)
            for article in final:
                source_profiles[str(article.get("source") or "UNKNOWN")].append(self._article_freshness(article))
            source_scores = {
                source: max(scores) if scores else 0.0
                for source, scores in source_profiles.items()
            }
            source_cutoff = float(np.percentile(list(source_scores.values()), 50)) if source_scores else 0.0
            preferred_sources = {source for source, score in source_scores.items() if score >= source_cutoff}
            if preferred_sources:
                filtered = [article for article in final if str(article.get("source") or "UNKNOWN") in preferred_sources]
                if filtered:
                    final = filtered
            freshness_series = np.array(
                [self._article_freshness(article) for article in final if article.get("normalized_time") or article.get("published")],
                dtype=float
            )
            if freshness_series.size:
                freshness_cutoff = float(np.percentile(freshness_series, 35))
                freshest = [
                    article for article in final
                    if self._article_freshness(article) >= freshness_cutoff
                ]
                if freshest:
                    final = freshest
        final.sort(key=lambda x: x.get("normalized_time") or "", reverse=True)

        sectorwise = defaultdict(list)
        for a in final:
            sectorwise[a["sector"]].append(a)

        self.news_cache = final
        self.sector_cache = dict(sectorwise)
        self.cache_time = datetime.now(timezone.utc)

        return {"articles": self.news_cache, "sectorwise": self.sector_cache}

    def _fetch_general_newsapi(self) -> List[Dict]:
        if not self.news_api_key: return []
        
        categories = ["business", "technology", "general"]
        all_articles = []
        
        for category in categories:
            try:
                r = requests.get(
                    "https://newsapi.org/v2/top-headlines",
                    params={
                        "language": "en",
                        "category": category,
                        "pageSize": 30,  # Increased from 20
                        "apiKey": self.news_api_key,
                    },
                    timeout=3,
                )
                raw = r.json().get("articles", [])
                
                for a in raw:
                    title = a.get("title") or ""
                    desc = a.get("description") or ""
                    if not title: continue
                    
                    s = self.analyze_sentiment(f"{title} {desc}")
                    all_articles.append({
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
            except Exception as e:
                print(f"Error fetching {category} news: {e}")
                continue
        
        # Remove duplicates based on title
        seen_titles = set()
        unique_articles = []
        for article in all_articles:
            if article["title"] not in seen_titles:
                seen_titles.add(article["title"])
                unique_articles.append(article)
        
        return unique_articles[:50]  # Limit to 50 articles total

    def _fetch_targeted_newsapi(self, query: str = "stocks OR market OR economy OR finance") -> List[Dict]:
        """Fetch targeted news articles using NewsAPI with specific keywords."""
        if not self.news_api_key: return []
        
        try:
            r = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": query,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": 25,
                    "apiKey": self.news_api_key,
                },
                timeout=3,
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
        except Exception as e:
            print(f"Error fetching targeted news: {e}")
            return []

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
        for key in ("published_parsed", "updated_parsed"):
            parsed_struct = entry.get(key)
            if parsed_struct:
                try:
                    return datetime(*parsed_struct[:6], tzinfo=timezone.utc).isoformat()
                except Exception:
                    continue
        for k in ("published", "pubDate", "updated"):
            if entry.get(k):
                parsed = self._safe_parse_time(entry.get(k))
                if parsed:
                    return parsed.isoformat()
                return str(entry.get(k))
        return None

    def _infer_sector(self, article: Dict) -> str:
        text = (str(article.get("title", "")) + " " + str(article.get("description", ""))).lower()
        for sector, keys in self._get_sector_profiles().items():
            if any(k in text for k in keys):
                return sector
        return "GENERAL"

    def _get_feed_sources(self) -> List[tuple]:
        raw = os.getenv("NEWS_RSS_FEEDS", "").strip()
        if raw:
            try:
                parsed = json.loads(raw)
                pairs = []
                for item in parsed:
                    if isinstance(item, dict) and item.get("url") and item.get("source"):
                        pairs.append((str(item["url"]), str(item["source"])))
                if pairs:
                    return pairs
            except Exception as e:
                logger.debug(f"NEWS_RSS_FEEDS parse failed: {e}")
        return [
            ("https://www.moneycontrol.com/rss/latestnews.xml", "MoneyControl"),
            ("https://www.livemint.com/rss/markets", "LiveMint"),
            ("https://feeds.marketwatch.com/marketwatch/marketpulse/", "MarketWatch"),
            ("https://www.cnbc.com/id/100003114/device/rss/rss.html", "CNBC"),
            ("https://www.investing.com/rss/news.rss", "Investing.com"),
            ("https://feeds.feedburner.com/ndtvprofit-latest", "NDTV Profit"),
            ("https://www.business-standard.com/rss/latest.rss", "Business Standard"),
        ]

    def _get_sector_profiles(self) -> Dict[str, List[str]]:
        raw = os.getenv("NEWS_SECTOR_KEYWORDS", "").strip()
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    cleaned = {
                        str(k).upper(): [str(v).lower() for v in vals if str(v).strip()]
                        for k, vals in parsed.items()
                        if isinstance(vals, list)
                    }
                    if cleaned:
                        return cleaned
            except Exception as e:
                logger.debug(f"NEWS_SECTOR_KEYWORDS parse failed: {e}")
        return self.SECTOR_KEYWORDS

    def _get_event_profiles(self) -> Dict[str, List[str]]:
        raw = os.getenv("NEWS_EVENT_PATTERNS", "").strip()
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    return {
                        str(k).upper(): [str(v).lower() for v in vals if str(v).strip()]
                        for k, vals in parsed.items()
                        if isinstance(vals, list)
                    }
            except Exception as e:
                logger.debug(f"NEWS_EVENT_PATTERNS parse failed: {e}")
        return {
            "EARNINGS": ["earnings", "results", "quarter", "guidance", "profit", "revenue"],
            "POLICY": ["policy", "rate", "inflation", "rbi", "fed", "central bank", "budget"],
            "GEOPOLITICAL": ["war", "sanction", "tariff", "conflict", "border", "military"],
            "COMMODITY": ["oil", "gold", "gas", "copper", "silver", "crude"],
            "CORPORATE": ["merger", "acquisition", "deal", "stake", "buyback", "dividend"],
            "REGULATION": ["regulation", "ban", "approval", "court", "compliance", "probe"],
            "MARKET_STRUCTURE": ["volume", "flow", "liquidity", "block trade", "delivery", "open interest"],
        }

    def _get_narrative_profiles(self) -> Dict[str, List[str]]:
        raw = os.getenv("NEWS_NARRATIVE_PATTERNS", "").strip()
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    return {
                        str(k).upper(): [str(v).lower() for v in vals if str(v).strip()]
                        for k, vals in parsed.items()
                        if isinstance(vals, list)
                    }
            except Exception as e:
                logger.debug(f"NEWS_NARRATIVE_PATTERNS parse failed: {e}")
        return {
            "AI_ADOPTION": ["ai", "artificial intelligence", "semiconductor", "data center"],
            "RATE_CYCLE": ["rate", "yield", "central bank", "inflation"],
            "ENERGY_STRESS": ["oil", "gas", "energy", "crude"],
            "BANKING_STRESS": ["bank", "credit", "liquidity", "nbfc"],
            "DEFENCE_SHIFT": ["defence", "military", "geopolitical", "war"],
            "CONSUMER_DEMAND": ["consumption", "fmcg", "retail", "demand"],
            "SUPPLY_CHAIN": ["shipping", "supply chain", "logistics", "port"],
        }

    def _build_text_blob(self, article: Dict) -> str:
        return " ".join([
            str(article.get("title", "")),
            str(article.get("description", "")),
            str(article.get("source", "")),
        ]).strip()

    def _safe_parse_time(self, value: Any) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        text = str(value).replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            try:
                dt = parsedate_to_datetime(str(value))
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except Exception:
                return None

    def _article_freshness(self, article: Dict) -> float:
        published_at = self._safe_parse_time(article.get("normalized_time") or article.get("published"))
        if not published_at:
            return 0.5
        age_hours = max(0.0, (datetime.now(timezone.utc) - published_at).total_seconds() / 3600.0)
        return float(1.0 / (1.0 + math.log1p(age_hours)))

    def _extract_entities(self, article: Dict, prediction_rows: Optional[List[Dict]] = None) -> Dict[str, List[str]]:
        text = self._build_text_blob(article).lower()
        entities = {"symbols": [], "sectors": [], "assets": []}
        for row in prediction_rows or []:
            base = str(row.get("symbol", "")).upper().replace(".NS", "").replace(".BO", "")
            if base and base.lower() in text:
                entities["symbols"].append(base)
            sector = str(row.get("sector") or "").upper().strip()
            if sector and sector.lower() in text:
                entities["sectors"].append(sector)
        for sector, tokens in self._get_sector_profiles().items():
            if any(token in text for token in tokens):
                entities["sectors"].append(sector)
        entities["assets"] = [
            token for token in ["USDINR", "DOLLAR", "CRUDE", "GOLD", "BITCOIN", "NASDAQ", "S&P", "NIFTY", "SENSEX", "BOND", "YIELD"]
            if token.lower() in text
        ]
        return {key: sorted(set(values)) for key, values in entities.items()}

    def _classify_event(self, article: Dict) -> str:
        text = self._build_text_blob(article).lower()
        scores = {
            label: sum(text.count(token) for token in tokens)
            for label, tokens in self._get_event_profiles().items()
        }
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        return ranked[0][0] if ranked and ranked[0][1] > 0 else "GENERAL"

    def _classify_narrative(self, article: Dict, event_type: str, entities: Dict[str, List[str]]) -> str:
        text = self._build_text_blob(article).lower()
        profile_scores = {
            label: sum(text.count(token) for token in tokens)
            for label, tokens in self._get_narrative_profiles().items()
        }
        ranked = sorted(profile_scores.items(), key=lambda item: item[1], reverse=True)
        if ranked and ranked[0][1] > 0:
            return ranked[0][0]
        if entities.get("sectors"):
            return f"{entities['sectors'][0]}_FLOW"
        return event_type

    def _compute_article_impact(self, article: Dict, market_context: Dict) -> float:
        market_context = market_context if isinstance(market_context, dict) else {}
        sentiment_strength = abs(float(article.get("sentiment_score", 0.0)))
        relevance = float(article.get("relevance", 0.0))
        freshness = self._article_freshness(article)
        macro_pressure = abs(float((market_context or {}).get("macro_pressure", 0.0)))
        index_moves = [
            abs(float(item.get("change_percent", 0.0)))
            for item in (market_context or {}).get("live_indices", [])
            if isinstance(item, dict)
        ]
        cross_asset_stress = float(np.mean(index_moves)) if index_moves else 0.0
        raw = np.mean([
            sentiment_strength,
            relevance,
            freshness,
            macro_pressure / 100.0 if macro_pressure else 0.0,
            cross_asset_stress / 100.0 if cross_asset_stress else 0.0,
        ])
        return round(float(np.clip(raw, 0.0, 1.0)), 3)

    def _compute_duration_decay(self, article: Dict, event_type: str) -> float:
        freshness = self._article_freshness(article)
        profiles = self._get_event_profiles()
        token_lengths = [len(tokens) for key, tokens in profiles.items() if key == event_type]
        persistence_bias = float(np.mean(token_lengths)) if token_lengths else 1.0
        return round(float(np.clip((freshness * 0.65) + (min(persistence_bias, 10.0) / 10.0 * 0.35), 0.0, 1.0)), 3)

    def _derive_affected_sectors(self, entities: Dict[str, List[str]], narrative: str, prediction_rows: Optional[List[Dict]] = None) -> List[str]:
        sectors = set(entities.get("sectors", []))
        if prediction_rows:
            narrative_upper = str(narrative or "").upper()
            for row in prediction_rows:
                sector = str(row.get("sector") or "").upper().strip()
                symbol = str(row.get("symbol") or "").upper().replace(".NS", "").replace(".BO", "")
                if not sector:
                    continue
                if sector in narrative_upper or (symbol and symbol in narrative_upper):
                    sectors.add(sector)
        return sorted(sectors)

    def _enrich_article(self, article: Dict, prediction_rows: Optional[List[Dict]] = None, market_context: Optional[Dict] = None) -> Dict:
        enriched = dict(article)
        entities = self._extract_entities(article, prediction_rows=prediction_rows)
        event_type = self._classify_event(article)
        narrative = self._classify_narrative(article, event_type=event_type, entities=entities)
        impact_score = self._compute_article_impact(article, market_context or {})
        affected_sectors = self._derive_affected_sectors(entities, narrative, prediction_rows=prediction_rows)
        duration_decay = self._compute_duration_decay(article, event_type)
        enriched.update({
            "entities": entities,
            "event_type": event_type,
            "narrative": narrative,
            "impact_score": impact_score,
            "impact_strength": impact_score,
            "affected_sectors": affected_sectors,
            "duration_decay": duration_decay,
            "confidence_band": impact_score,
            "freshness": self._article_freshness(article),
        })
        return enriched

    def _build_narratives(self, articles: List[Dict]) -> List[Dict]:
        grouped: Dict[str, List[Dict]] = defaultdict(list)
        for article in articles:
            grouped[str(article.get("narrative", "GENERAL"))].append(article)

        items: List[Dict[str, Any]] = []
        for narrative_id, rows in grouped.items():
            scores = [float(row.get("impact_score", 0.0)) for row in rows]
            sentiments = [float(row.get("sentiment_score", 0.0)) for row in rows]
            spread = len({
                sector
                for row in rows
                for sector in row.get("entities", {}).get("sectors", [])
            })
            freshness = [float(row.get("freshness", 0.0)) for row in rows]
            items.append({
                "id": narrative_id,
                "label": narrative_id.replace("_", " ").title(),
                "coverage": len(rows),
                "spread": spread,
                "sentiment": round(float(np.mean(sentiments)) if sentiments else 0.0, 3),
                "score": round(float(np.mean(scores + freshness)) if (scores or freshness) else 0.0, 3),
                "articles": rows[:6],
            })

        if not items:
            return []

        ranking = sorted(items, key=lambda item: (item["score"], item["coverage"], item["spread"]), reverse=True)
        count = max(1, len(ranking))
        momentum_scores = []
        for index, item in enumerate(ranking, start=1):
            momentum_scores.append(round(float(1.0 - ((index - 1) / count) * 0.65 + min(0.35, item["spread"] * 0.08)), 3))
        q75 = float(np.percentile(momentum_scores, 75)) if momentum_scores else 0.0
        q50 = float(np.percentile(momentum_scores, 50)) if momentum_scores else 0.0
        q25 = float(np.percentile(momentum_scores, 25)) if momentum_scores else 0.0
        for index, item in enumerate(ranking, start=1):
            momentum_score = momentum_scores[index - 1]
            if momentum_score >= q75:
                momentum = "ACCELERATING"
            elif momentum_score >= q50:
                momentum = "EMERGING"
            elif momentum_score >= q25:
                momentum = "STABLE"
            else:
                momentum = "FADING"
            item["momentum"] = momentum
            self.narrative_history[item["id"]].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "score": item["score"],
                "coverage": item["coverage"],
                "momentum": momentum,
            })
            self.narrative_history[item["id"]] = self.narrative_history[item["id"]][-50:]
        return ranking[:8]

    def _build_shock_propagation(self, narratives: List[Dict], market_context: Dict) -> List[Dict]:
        propagation = []
        narrative_scores = [float(item.get("score", 0.0)) for item in narratives]
        fast_cutoff = float(np.percentile(narrative_scores, 60)) if narrative_scores else 0.0
        for narrative in narratives[:5]:
            label = str(narrative.get("id", ""))
            if "ENERGY" in label or "OIL" in label:
                path = ["Commodities", "Inflation", "Rates", "Energy Equities"]
            elif "BANK" in label or "RATE" in label:
                path = ["Financials", "Bond Yields", "Currencies", "Growth Equities"]
            elif "AI" in label or "TECH" in label:
                path = ["IT", "Semiconductors", "Global Growth", "Risk Appetite"]
            elif "GEOPOLITICAL" in label or "DEFENCE" in label:
                path = ["Commodities", "Currencies", "Defensives", "Global Indices"]
            else:
                path = ["Sectors", "Indices", "Cross-Asset Risk"]
            propagation.append({
                "narrative": narrative.get("label"),
                "path": path,
                "lag_bias": "FAST" if float(narrative.get("score", 0)) >= fast_cutoff else "DEVELOPING",
                "strength": narrative.get("score", 0),
            })
        return propagation

    def _derive_market_intelligence(self, sentiment: Dict, narratives: List[Dict], market_context: Dict, prediction_rows: List[Dict]) -> Dict:
        market_status = dict((market_context or {}).get("market_status") or {})
        avg_pred_return = float(np.mean([float(row.get("predicted_return", 0.0)) for row in prediction_rows])) if prediction_rows else 0.0
        avg_conf = float(np.mean([float(row.get("confidence", 0.0)) for row in prediction_rows])) if prediction_rows else 0.0
        avg_reliability = float(np.mean([float(row.get("reliability_score", 0.0)) for row in prediction_rows if row.get("reliability_score") is not None])) if prediction_rows else 0.0
        regime_votes = [str(row.get("market_regime") or row.get("regime") or "").upper() for row in prediction_rows if row.get("market_regime") or row.get("regime")]
        regime = max(set(regime_votes), key=regime_votes.count) if regime_votes else str((market_context or {}).get("regime") or "UNKNOWN")
        sentiment_label = sentiment.get("label", "NEUTRAL")
        market_open = str(market_status.get("status", "UNKNOWN")).upper() == "OPEN"
        macro_pressure = float((market_context or {}).get("macro_pressure", 0.0) or 0.0)
        live_indices = [item for item in (market_context or {}).get("live_indices", []) if isinstance(item, dict)]
        index_move = float(np.mean([abs(float(item.get("change_percent", 0.0) or 0.0)) for item in live_indices])) if live_indices else 0.0
        article_impacts = np.array([float(item.get("impact_score", 0.0)) for item in narratives], dtype=float)
        impact_strength = float(np.mean(article_impacts)) if len(article_impacts) else 0.0
        direction_score = np.mean([
            avg_pred_return / 100.0 if avg_pred_return else 0.0,
            float(sentiment.get("overall_score", 0.0)) / 100.0,
            float(narratives[0]["sentiment"]) if narratives else 0.0,
        ])
        if direction_score > 0:
            bias = "Bullish Bias"
        elif direction_score < 0:
            bias = "Bearish Bias"
        else:
            bias = "Balanced Bias"
        mpi_components = np.array([
            np.clip(avg_pred_return / 100.0, -1.0, 1.0),
            np.clip(float(sentiment.get("overall_score", 0.0)) / 100.0, -1.0, 1.0),
            np.clip(float(narratives[0]["sentiment"]) if narratives else 0.0, -1.0, 1.0),
            np.clip(-macro_pressure, -1.0, 1.0),
            np.clip(-index_move / 5.0, -1.0, 1.0),
            np.clip((avg_reliability / 100.0) - 0.5, -1.0, 1.0),
        ], dtype=float)
        mpi = round(float(np.clip(np.mean(mpi_components), -1.0, 1.0)), 4)
        next_open_bias = "Bullish" if mpi > 0 else "Bearish" if mpi < 0 else "Balanced"
        expected_close_direction = "Up" if direction_score > 0 else "Down" if direction_score < 0 else "Flat"
        return {
            "market_status": market_status.get("status", "UNKNOWN"),
            "next_market_event": {
                "label": "Expected Close" if market_open else "Next Open",
                "timing": market_status.get("next_close") or market_status.get("next_open") or market_status.get("next_session"),
                "bias": bias,
            },
            "global_sentiment": sentiment_label,
            "market_regime": regime or "UNKNOWN",
            "avg_prediction_confidence": round(avg_conf, 2),
            "avg_prediction_reliability": round(avg_reliability, 2),
            "narrative_focus": narratives[0]["label"] if narratives else "No dominant narrative",
            "macro_bias": bias,
            "market_pressure_index": mpi,
            "market_pressure_bias": next_open_bias,
            "expected_close_direction": expected_close_direction,
            "next_open_bias": next_open_bias,
            "impact_strength": round(impact_strength, 3),
        }

    def _build_prediction_context(self, articles: List[Dict], prediction_rows: List[Dict]) -> List[Dict]:
        context_rows = []
        for row in prediction_rows[:20]:
            symbol = str(row.get("symbol", "")).upper().replace(".NS", "").replace(".BO", "")
            sector = str(row.get("sector") or "").upper()
            related = [
                article for article in articles
                if symbol in article.get("entities", {}).get("symbols", [])
                or (sector and sector in article.get("entities", {}).get("sectors", []))
            ]
            if not related:
                continue
            ranked = sorted(related, key=lambda item: (item.get("impact_score", 0), item.get("freshness", 0)), reverse=True)
            context_rows.append({
                "symbol": symbol,
                "headline": ranked[0].get("title"),
                "top_driver": ranked[0].get("title"),
                "narrative": ranked[0].get("narrative"),
                "narratives": sorted(set(article.get("narrative") for article in ranked[:3])),
                "event_type": ranked[0].get("event_type"),
                "affected_sectors": sorted({sector for article in ranked[:3] for sector in article.get("affected_sectors", [])}),
                "impact_score": round(float(np.mean([article.get("impact_score", 0.0) for article in ranked[:3]])), 3),
                "impact_shift": round(float(np.mean([article.get("impact_score", 0.0) for article in ranked[:3]])), 3),
                "duration_decay": round(float(np.mean([article.get("duration_decay", 0.0) for article in ranked[:3]])), 3),
                "timing": ranked[0].get("freshness", 0.0),
            })
        return context_rows

    def _build_portfolio_alerts(self, articles: List[Dict], portfolio_symbols: List[str]) -> List[Dict]:
        if not portfolio_symbols:
            return []
        tracked = set(str(symbol).upper() for symbol in portfolio_symbols if symbol)
        alerts = []
        for article in articles:
            matches = tracked.intersection(set(article.get("entities", {}).get("symbols", [])))
            if not matches:
                continue
            alerts.append({
                "symbols": sorted(matches),
                "headline": article.get("title"),
                "event_type": article.get("event_type"),
                "impact_score": article.get("impact_score", 0.0),
                "narrative": article.get("narrative"),
                "sentiment": article.get("sentiment"),
            })
        return alerts[:10]

    def _compute_information_advantage(self, articles: List[Dict], narratives: List[Dict], market_context: Dict) -> Dict:
        article_scores = np.array([float(article.get("impact_score", 0.0)) for article in articles], dtype=float)
        freshness_scores = np.array([float(article.get("freshness", 0.0)) for article in articles], dtype=float)
        narrative_scores = np.array([float(narrative.get("score", 0.0)) for narrative in narratives], dtype=float)
        combined = np.concatenate([arr for arr in [article_scores, freshness_scores, narrative_scores] if len(arr)])
        base = float(np.mean(combined)) if len(combined) else 0.0
        market_reaction = [
            abs(float(item.get("change_percent", 0.0)))
            for item in (market_context or {}).get("live_indices", [])
            if isinstance(item, dict)
        ]
        reaction_scale = float(np.mean(market_reaction)) / 100.0 if market_reaction else 0.0
        lead_score = round(float(np.clip(base * (1.0 - min(0.9, reaction_scale)), 0.0, 1.0)), 3)
        label_cutoffs = np.percentile([lead_score, base, 1.0 - reaction_scale], [33, 66]) if np.isfinite(lead_score) else [0.33, 0.66]
        return {
            "score": lead_score,
            "label": "EARLY" if lead_score >= label_cutoffs[1] else "ACTIVE" if lead_score >= label_cutoffs[0] else "LATE",
            "headline_count": len(articles),
            "narrative_strength": round(float(np.mean(narrative_scores)) if len(narrative_scores) else 0.0, 3),
        }

    def get_market_intelligence_bundle(
        self,
        prediction_rows: Optional[List[Dict]] = None,
        portfolio_symbols: Optional[List[str]] = None,
        market_context: Optional[Dict] = None,
        force_refresh: bool = False,
    ) -> Dict:
        bundle = self.get_aggregated_news(force_refresh=force_refresh)
        prediction_rows = list(prediction_rows or [])
        portfolio_symbols = [str(symbol).upper() for symbol in (portfolio_symbols or []) if symbol]
        market_context = market_context or {}
        articles = [
            self._enrich_article(article, prediction_rows=prediction_rows, market_context=market_context)
            for article in list(bundle.get("articles", []))
        ]
        articles = sorted(
            articles,
            key=lambda item: (
                float(item.get("impact_score", 0.0)),
                float(item.get("freshness", 0.0)),
                float(item.get("relevance", 0.0)),
            ),
            reverse=True,
        )
        sectorwise = defaultdict(list)
        for article in articles:
            sectorwise[article.get("sector", "GENERAL")].append(article)
        for sector, rows in list(sectorwise.items()):
            sectorwise[sector] = sorted(
                rows,
                key=lambda item: (
                    float(item.get("impact_score", 0.0)),
                    float(item.get("freshness", 0.0)),
                    float(item.get("relevance", 0.0)),
                ),
                reverse=True,
            )
        narratives = self._build_narratives(articles)
        sentiment = self.get_market_sentiment_analysis()
        return {
            "articles": articles,
            "sectorwise": dict(sectorwise),
            "sentiment": sentiment,
            "narratives": narratives,
            "narrative_momentum": [
                {
                    "id": item["id"],
                    "label": item["label"],
                    "momentum": item["momentum"],
                    "score": item["score"],
                    "coverage": item["coverage"],
                    "spread": item["spread"],
                    "sentiment": item["sentiment"],
                }
                for item in narratives
            ],
            "shock_propagation": self._build_shock_propagation(narratives, market_context),
            "market_intelligence": self._derive_market_intelligence(sentiment, narratives, market_context, prediction_rows),
            "portfolio_alerts": self._build_portfolio_alerts(articles, portfolio_symbols),
            "prediction_context": self._build_prediction_context(articles, prediction_rows),
            "information_advantage": self._compute_information_advantage(articles, narratives, market_context),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

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
