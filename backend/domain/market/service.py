"""Market universe and symbol query services."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
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

