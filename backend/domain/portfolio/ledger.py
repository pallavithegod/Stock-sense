"""Shared portfolio lot matching and Indian FY classification helpers."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any


SELL_METHODS = {"FIFO", "LIFO", "HIFO"}


def parse_trade_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return date.fromisoformat(text[:10])


def normalize_trade_date(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).date().isoformat()
    return parse_trade_date(value).isoformat()


def gain_type(buy_date: Any, sell_date: Any) -> str:
    bought = parse_trade_date(buy_date)
    sold = parse_trade_date(sell_date)
    try:
        long_term_from = bought.replace(year=bought.year + 1)
    except ValueError:
        long_term_from = bought.replace(year=bought.year + 1, day=28)
    return "LTCG" if sold >= long_term_from else "STCG"


def match_sell(
    lots: list[dict[str, Any]],
    *,
    quantity: float,
    sell_price: float,
    sell_date: str,
    fees: float = 0.0,
    method: str = "FIFO",
) -> list[dict[str, Any]]:
    normalized_method = method.upper()
    if normalized_method not in SELL_METHODS:
        raise ValueError(f"Unsupported sell method: {method}")
    requested = Decimal(str(quantity))
    available = sum((Decimal(str(lot["remaining_quantity"])) for lot in lots), Decimal("0"))
    if requested <= 0 or requested > available:
        raise ValueError("Sell quantity exceeds the available open-lot quantity.")

    def ordering(lot: dict[str, Any]) -> tuple[Any, ...]:
        bought = parse_trade_date(lot["buy_date"])
        if normalized_method == "FIFO":
            return (bought, str(lot.get("id", lot.get("lot_id", ""))))
        if normalized_method == "LIFO":
            return (-bought.toordinal(), str(lot.get("id", lot.get("lot_id", ""))))
        return (-Decimal(str(lot["buy_price"])), bought, str(lot.get("id", lot.get("lot_id", ""))))

    remaining = requested
    sell_fee_total = Decimal(str(fees))
    sale_price = Decimal(str(sell_price))
    allocations: list[dict[str, Any]] = []
    for lot in sorted(lots, key=ordering):
        lot_quantity = Decimal(str(lot["remaining_quantity"]))
        if lot_quantity <= 0:
            continue
        bought_date = parse_trade_date(lot["buy_date"])
        if parse_trade_date(sell_date) < bought_date:
            raise ValueError("Sell date cannot be earlier than the lot purchase date.")
        allocated_quantity = min(remaining, lot_quantity)
        remaining_buy_fees = Decimal(str(lot.get("remaining_fees") or 0))
        allocated_buy_fees = remaining_buy_fees * allocated_quantity / lot_quantity
        allocated_sell_fees = sell_fee_total * allocated_quantity / requested
        buy_price = Decimal(str(lot["buy_price"]))
        realized_gain = (sale_price - buy_price) * allocated_quantity - allocated_buy_fees - allocated_sell_fees
        allocations.append(
            {
                "lot_id": lot.get("id", lot.get("lot_id")),
                "symbol": lot.get("symbol"),
                "quantity": float(allocated_quantity),
                "buy_price": float(buy_price),
                "sell_price": float(sale_price),
                "buy_fees": float(allocated_buy_fees),
                "sell_fees": float(allocated_sell_fees),
                "realized_gain": float(realized_gain),
                "gain_type": gain_type(lot["buy_date"], sell_date),
                "buy_date": bought_date.isoformat(),
                "sell_date": normalize_trade_date(sell_date),
            }
        )
        remaining -= allocated_quantity
        if remaining == 0:
            break
    if remaining:
        raise ValueError("Sell quantity exceeds the available open-lot quantity.")
    return allocations


def indian_financial_year_start(value: date) -> int:
    return value.year if value.month >= 4 else value.year - 1
