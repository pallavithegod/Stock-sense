"""Market universe and symbol query services."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from backend.services.market_data import ProviderResponse, ResilientMarketDataClient, normalize_symbol


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
    def __init__(self, universe: MarketUniverse, *, market_data: ResilientMarketDataClient | None = None):
        self.universe = universe
        self.market_data = market_data

    @property
    def symbols(self) -> dict[str, dict[str, Any]]:
        return self.universe.symbols

    def _stock_row(self, symbol: str, data: dict[str, Any], quote: ProviderResponse | None = None) -> dict[str, Any]:
        display = data.get("exchange_symbols", [f"{symbol}.NS"])[0]
        quote_data = quote.data if quote and isinstance(quote.data, dict) else {}
        price = quote_data.get("price")
        current_price = quote_data.get("current_price")
        row = {
            "symbol": symbol,
            "display": quote_data.get("display") or display,
            "name": data.get("name", symbol),
            "exchange": "NSE" if str(display).upper().endswith(".NS") else "BSE",
            "price": price,
            "current_price": current_price,
            "change_percent": quote_data.get("change_percent"),
            "change_value": quote_data.get("change_value"),
            "data_quality": quote.quality_status if quote else "unavailable",
            "provider": quote.provider if quote else None,
            "fetched_at": quote.fetched_at if quote else None,
            "stale": quote.stale if quote else True,
            "synthetic": quote.synthetic if quote else False,
            "demo": quote.demo if quote else False,
        }
        if quote and quote.state == "unavailable":
            row["provider_error_code"] = quote.error_code
        return row

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

    def dashboard_stocks(self, limit: int = 8) -> list[dict[str, Any]]:
        rows = []
        for symbol, data in list(sorted(self.universe.symbols.items()))[: max(1, min(int(limit or 8), 60))]:
            quote = self.market_data.quote(symbol, allow_stale=True) if self.market_data else None
            rows.append(self._stock_row(symbol, data, quote=quote))
        return rows

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
        response = self.market_data.history(base_symbol, period="1y", interval="1d", allow_stale=True) if self.market_data else None
        prices = response.data.get("prices", []) if response and isinstance(response.data, dict) else []
        return {
            "success": True,
            "symbol": base_symbol,
            "data": prices,
            "prices": prices,
            "labels": [row.get("timestamp") for row in prices],
            "datasets": [{"label": base_symbol, "data": [row.get("close") for row in prices]}] if prices else [],
            "data_quality": response.quality_status if response else "unavailable",
            "provider": response.provider if response else None,
            "fetched_at": response.fetched_at if response else None,
            "stale": response.stale if response else True,
            "synthetic": response.synthetic if response else False,
            "demo": response.demo if response else False,
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
