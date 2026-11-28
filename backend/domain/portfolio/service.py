"""Portfolio persistence and read-model services."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from backend.db import apply_migrations, connect
from backend.domain.portfolio.exceptions import PortfolioFeatureUnavailable
from backend.domain.portfolio.ledger import (
    indian_financial_year_start,
    match_sell,
    normalize_trade_date,
    parse_trade_date,
)
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
        idempotency_key: str | None = None,
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

    def record_sell(
        self,
        symbol: str,
        quantity: float,
        sell_price: float,
        sell_date: str | None = None,
        fees: float = 0.0,
        method: str = "FIFO",
        notes: str | None = None,
        principal: AuthenticatedUser | None = None,
        idempotency_key: str | None = None,
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
        self._seed_opening_lots()

    def _seed_opening_lots(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT p.id, p.symbol, p.quantity, p.avg_price, p.added_date
                FROM portfolio AS p
                WHERE NOT EXISTS (
                    SELECT 1 FROM portfolio_transactions AS tx WHERE tx.symbol = p.symbol
                )
                """
            ).fetchall()
            for row in rows:
                source_key = f"opening-position:{row['id']}"
                conn.execute(
                    """
                    INSERT INTO portfolio_transactions
                        (symbol, side, quantity, price, trade_date, fees, notes, source_key, created_at)
                    VALUES (?, 'BUY', ?, ?, ?, 0, 'Opening balance imported from aggregate position', ?, ?)
                    ON CONFLICT(source_key) DO NOTHING
                    """,
                    (
                        row["symbol"],
                        row["quantity"],
                        row["avg_price"],
                        normalize_trade_date(row["added_date"]),
                        source_key,
                        now,
                    ),
                )
                transaction = conn.execute(
                    "SELECT id, trade_date FROM portfolio_transactions WHERE source_key = ?",
                    (source_key,),
                ).fetchone()
                if transaction is not None:
                    conn.execute(
                        """
                        INSERT INTO portfolio_lots (
                            symbol, buy_txn_id, buy_date, buy_price, original_quantity,
                            remaining_quantity, original_fees, remaining_fees, created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?)
                        ON CONFLICT(buy_txn_id) DO NOTHING
                        """,
                        (
                            row["symbol"],
                            transaction["id"],
                            transaction["trade_date"],
                            row["avg_price"],
                            row["quantity"],
                            row["quantity"],
                            now,
                        ),
                    )

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
        idempotency_key: str | None = None,
    ) -> None:
        self.ensure_schema()
        trade_date = normalize_trade_date(purchase_date)
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            source_key = f"api:{idempotency_key}" if idempotency_key else None
            if source_key:
                previous = conn.execute(
                    "SELECT symbol, side, quantity, price, trade_date FROM portfolio_transactions WHERE source_key = ?",
                    (source_key,),
                ).fetchone()
                if previous is not None:
                    if (
                        previous["side"] != "BUY"
                        or previous["symbol"] != symbol.upper()
                        or float(previous["quantity"]) != float(quantity)
                        or float(previous["price"]) != float(avg_price)
                        or previous["trade_date"] != trade_date
                    ):
                        raise ValueError("Idempotency key was already used for a different trade.")
                    return
            transaction = conn.execute(
                """
                INSERT INTO portfolio_transactions
                    (symbol, side, quantity, price, trade_date, fees, source_key, created_at)
                VALUES (?, 'BUY', ?, ?, ?, 0, ?, ?)
                ON CONFLICT(source_key) DO NOTHING
                RETURNING id
                """,
                (
                    symbol.upper(),
                    float(quantity),
                    float(avg_price),
                    trade_date,
                    source_key,
                    now,
                ),
            ).fetchone()
            if transaction is None:
                previous = conn.execute(
                    "SELECT symbol, side, quantity, price, trade_date FROM portfolio_transactions WHERE source_key = ?",
                    (source_key,),
                ).fetchone()
                if previous is None:
                    raise RuntimeError("The buy transaction could not be confirmed.")
                if (
                    previous["side"] != "BUY"
                    or previous["symbol"] != symbol.upper()
                    or float(previous["quantity"]) != float(quantity)
                    or float(previous["price"]) != float(avg_price)
                    or previous["trade_date"] != trade_date
                ):
                    raise ValueError("Idempotency key was already used for a different trade.")
                return
            conn.execute(
                """
                INSERT INTO portfolio_lots (
                    symbol, buy_txn_id, buy_date, buy_price, original_quantity,
                    remaining_quantity, original_fees, remaining_fees, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?)
                """,
                (symbol.upper(), transaction["id"], trade_date, float(avg_price), float(quantity), float(quantity), now),
            )
            self._refresh_position(conn, symbol)

    def update_portfolio_position_summary(
        self,
        symbol: str,
        quantity: float,
        avg_price: float,
        purchase_date: str | None = None,
        principal: AuthenticatedUser | None = None,
    ) -> None:
        raise PortfolioFeatureUnavailable("Positions are updated by recording buys and sells.")

    def delete_portfolio_position(self, symbol: str, principal: AuthenticatedUser | None = None) -> None:
        raise PortfolioFeatureUnavailable("Positions are removed by recording a sell.")

    def get_portfolio_lots(
        self,
        symbol: str | None = None,
        only_open: bool = True,
        principal: AuthenticatedUser | None = None,
    ) -> list[dict[str, Any]]:
        self.ensure_schema()
        clauses = ["remaining_quantity > 0"] if only_open else ["1 = 1"]
        params: list[Any] = []
        if symbol:
            clauses.append("symbol = ?")
            params.append(symbol.upper())
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, id AS lot_id, symbol, buy_date, buy_price,
                       original_quantity, remaining_quantity, remaining_fees
                FROM portfolio_lots
                WHERE {' AND '.join(clauses)}
                ORDER BY buy_date ASC, id ASC
                """,
                params,
            ).fetchall()
        return [dict(row) for row in rows]

    def get_realized_gains(
        self,
        symbol: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        principal: AuthenticatedUser | None = None,
    ) -> list[dict[str, Any]]:
        self.ensure_schema()
        clauses: list[str] = []
        params: list[Any] = []
        if symbol:
            clauses.append("symbol = ?")
            params.append(symbol.upper())
        if from_date:
            clauses.append("realized_at >= ?")
            params.append(normalize_trade_date(from_date))
        if to_date:
            clauses.append("realized_at <= ?")
            params.append(normalize_trade_date(to_date))
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, symbol, sell_txn_id, lot_id, quantity, buy_price, sell_price,
                       gain AS realized_gain, gain_percent, gain_type,
                       realized_at AS sell_date, buy_fees, sell_fees, holding_days
                FROM portfolio_realized_gains
                {where}
                ORDER BY realized_at DESC, id DESC
                """,
                params,
            ).fetchall()
        gains = [dict(row) for row in rows]
        for row in gains:
            row["realized_stcg"] = row["realized_gain"] if row["gain_type"] == "STCG" else 0
            row["realized_ltcg"] = row["realized_gain"] if row["gain_type"] == "LTCG" else 0
        return gains

    def get_financial_year_realized_summary(
        self,
        fy_start_year: int | None = None,
        principal: AuthenticatedUser | None = None,
    ) -> dict[str, Any]:
        today = datetime.now(timezone.utc).date()
        start_year = fy_start_year or indian_financial_year_start(today)
        start_date = date(start_year, 4, 1)
        end_date = date(start_year + 1, 3, 31)
        gains = self.get_realized_gains(from_date=start_date.isoformat(), to_date=end_date.isoformat(), principal=principal)
        return _financial_year_summary(gains, start_year)

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
        self.ensure_schema()
        method_list = methods or ["FIFO", "LIFO", "HIFO"]
        lots = self.get_portfolio_lots(symbol=symbol, principal=principal)
        sale_date = normalize_trade_date(sell_date)
        scenarios = []
        for method in method_list:
            matched = match_sell(
                lots,
                quantity=quantity,
                sell_price=sell_price,
                sell_date=sale_date,
                fees=fees,
                method=method,
            )
            scenarios.append(
                {
                    "symbol": symbol.upper(),
                    "method": method,
                    "sold_quantity": float(quantity),
                    "sell_price": float(sell_price),
                    "fees": float(fees),
                    "realized_gain": round(sum(item["realized_gain"] for item in matched), 6),
                    "matched_lots": matched,
                }
            )
        return {
            "symbol": symbol.upper(),
            "sell_quantity": float(quantity or 0),
            "sell_price": float(sell_price or 0),
            "scenarios": scenarios,
            "recommended_method": method_list[0] if method_list else "FIFO",
        }

    def record_sell(
        self,
        symbol: str,
        quantity: float,
        sell_price: float,
        sell_date: str | None = None,
        fees: float = 0.0,
        method: str = "FIFO",
        notes: str | None = None,
        principal: AuthenticatedUser | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        self.ensure_schema()
        trade_date = normalize_trade_date(sell_date)
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            source_key = f"api:{idempotency_key}" if idempotency_key else None
            if source_key:
                previous = conn.execute(
                    "SELECT id, symbol, side, quantity, price, trade_date, fees, lot_method FROM portfolio_transactions WHERE source_key = ?",
                    (source_key,),
                ).fetchone()
                if previous is not None:
                    if (
                        previous["side"] != "SELL"
                        or previous["symbol"] != symbol.upper()
                        or float(previous["quantity"]) != float(quantity)
                        or float(previous["price"]) != float(sell_price)
                        or previous["trade_date"] != trade_date
                        or float(previous["fees"]) != float(fees)
                        or previous["lot_method"] != method.upper()
                    ):
                        raise ValueError("Idempotency key was already used for a different trade.")
                    return {"status": "ok", "transaction_id": previous["id"], "already_recorded": True}
            lots = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT id, id AS lot_id, symbol, buy_date, buy_price,
                           original_quantity, remaining_quantity, remaining_fees
                    FROM portfolio_lots
                    WHERE symbol = ? AND remaining_quantity > 0
                    ORDER BY buy_date ASC, id ASC
                    """,
                    (symbol.upper(),),
                ).fetchall()
            ]
            allocations = match_sell(
                lots,
                quantity=quantity,
                sell_price=sell_price,
                sell_date=trade_date,
                fees=fees,
                method=method,
            )
            txn = conn.execute(
                """
                INSERT INTO portfolio_transactions
                    (symbol, side, quantity, price, trade_date, fees, notes, source_key, lot_method, created_at)
                VALUES (?, 'SELL', ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_key) DO NOTHING
                RETURNING id
                """,
                (symbol.upper(), quantity, sell_price, trade_date, fees, notes, source_key, method.upper(), now),
            ).fetchone()
            if txn is None:
                previous = conn.execute(
                    "SELECT id, symbol, side, quantity, price, trade_date, fees, lot_method FROM portfolio_transactions WHERE source_key = ?",
                    (source_key,),
                ).fetchone()
                if previous is None:
                    raise RuntimeError("The sell transaction could not be confirmed.")
                if (
                    previous["side"] != "SELL"
                    or previous["symbol"] != symbol.upper()
                    or float(previous["quantity"]) != float(quantity)
                    or float(previous["price"]) != float(sell_price)
                    or previous["trade_date"] != trade_date
                    or float(previous["fees"]) != float(fees)
                    or previous["lot_method"] != method.upper()
                ):
                    raise ValueError("Idempotency key was already used for a different trade.")
                return {"status": "ok", "transaction_id": previous["id"], "already_recorded": True}
            for allocation in allocations:
                lot = next(row for row in lots if row["id"] == allocation["lot_id"])
                old_quantity = float(lot["remaining_quantity"])
                remaining_quantity = old_quantity - allocation["quantity"]
                remaining_fees = float(lot.get("remaining_fees") or 0) - allocation["buy_fees"]
                conn.execute(
                    "UPDATE portfolio_lots SET remaining_quantity = ?, remaining_fees = ? WHERE id = ?",
                    (max(0, remaining_quantity), max(0, remaining_fees), allocation["lot_id"]),
                )
                cost = allocation["buy_price"] * allocation["quantity"] + allocation["buy_fees"]
                gain = allocation["realized_gain"]
                conn.execute(
                    """
                    INSERT INTO portfolio_realized_gains (
                        symbol, sell_txn_id, lot_id, quantity, buy_price, sell_price,
                        gain, gain_percent, gain_type, realized_at, buy_fees, sell_fees, holding_days
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        symbol.upper(),
                        txn["id"],
                        allocation["lot_id"],
                        allocation["quantity"],
                        allocation["buy_price"],
                        allocation["sell_price"],
                        gain,
                        gain / cost * 100 if cost else None,
                        allocation["gain_type"],
                        trade_date,
                        allocation["buy_fees"],
                        allocation["sell_fees"],
                        (parse_trade_date(trade_date) - parse_trade_date(allocation["buy_date"])).days,
                    ),
                )
            self._refresh_position(conn, symbol)
        return {
            "status": "ok",
            "transaction_id": txn["id"],
            "symbol": symbol.upper(),
            "quantity": float(quantity),
            "sell_price": float(sell_price),
            "method": method.upper(),
            "realized_gain": round(sum(item["realized_gain"] for item in allocations), 6),
            "matched_lots": allocations,
        }

    @staticmethod
    def _refresh_position(conn, symbol: str) -> None:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(remaining_quantity), 0) AS quantity,
                   CASE WHEN SUM(remaining_quantity) > 0
                        THEN SUM(remaining_quantity * buy_price) / SUM(remaining_quantity)
                        ELSE NULL END AS avg_price,
                   MIN(buy_date) AS added_date
            FROM portfolio_lots
            WHERE symbol = ?
            """,
            (symbol.upper(),),
        ).fetchone()
        if not row or not row["quantity"]:
            conn.execute("DELETE FROM portfolio WHERE symbol = ?", (symbol.upper(),))
            return
        conn.execute(
            """
            INSERT INTO portfolio (symbol, quantity, avg_price, added_date)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                quantity = excluded.quantity,
                avg_price = excluded.avg_price,
                added_date = excluded.added_date
            """,
            (symbol.upper(), row["quantity"], row["avg_price"], row["added_date"]),
        )


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
            data.get("idempotency_key"),
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

    def record_sell(
        self,
        data: dict[str, Any],
        principal: AuthenticatedUser | None = None,
    ) -> dict[str, Any]:
        # Locked product decision: actual sells consume lots FIFO only.
        if str(data.get("method") or "FIFO").upper() != "FIFO":
            raise ValueError("Recorded sells must use FIFO; LIFO and HIFO are simulation-only.")
        result = self.repository.record_sell(
            data["symbol"],
            data["quantity"],
            data["sell_price"],
            sell_date=data["sell_date"],
            fees=data["fees"],
            method=data["method"],
            notes=data["notes"],
            principal=principal,
            idempotency_key=data.get("idempotency_key"),
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


def _financial_year_summary(gains: list[dict[str, Any]], start_year: int) -> dict[str, Any]:
    stcg = sum(float(row.get("realized_gain") or 0) for row in gains if row.get("gain_type") == "STCG")
    ltcg = sum(float(row.get("realized_gain") or 0) for row in gains if row.get("gain_type") == "LTCG")
    return {
        "financial_year": f"{start_year}-{str(start_year + 1)[-2:]}",
        "fy_start_year": start_year,
        "realized_total": round(stcg + ltcg, 6),
        "stcg_realized": round(stcg, 6),
        "ltcg_realized": round(ltcg, 6),
        "transactions": len({row.get("sell_txn_id") for row in gains}),
        "symbols": sorted({str(row["symbol"]) for row in gains if row.get("symbol")}),
        "tax_amount": None,
        "classification_basis": "India-listed equity: LTCG from 12-month anniversary; no tax calculation",
    }
