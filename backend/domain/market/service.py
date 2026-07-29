"""Market universe and symbol query services."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def normalize_symbol(value: Any) -> str | None:
    if value is None:
        return None
    symbol = str(value).strip().upper().replace(".NS", "").replace(".BO", "")
    symbol = re.sub(r"[^A-Z0-9&.-]", "", symbol)
    return symbol or None


@dataclass
class MarketUniverse:
    symbols: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.symbols:
            return
        self.symbols.update(
            {
                "INFY": {"symbol": "INFY", "name": "Infosys", "exchange_symbols": ["INFY.NS"]},
                "TCS": {"symbol": "TCS", "name": "Tata Consultancy Services", "exchange_symbols": ["TCS.NS"]},
                "SBIN": {"symbol": "SBIN", "name": "State Bank of India", "exchange_symbols": ["SBIN.NS"]},
                "RELIANCE": {"symbol": "RELIANCE", "name": "Reliance Industries", "exchange_symbols": ["RELIANCE.NS"]},
            }
        )


class MarketService:
    def __init__(self, universe: MarketUniverse):
        self.universe = universe

    @property
    def symbols(self) -> dict[str, dict[str, Any]]:
        return self.universe.symbols

    def _stock_row(self, symbol: str, data: dict[str, Any]) -> dict[str, Any]:
        display = data.get("exchange_symbols", [f"{symbol}.NS"])[0]
        return {
            "symbol": symbol,
            "display": display,
            "name": data.get("name", symbol),
            "exchange": "NSE" if str(display).upper().endswith(".NS") else "BSE",
            "price": None,
            "current_price": None,
            "change_percent": None,
            "change_value": None,
            "data_quality": "unavailable",
        }

    def search(self, query: str, limit: int = 15) -> list[dict[str, Any]]:
        needle = normalize_symbol(query)
        if not needle:
            return []
        rows = [
            self._stock_row(symbol, data)
            for symbol, data in sorted(self.universe.symbols.items())
            if needle in symbol or needle in str(data.get("name", "")).upper()
        ]
        return rows[: max(1, min(int(limit or 15), 60))]

    def list_stocks(self, limit: int = 20) -> list[dict[str, Any]]:
        return [
            self._stock_row(symbol, data)
            for symbol, data in list(sorted(self.universe.symbols.items()))[: max(1, min(int(limit or 20), 200))]
        ]

    def get_stock(self, symbol: str) -> dict[str, Any] | None:
        base_symbol = normalize_symbol(symbol)
        if not base_symbol:
            return None
        data = self.universe.symbols.get(base_symbol)
        if not data:
            return None
        return self._stock_row(base_symbol, data)

    def universe_payload(self) -> dict[str, Any]:
        rows = self.list_stocks(limit=len(self.universe.symbols) or 1)
        return {
            "success": True,
            "symbols": [row["symbol"] for row in rows],
            "stocks": rows,
            "count": len(rows),
            "data_quality": "unavailable",
        }

    def save_user_tickers_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        tickers = payload.get("tickers") if isinstance(payload, dict) else []
        cleaned = [symbol for symbol in (normalize_symbol(item) for item in tickers or []) if symbol]
        return {
            "success": True,
            "tickers": cleaned,
            "message": "Ticker persistence is deferred in the app-factory runtime.",
            "data_quality": "unavailable",
        }

    def stock_history_payload(self, symbol: str) -> dict[str, Any]:
        base_symbol = normalize_symbol(symbol) or str(symbol).upper()
        return {
            "success": True,
            "symbol": base_symbol,
            "data": [],
            "prices": [],
            "labels": [],
            "datasets": [],
            "data_quality": "unavailable",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def stock_analysis_payload(self, symbol: str) -> dict[str, Any]:
        stock = self.get_stock(symbol)
        base_symbol = normalize_symbol(symbol) or str(symbol).upper()
        return {
            "success": stock is not None,
            "symbol": base_symbol,
            "stock": stock,
            "analysis": {},
            "indicators": {},
            "signal": None,
            "confidence": None,
            "data_quality": "unavailable",
        }

    def compare_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        raw_symbols = payload.get("symbols") if isinstance(payload, dict) else []
        symbols = [symbol for symbol in (normalize_symbol(item) for item in raw_symbols or []) if symbol]
        return {
            "success": True,
            "symbols": symbols,
            "results": [self.get_stock(symbol) for symbol in symbols if self.get_stock(symbol) is not None],
            "data_quality": "unavailable",
        }

    def autocomplete_payload(self, query: str, limit: int = 10) -> dict[str, Any]:
        results = self.search(query, limit=limit)
        return {"success": True, "suggestions": results, "results": results, "data_quality": "unavailable"}

    def market_trends_payload(self) -> dict[str, Any]:
        return {
            "success": True,
            "labels": [],
            "datasets": [],
            "data": [],
            "data_quality": "unavailable",
        }

    def sector_analytics_payload(self) -> dict[str, Any]:
        return {
            "success": True,
            "labels": [],
            "values": [],
            "sectoranalysis": {},
            "sector_analysis": {},
            "data_quality": "unavailable",
        }

    def risk_return_payload(self) -> dict[str, Any]:
        return {
            "success": True,
            "points": [],
            "datasets": [],
            "data_quality": "unavailable",
        }
