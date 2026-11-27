"""User-scoped portfolio persistence through Supabase PostgREST and RLS."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import requests

from backend.db import apply_migrations
from backend.domain.portfolio.exceptions import PortfolioFeatureUnavailable
from backend.domain.portfolio.ledger import (
    indian_financial_year_start,
    match_sell,
    normalize_trade_date,
)
from backend.services.supabase_auth import AuthenticatedUser


class SupabasePortfolioRepository:
    provider_name = "supabase_postgres_portfolio"

    def __init__(
        self,
        *,
        supabase_url: str,
        publishable_key: str,
        secret_key: str,
        local_db_path: Path,
        session: requests.Session | None = None,
        verify_remote_schema: bool = True,
    ):
        self.supabase_url = supabase_url.rstrip("/")
        self.publishable_key = publishable_key
        self.secret_key = secret_key
        self.local_db_path = Path(local_db_path)
        self.session = session or requests.Session()
        self.verify_remote_schema = verify_remote_schema

    @property
    def db_path(self) -> Path:
        return self.local_db_path

    def ensure_schema(self) -> None:
        apply_migrations(
            self.local_db_path,
            backup=self.local_db_path.exists(),
            backup_dir=self.local_db_path.parent / "backups",
        )
        if not self.verify_remote_schema:
            return
        response = self.session.get(
            f"{self.supabase_url}/rest/v1/portfolio_positions",
            params={"select": "id", "limit": "1"},
            headers={
                "apikey": self.secret_key,
            },
            timeout=10,
        )
        response.raise_for_status()

    def get_portfolio(self, principal: AuthenticatedUser | None = None) -> list[dict[str, Any]]:
        user = self._require_user(principal)
        response = self._request(
            "GET",
            params={
                "select": "id,symbol,quantity,avg_price,added_date",
                "user_id": f"eq.{user.user_id}",
                "order": "symbol.asc",
            },
            principal=user,
        )
        rows = response.json()
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise RuntimeError("Supabase returned an invalid portfolio response.")
        return rows

    def add_to_portfolio(
        self,
        symbol: str,
        quantity: float,
        avg_price: float,
        purchase_date: str | None = None,
        principal: AuthenticatedUser | None = None,
        idempotency_key: str | None = None,
    ) -> None:
        user = self._require_user(principal)
        self._rpc(
            "record_portfolio_buy",
            {
                "p_symbol": symbol.upper(),
                "p_quantity": float(quantity),
                "p_price": float(avg_price),
                "p_trade_date": normalize_trade_date(purchase_date) if purchase_date else None,
                "p_fees": 0,
                "p_idempotency_key": idempotency_key,
            },
            principal=user,
        )

    def update_portfolio_position_summary(
        self,
        symbol: str,
        quantity: float,
        avg_price: float,
        purchase_date: str | None = None,
        principal: AuthenticatedUser | None = None,
    ) -> None:
        self._require_user(principal)
        raise PortfolioFeatureUnavailable("Positions are updated by recording buys and sells.")

    def delete_portfolio_position(
        self,
        symbol: str,
        principal: AuthenticatedUser | None = None,
    ) -> None:
        self._require_user(principal)
        raise PortfolioFeatureUnavailable("Positions are removed by recording a sell.")

    def get_portfolio_lots(
        self,
        symbol: str | None = None,
        only_open: bool = True,
        principal: AuthenticatedUser | None = None,
    ) -> list[dict[str, Any]]:
        user = self._require_user(principal)
        params = {
            "select": "id,symbol,buy_txn_id,buy_date,buy_price,original_quantity,remaining_quantity,original_fees,remaining_fees",
            "user_id": f"eq.{user.user_id}",
            "order": "buy_date.asc,id.asc",
        }
        if only_open:
            params["remaining_quantity"] = "gt.0"
        if symbol:
            params["symbol"] = f"eq.{symbol.upper()}"
        response = self._request("GET", params=params, principal=user, resource="portfolio_lots")
        rows = response.json()
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise RuntimeError("Supabase returned an invalid portfolio-lots response.")
        return [{**row, "lot_id": row["id"]} for row in rows]

    def get_realized_gains(
        self,
        symbol: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        principal: AuthenticatedUser | None = None,
    ) -> list[dict[str, Any]]:
        user = self._require_user(principal)
        params = {
            "select": "id,symbol,sell_txn_id,lot_id,quantity,buy_price,sell_price,buy_fees,sell_fees,gain,gain_percent,holding_days,gain_type,realized_at",
            "user_id": f"eq.{user.user_id}",
            "order": "realized_at.desc,id.desc",
        }
        if symbol:
            params["symbol"] = f"eq.{symbol.upper()}"
        if from_date and to_date:
            params["and"] = (
                f"(realized_at.gte.{normalize_trade_date(from_date)},"
                f"realized_at.lte.{normalize_trade_date(to_date)})"
            )
        elif from_date:
            params["realized_at"] = f"gte.{normalize_trade_date(from_date)}"
        elif to_date:
            params["realized_at"] = f"lte.{normalize_trade_date(to_date)}"
        response = self._request("GET", params=params, principal=user, resource="portfolio_realized_gains")
        rows = response.json()
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise RuntimeError("Supabase returned an invalid realized-gains response.")
        gains = []
        for row in rows:
            gain = float(row["gain"])
            gains.append(
                {
                    **row,
                    "realized_gain": gain,
                    "realized_stcg": gain if row["gain_type"] == "STCG" else 0,
                    "realized_ltcg": gain if row["gain_type"] == "LTCG" else 0,
                    "sell_date": row["realized_at"],
                }
            )
        return gains

    def get_financial_year_realized_summary(
        self,
        fy_start_year: int | None = None,
        principal: AuthenticatedUser | None = None,
    ) -> dict[str, Any]:
        user = self._require_user(principal)
        today = datetime.now(timezone.utc).date()
        start_year = fy_start_year or indian_financial_year_start(today)
        gains = self.get_realized_gains(
            from_date=date(start_year, 4, 1).isoformat(),
            to_date=date(start_year + 1, 3, 31).isoformat(),
            principal=user,
        )
        stcg = sum(row["realized_gain"] for row in gains if row["gain_type"] == "STCG")
        ltcg = sum(row["realized_gain"] for row in gains if row["gain_type"] == "LTCG")
        return {
            "financial_year": f"{start_year}-{str(start_year + 1)[-2:]}",
            "fy_start_year": start_year,
            "realized_total": round(stcg + ltcg, 6),
            "stcg_realized": round(stcg, 6),
            "ltcg_realized": round(ltcg, 6),
            "transactions": len({row.get("sell_txn_id") for row in gains}),
            "symbols": sorted({row["symbol"] for row in gains}),
            "tax_amount": None,
            "classification_basis": "India-listed equity: LTCG from 12-month anniversary; no tax calculation",
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
        lots = self.get_portfolio_lots(symbol=symbol, principal=principal)
        method_list = methods or ["FIFO", "LIFO", "HIFO"]
        scenarios = []
        for method in method_list:
            matched = match_sell(
                lots,
                quantity=quantity,
                sell_price=sell_price,
                sell_date=normalize_trade_date(sell_date),
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
            "sell_quantity": float(quantity),
            "sell_price": float(sell_price),
            "scenarios": scenarios,
            "recommended_method": "FIFO",
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
        user = self._require_user(principal)
        if not idempotency_key:
            lots = self.get_portfolio_lots(symbol=symbol, principal=user)
            match_sell(
                lots,
                quantity=quantity,
                sell_price=sell_price,
                sell_date=normalize_trade_date(sell_date),
                fees=fees,
                method=method,
            )
        return self._rpc(
            "record_portfolio_sell",
            {
                "p_symbol": symbol.upper(),
                "p_quantity": float(quantity),
                "p_price": float(sell_price),
                "p_trade_date": normalize_trade_date(sell_date),
                "p_fees": float(fees),
                "p_method": method.upper(),
                "p_notes": notes,
                "p_idempotency_key": idempotency_key,
            },
            principal=user,
        )

    def _request(
        self,
        method: str,
        *,
        principal: AuthenticatedUser,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        resource: str = "portfolio_positions",
    ) -> requests.Response:
        request_headers = {
            "apikey": self.publishable_key,
            "Authorization": f"Bearer {principal.access_token}",
            "Content-Type": "application/json",
        }
        request_headers.update(headers or {})
        response = self.session.request(
            method,
            f"{self.supabase_url}/rest/v1/{resource}",
            params=params,
            json=json,
            headers=request_headers,
            timeout=10,
        )
        response.raise_for_status()
        return response

    def _rpc(
        self,
        function: str,
        payload: dict[str, Any],
        *,
        principal: AuthenticatedUser,
    ) -> dict[str, Any]:
        response = self.session.post(
            f"{self.supabase_url}/rest/v1/rpc/{function}",
            json=payload,
            headers={
                "apikey": self.publishable_key,
                "Authorization": f"Bearer {principal.access_token}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        if response.status_code == 400:
            try:
                details = response.json()
            except ValueError:
                details = {}
            message = details.get("message") if isinstance(details, dict) else None
            raise ValueError(str(message or f"Supabase rejected RPC {function}."))
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict):
            raise RuntimeError(f"Supabase RPC {function} returned an invalid response.")
        return result

    @staticmethod
    def _require_user(principal: AuthenticatedUser | None) -> AuthenticatedUser:
        if principal is None:
            raise RuntimeError("A verified user is required for portfolio access.")
        return principal
