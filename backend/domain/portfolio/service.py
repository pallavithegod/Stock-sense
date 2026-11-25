"""Portfolio persistence and read-model services."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from backend.db import apply_migrations, connect
from backend.domain.market import MarketService, normalize_symbol
from backend.services.supabase_auth import AuthenticatedUser


class PortfolioRepository(Protocol):
    provider_name: str

    @property
    def db_path(self) -> Path: ...

    def ensure_schema(self) -> None: ...

    def get_portfolio(self, principal: AuthenticatedUser | None = None) -> list[dict[str, Any]]: ...

    def add_to_portfolio(
        self,
        symbol: str,
        quantity: float,
        avg_price: float,
        purchase_date: str | None = None,
        principal: AuthenticatedUser | None = None,
    ) -> None: ...

    def update_portfolio_position_summary(
        self,
        symbol: str,
        quantity: float,
        avg_price: float,
        purchase_date: str | None = None,
        principal: AuthenticatedUser | None = None,
    ) -> None: ...

    def delete_portfolio_position(
        self,
        symbol: str,
        principal: AuthenticatedUser | None = None,
    ) -> None: ...

    def get_portfolio_lots(
        self,
        symbol: str | None = None,
        only_open: bool = True,
        principal: AuthenticatedUser | None = None,
    ) -> list[dict[str, Any]]: ...

    def get_realized_gains(
        self,
        symbol: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        principal: AuthenticatedUser | None = None,
    ) -> list[dict[str, Any]]: ...

    def get_financial_year_realized_summary(
        self,
        fy_start_year: int | None = None,
        principal: AuthenticatedUser | None = None,
    ) -> dict[str, Any]: ...

    def compare_sell_methods(
        self,
        symbol: str,
        quantity: float,
        sell_price: float,
        sell_date: str | None = None,
        fees: float = 0.0,
        methods: list[str] | None = None,
        principal: AuthenticatedUser | None = None,
    ) -> dict[str, Any]: ...


class SQLitePortfolioRepository:
    """Read/write the local portfolio summary table."""

    provider_name = "local_sqlite_portfolio"

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    def _connect(self):
        return connect(self.db_path)

    def ensure_schema(self) -> None:
        apply_migrations(self.db_path, backup=self.db_path.exists(), backup_dir=self.db_path.parent / "backups")

    def get_portfolio(self, principal: AuthenticatedUser | None = None) -> list[dict[str, Any]]:
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

    def add_to_portfolio(
        self,
        symbol: str,
        quantity: float,
        avg_price: float,
        purchase_date: str | None = None,
        principal: AuthenticatedUser | None = None,
    ) -> None:
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
                (symbol.upper(), float(quantity), float(avg_price), purchase_date or datetime.now(timezone.utc).isoformat()),
            )

    def update_portfolio_position_summary(
        self,
        symbol: str,
        quantity: float,
        avg_price: float,
        purchase_date: str | None = None,
        principal: AuthenticatedUser | None = None,
    ) -> None:
        self.add_to_portfolio(symbol, quantity, avg_price, purchase_date, principal)

    def delete_portfolio_position(self, symbol: str, principal: AuthenticatedUser | None = None) -> None:
        self.ensure_schema()
        with self._connect() as conn:
            conn.execute("DELETE FROM portfolio WHERE symbol = ?", (symbol.upper(),))

    def get_portfolio_lots(
        self,
        symbol: str | None = None,
        only_open: bool = True,
        principal: AuthenticatedUser | None = None,
    ) -> list[dict[str, Any]]:
        rows = self.get_portfolio(principal)
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

    def get_realized_gains(
        self,
        symbol: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        principal: AuthenticatedUser | None = None,
    ) -> list[dict[str, Any]]:
        return []

    def get_financial_year_realized_summary(
        self,
        fy_start_year: int | None = None,
        principal: AuthenticatedUser | None = None,
    ) -> dict[str, Any]:
        return {
            "fy": str(fy_start_year or datetime.now().year),
            "realized_total": 0,
            "stcg_realized": 0,
            "ltcg_realized": 0,
            "transactions": 0,
            "symbols": [],
        }

    def compare_sell_methods(
        self,
        symbol: str,
        quantity: float,
        sell_price: float,
        sell_date: str | None = None,
        fees: float = 0.0,
        methods: list[str] | None = None,
        principal: AuthenticatedUser | None = None,
    ) -> dict[str, Any]:
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


class PortfolioService:
    def __init__(self, *, repository: PortfolioRepository, market_service: MarketService):
        self.repository = repository
        self.market_service = market_service

    @property
    def db_path(self) -> Path:
        return self.repository.db_path

    def ensure_schema(self) -> None:
        self.repository.ensure_schema()

    def list_positions(self, principal: AuthenticatedUser | None = None) -> list[dict[str, Any]]:
        return self.repository.get_portfolio(principal)

    def build_state(self, principal: AuthenticatedUser | None = None) -> dict[str, Any]:
        intelligence = self.compute_intelligence(self.list_positions(principal))
        return {"success": True, **intelligence}

    def create_position(
        self,
        data: dict[str, Any],
        principal: AuthenticatedUser | None = None,
    ) -> dict[str, Any]:
        symbol = data["symbol"]
        self.repository.add_to_portfolio(
            symbol,
            data["quantity"],
            data["avg_price"],
            data["purchase_date"],
            principal,
        )
        return {"status": "ok", "exchange_symbol": f"{symbol}.NS"}

    def update_position(
        self,
        symbol: str,
        data: dict[str, Any],
        principal: AuthenticatedUser | None = None,
    ) -> dict[str, Any]:
        self.repository.update_portfolio_position_summary(
            data["symbol"],
            data["quantity"],
            data["avg_price"],
            data["purchase_date"],
            principal,
        )
        return {"status": "ok", "message": f"{data['symbol']} updated"}

    def delete_position(
        self,
        symbol: str,
        principal: AuthenticatedUser | None = None,
    ) -> dict[str, Any]:
        base_symbol = normalize_symbol(symbol)
        if not base_symbol:
            return {"status": "error", "error": "invalid symbol"}
        self.repository.delete_portfolio_position(base_symbol, principal)
        return {"status": "deleted"}

    def lots(self, symbol: str | None = None, principal: AuthenticatedUser | None = None) -> dict[str, Any]:
        rows = self.repository.get_portfolio_lots(symbol=symbol, principal=principal)
        return {"status": "ok", "data": rows, "count": len(rows), "total": len(rows)}

    def realized_gains(self, symbol: str | None = None, principal: AuthenticatedUser | None = None) -> dict[str, Any]:
        rows = self.repository.get_realized_gains(symbol=symbol, principal=principal)
        return {"status": "ok", "data": rows, "count": len(rows), "total": len(rows)}

    def tax_summary(self, principal: AuthenticatedUser | None = None) -> dict[str, Any]:
        return {"status": "ok", "data": self.repository.get_financial_year_realized_summary(principal=principal)}

    def lot_insights(self, symbol: str | None = None, principal: AuthenticatedUser | None = None) -> dict[str, Any]:
        return {
            "status": "ok",
            "data": {
                "symbol": symbol,
                "open_lots": self.repository.get_portfolio_lots(symbol=symbol, principal=principal),
                "all_lots": self.repository.get_portfolio_lots(symbol=symbol, principal=principal),
                "near_ltcg": [],
                "fy_summary": self.repository.get_financial_year_realized_summary(principal=principal),
            },
        }

    def intelligence_suite(self, principal: AuthenticatedUser | None = None) -> dict[str, Any]:
        intelligence = self._intelligence_layers(principal)
        return {"status": "ok", "data": intelligence}

    def forecast(self, principal: AuthenticatedUser | None = None) -> dict[str, Any]:
        return {"status": "ok", "data": self._intelligence_layers(principal)["forecast"]}

    def survival(self, principal: AuthenticatedUser | None = None) -> dict[str, Any]:
        return {"status": "ok", "data": self._intelligence_layers(principal)["survival"]}

    def backtesting(self, principal: AuthenticatedUser | None = None) -> dict[str, Any]:
        return {"status": "ok", "data": self._intelligence_layers(principal)["backtesting"]}

    def drift(self, principal: AuthenticatedUser | None = None) -> dict[str, Any]:
        return {"status": "ok", "data": self._intelligence_layers(principal)["drift"]}

    def governance(self, principal: AuthenticatedUser | None = None) -> dict[str, Any]:
        return {"status": "ok", "data": self._intelligence_layers(principal)["governance"]}

    def explainability(self, principal: AuthenticatedUser | None = None) -> dict[str, Any]:
        return {"status": "ok", "data": self._intelligence_layers(principal)["explainability"]}

    def scorecard(self, principal: AuthenticatedUser | None = None) -> dict[str, Any]:
        return {"status": "ok", "data": self._intelligence_layers(principal)["scorecard"]}

    def allocation_chart(self, principal: AuthenticatedUser | None = None) -> dict[str, Any]:
        positions = self.compute_intelligence(self.list_positions(principal))["positions"]
        return {
            "status": "ok",
            "data": {
                "labels": [str(position.get("symbol")) for position in positions],
                "values": [position.get("market_value", 0) for position in positions],
                "data_quality": "portfolio_only",
            },
        }

    def simulate_sell(
        self,
        data: dict[str, Any],
        principal: AuthenticatedUser | None = None,
    ) -> dict[str, Any]:
        result = self.repository.compare_sell_methods(
            data["symbol"],
            data["quantity"],
            data["sell_price"],
            sell_date=data["sell_date"],
            fees=data["fees"],
            methods=data["methods"],
            principal=principal,
        )
        return {"status": "ok", "data": result}

    def compute_intelligence(self, holdings: list[dict[str, Any]]) -> dict[str, Any]:
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
                    "source_type": "presentation_intelligence",
                    "provider": self.repository.provider_name,
                    "data_quality": "portfolio_only",
                    "model_version": None,
                    "is_synthetic": False,
                    "is_demo": False,
                }
            )
        return {
            "positions": positions,
            "account_metrics": {"total_value": round(total_value, 2)},
            "data_quality": "portfolio_only",
            "source_type": "presentation_intelligence",
            "provider": self.repository.provider_name,
            "model_version": None,
            "is_synthetic": False,
            "is_demo": False,
        }

    def _intelligence_layers(self, principal: AuthenticatedUser | None = None) -> dict[str, Any]:
        intelligence = self.compute_intelligence(self.list_positions(principal))
        total_value = float(intelligence["account_metrics"].get("total_value") or 0)
        position_count = len(intelligence["positions"])
        generated_at = datetime.now().isoformat()
        return {
            "generated_at": generated_at,
            "data_quality": "portfolio_only",
            **intelligence,
            "forecast": {
                "status": "unavailable_without_market_provider",
                "expected_value": None,
                "portfolio_value": total_value,
                "data_quality": "portfolio_only",
            },
            "survival": {
                "score": None,
                "status": "unavailable_without_risk_model",
                "positions_analyzed": position_count,
                "data_quality": "portfolio_only",
            },
            "backtesting": {
                "status": "unavailable_without_historical_provider",
                "trades": 0,
                "data_quality": "unavailable",
            },
            "drift": {
                "status": "unavailable_without_benchmark",
                "alerts": [],
                "data_quality": "portfolio_only",
            },
            "governance": {
                "status": "WATCH" if position_count else "EMPTY",
                "alerts": [],
                "data_quality": "portfolio_only",
            },
            "explainability": {
                "summary": "Portfolio intelligence is based only on saved holdings in the app-factory runtime.",
                "drivers": [],
                "data_quality": "portfolio_only",
            },
            "scorecard": {
                "score": None,
                "basis": "unavailable_without_matured_outcomes",
                "data_quality": "portfolio_only",
            },
        }
