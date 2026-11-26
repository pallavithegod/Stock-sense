"""User-scoped portfolio persistence through Supabase PostgREST and RLS."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from backend.db import apply_migrations
from backend.domain.portfolio.exceptions import PortfolioFeatureUnavailable
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
    ) -> None:
        user = self._require_user(principal)
        body = {
            "user_id": user.user_id,
            "symbol": symbol.upper(),
            "quantity": float(quantity),
            "avg_price": float(avg_price),
        }
        if purchase_date:
            body["added_date"] = _normalize_timestamp(purchase_date)
        self._request(
            "POST",
            params={"on_conflict": "user_id,symbol"},
            json=body,
            headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
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
        self.add_to_portfolio(symbol, quantity, avg_price, purchase_date, principal)

    def delete_portfolio_position(
        self,
        symbol: str,
        principal: AuthenticatedUser | None = None,
    ) -> None:
        user = self._require_user(principal)
        self._request(
            "DELETE",
            params={
                "user_id": f"eq.{user.user_id}",
                "symbol": f"eq.{symbol.upper()}",
            },
            principal=user,
        )

    def get_portfolio_lots(
        self,
        symbol: str | None = None,
        only_open: bool = True,
        principal: AuthenticatedUser | None = None,
    ) -> list[dict[str, Any]]:
        self._require_user(principal)
        raise PortfolioFeatureUnavailable(
            "Trade-lot history is not available for aggregate portfolio positions."
        )

    def get_realized_gains(
        self,
        symbol: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        principal: AuthenticatedUser | None = None,
    ) -> list[dict[str, Any]]:
        self._require_user(principal)
        raise PortfolioFeatureUnavailable("Realized gains are not available without trade history.")

    def get_financial_year_realized_summary(
        self,
        fy_start_year: int | None = None,
        principal: AuthenticatedUser | None = None,
    ) -> dict[str, Any]:
        self._require_user(principal)
        raise PortfolioFeatureUnavailable("Tax summaries are not available without trade history.")

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
        self._require_user(principal)
        raise PortfolioFeatureUnavailable("Sell simulation is not available without trade history.")

    def _request(
        self,
        method: str,
        *,
        principal: AuthenticatedUser,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> requests.Response:
        request_headers = {
            "apikey": self.publishable_key,
            "Authorization": f"Bearer {principal.access_token}",
            "Content-Type": "application/json",
        }
        request_headers.update(headers or {})
        response = self.session.request(
            method,
            f"{self.supabase_url}/rest/v1/portfolio_positions",
            params=params,
            json=json,
            headers=request_headers,
            timeout=10,
        )
        response.raise_for_status()
        return response

    @staticmethod
    def _require_user(principal: AuthenticatedUser | None) -> AuthenticatedUser:
        if principal is None:
            raise RuntimeError("A verified user is required for portfolio access.")
        return principal


def _normalize_timestamp(value: str) -> str:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()
