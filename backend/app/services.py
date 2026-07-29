"""Small service objects used by the Phase 2 app factory."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


class SQLitePortfolioRepository:
    """Read/write the portfolio summary table without importing the legacy app."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    def _connect(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS portfolio (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL UNIQUE,
                    quantity REAL NOT NULL,
                    avg_price REAL NOT NULL,
                    added_date TEXT NOT NULL
                )
                """
            )

    def get_portfolio(self) -> list[dict[str, Any]]:
        self.ensure_schema()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, symbol, quantity, avg_price, added_date
                FROM portfolio
                ORDER BY symbol ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def add_to_portfolio(self, symbol: str, quantity: float, avg_price: float, purchase_date: str | None = None) -> None:
        self.ensure_schema()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO portfolio (symbol, quantity, avg_price, added_date)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    quantity = excluded.quantity,
                    avg_price = excluded.avg_price,
                    added_date = excluded.added_date
                """,
                (symbol.upper(), float(quantity), float(avg_price), purchase_date or datetime.now().isoformat()),
            )

    def update_portfolio_position_summary(self, symbol: str, quantity: float, avg_price: float, purchase_date: str | None = None) -> None:
        self.add_to_portfolio(symbol, quantity, avg_price, purchase_date)

    def delete_portfolio_position(self, symbol: str) -> None:
        self.ensure_schema()
        with self._connect() as conn:
            conn.execute("DELETE FROM portfolio WHERE symbol = ?", (symbol.upper(),))

    def get_portfolio_lots(self, symbol: str | None = None, only_open: bool = True) -> list[dict[str, Any]]:
        rows = self.get_portfolio()
        if symbol:
            rows = [row for row in rows if str(row.get("symbol", "")).upper() == symbol.upper()]
        return [
            {
                "id": row.get("id"),
                "lot_id": row.get("id"),
                "symbol": row.get("symbol"),
                "buy_date": row.get("added_date"),
                "buy_price": row.get("avg_price"),
                "original_quantity": row.get("quantity"),
                "remaining_quantity": row.get("quantity"),
            }
            for row in rows
        ]

    def get_realized_gains(self, symbol: str | None = None, from_date: str | None = None, to_date: str | None = None) -> list[dict[str, Any]]:
        return []

    def get_financial_year_realized_summary(self, fy_start_year: int | None = None) -> dict[str, Any]:
        return {
            "fy": str(fy_start_year or datetime.now().year),
            "realized_total": 0,
            "stcg_realized": 0,
            "ltcg_realized": 0,
            "transactions": 0,
            "symbols": [],
        }

    def compare_sell_methods(self, symbol: str, quantity: float, sell_price: float, sell_date: str | None = None, fees: float = 0.0, methods: list[str] | None = None) -> dict[str, Any]:
        method_list = methods or ["FIFO", "LIFO", "HIFO"]
        return {
            "symbol": symbol.upper(),
            "sell_quantity": float(quantity or 0),
            "sell_price": float(sell_price or 0),
            "scenarios": [
                {
                    "symbol": symbol.upper(),
                    "method": method,
                    "sold_quantity": float(quantity or 0),
                    "sell_price": float(sell_price or 0),
                    "fees": float(fees or 0),
                    "realized_gain": 0,
                    "matched_lots": [],
                }
                for method in method_list
            ],
            "recommended_method": method_list[0] if method_list else "FIFO",
        }


@dataclass
class MarketUniverse:
    symbols: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.symbols:
            self.symbols.update(
                {
                    "INFY": {"symbol": "INFY", "name": "Infosys", "exchange_symbols": ["INFY.NS"]},
                    "TCS": {"symbol": "TCS", "name": "Tata Consultancy Services", "exchange_symbols": ["TCS.NS"]},
                    "SBIN": {"symbol": "SBIN", "name": "State Bank of India", "exchange_symbols": ["SBIN.NS"]},
                    "RELIANCE": {"symbol": "RELIANCE", "name": "Reliance Industries", "exchange_symbols": ["RELIANCE.NS"]},
                }
            )

    def search(self, query: str, limit: int = 15) -> list[dict[str, Any]]:
        needle = str(query or "").upper().replace(".NS", "").replace(".BO", "")
        if not needle:
            return []
        rows = [
            {
                "symbol": symbol,
                "display": data.get("exchange_symbols", [f"{symbol}.NS"])[0],
                "name": data.get("name", symbol),
                "exchange": "NSE",
                "price": None,
                "current_price": None,
                "change_percent": None,
                "change_value": None,
            }
            for symbol, data in sorted(self.symbols.items())
            if needle in symbol or needle in str(data.get("name", "")).upper()
        ]
        return rows[: max(1, min(int(limit or 15), 60))]

    def list_stocks(self, limit: int = 20) -> list[dict[str, Any]]:
        return [
            {
                "symbol": symbol,
                "display": data.get("exchange_symbols", [f"{symbol}.NS"])[0],
                "name": data.get("name", symbol),
                "exchange": "NSE",
                "price": None,
                "current_price": None,
                "change_percent": None,
            }
            for symbol, data in list(sorted(self.symbols.items()))[: max(1, min(int(limit or 20), 200))]
        ]


class RuntimeContext:
    def __init__(self, *, portfolio: SQLitePortfolioRepository, logger: logging.Logger):
        self.db = portfolio
        self.portfolio = portfolio
        self.logger = logger
        self.prediction_history: list[dict[str, Any]] = []
        self.models: dict[str, Any] = {}
        self.cache: dict[str, Any] = {}
        self.cache_ttl = 60

    def compute_portfolio_intelligence(self, holdings: list[dict[str, Any]], preds: dict[str, Any] | None = None) -> dict[str, Any]:
        positions = []
        total_value = 0.0
        for row in holdings:
            quantity = float(row.get("quantity") or 0)
            avg_price = float(row.get("avg_price") or 0)
            value = quantity * avg_price
            total_value += value
            positions.append(
                {
                    "symbol": row.get("symbol"),
                    "quantity": quantity,
                    "avg_price": avg_price,
                    "current_price": avg_price or None,
                    "market_value": round(value, 2),
                }
            )
        return {"positions": positions, "account_metrics": {"total_value": round(total_value, 2)}}


@dataclass
class AppServices:
    settings: Any
    portfolio: SQLitePortfolioRepository
    market: MarketUniverse
    runtime: RuntimeContext
    logger: logging.Logger
    ai_engine_state: dict[str, Any] = field(default_factory=lambda: {"predictions": {}, "last_update": None, "cognitive_state": {}})
    state_cache: dict[str, Any] = field(default_factory=dict)
    system_cache: dict[str, Any] = field(default_factory=dict)
