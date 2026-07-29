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

