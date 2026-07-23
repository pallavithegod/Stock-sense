"""Portfolio calculation helpers.

These functions are deliberately framework-free. Database access and market
data fetching stay injected by the app layer while calculations live here.
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np


PriceFetcher = Callable[[str, str], Any]


EMPTY_PORTFOLIO_METRICS = {
    "total_value": 0,
    "day_pnl": 0,
    "day_pnl_percent": 0,
    "active_positions": 0,
    "winners": 0,
    "losers": 0,
    "risk_level": "LOW",
}


def enrich_holdings_with_prices(
    holdings: list[dict[str, Any]],
    *,
    price_fetcher: PriceFetcher,
    logger: Any,
) -> list[dict[str, Any]]:
    enriched = []
    for holding in holdings or []:
        try:
            symbol = holding.get("symbol")
            if not symbol:
                continue

            frame = price_fetcher(symbol, "1d")
            current_price = holding.get("avg_price", 0)
            if frame is not None and len(frame) > 0:
                current_price = float(frame["Close"].iloc[-1])

            avg_price = float(holding.get("avg_price", 0) or 0)
            quantity = float(holding.get("quantity", 0) or 0)
            pnl = (current_price - avg_price) * quantity
            pnl_percent = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0

            enriched.append({
                **holding,
                "current_price": current_price,
                "pnl": pnl,
                "pnl_percent": pnl_percent,
            })
        except Exception as exc:
            logger.warning("Portfolio enrichment failed: %s", exc)
            enriched.append(holding)
    return enriched


def calculate_portfolio_volatility(
    holdings: list[dict[str, Any]],
    *,
    price_fetcher: PriceFetcher,
) -> float:
    if not holdings:
        return 0.0

    returns = []
    for holding in holdings:
        symbol = holding.get("symbol", "")
        frame = price_fetcher(symbol, "1mo")
        if frame is not None and len(frame) > 1:
            daily_returns = frame["Close"].pct_change().dropna()
            returns.extend(daily_returns.tolist())
    return float(np.std(returns)) if returns else 0.0


def calculate_portfolio_metrics(
    holdings: list[dict[str, Any]],
    *,
    volatility: float,
) -> dict[str, Any]:
    if not holdings:
        return dict(EMPTY_PORTFOLIO_METRICS)

    total_value = 0.0
    total_invested = 0.0
    winners = 0
    losers = 0

    for holding in holdings:
        quantity = float(holding.get("quantity", 0) or 0)
        current_price = float(holding.get("current_price", 0) or 0)
        avg_price = float(holding.get("avg_price", 0) or 0)

        total_value += quantity * current_price
        total_invested += quantity * avg_price

        pnl = (current_price - avg_price) * quantity
        if pnl > 0:
            winners += 1
        elif pnl < 0:
            losers += 1

    day_pnl = total_value - total_invested
    day_pnl_percent = (day_pnl / total_invested * 100) if total_invested > 0 else 0
    risk_level = "HIGH" if volatility > 0.3 else "MEDIUM" if volatility > 0.15 else "LOW"

    return {
        "total_value": round(total_value, 2),
        "day_pnl": round(day_pnl, 2),
        "day_pnl_percent": round(day_pnl_percent, 2),
        "active_positions": len(holdings),
        "winners": winners,
        "losers": losers,
        "risk_level": risk_level,
    }
