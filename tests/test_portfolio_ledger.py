from __future__ import annotations

from backend.db import connect
from backend.domain.portfolio.service import SQLitePortfolioRepository


def test_legacy_aggregate_position_is_seeded_as_opening_lot(tmp_path):
    db_path = tmp_path / "portfolio.db"
    repository = SQLitePortfolioRepository(db_path)
    repository.ensure_schema()
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO portfolio (symbol, quantity, avg_price, added_date) VALUES (?, ?, ?, ?)",
            ("INFY", 4, 125, "2025-01-12T00:00:00+00:00"),
        )

    lots = repository.get_portfolio_lots("INFY")

    assert len(lots) == 1
    assert lots[0]["remaining_quantity"] == 4
    assert lots[0]["buy_price"] == 125
    assert lots[0]["buy_date"] == "2025-01-12"


def test_fifo_sale_updates_positions_and_realized_indian_fy_gains(tmp_path):
    repository = SQLitePortfolioRepository(tmp_path / "portfolio.db")
    repository.add_to_portfolio("INFY", 3, 100, "2024-01-01")
    repository.add_to_portfolio("INFY", 2, 120, "2025-01-01")

    simulation = repository.compare_sell_methods(
        "INFY",
        4,
        150,
        sell_date="2026-01-02",
        fees=4,
        methods=["FIFO"],
    )
    result = repository.record_sell(
        "INFY",
        4,
        150,
        sell_date="2026-01-02",
        fees=4,
        method="FIFO",
    )

    assert simulation["scenarios"][0]["realized_gain"] == 176
    assert result["realized_gain"] == 176
    assert [lot["quantity"] for lot in result["matched_lots"]] == [3, 1]
    assert repository.get_portfolio()[0]["quantity"] == 1
    assert repository.get_portfolio()[0]["avg_price"] == 120

    gains = repository.get_realized_gains()
    assert len(gains) == 2
    assert all(row["gain_type"] == "LTCG" for row in gains)
    summary = repository.get_financial_year_realized_summary(fy_start_year=2025)
    assert summary["financial_year"] == "2025-26"
    assert summary["realized_total"] == 176
    assert summary["ltcg_realized"] == 176
    assert summary["transactions"] == 1


def test_sell_cannot_exceed_open_lots_or_precede_purchase_date(tmp_path):
    repository = SQLitePortfolioRepository(tmp_path / "portfolio.db")
    repository.add_to_portfolio("INFY", 1, 100, "2026-01-01")

    try:
        repository.record_sell("INFY", 2, 120, sell_date="2026-02-01")
    except ValueError as exc:
        assert "available open-lot quantity" in str(exc)
    else:
        raise AssertionError("Overselling should be rejected.")

    try:
        repository.record_sell("INFY", 1, 120, sell_date="2025-12-31")
    except ValueError as exc:
        assert "earlier than" in str(exc)
    else:
        raise AssertionError("A sell before the buy date should be rejected.")


def test_trade_idempotency_retries_are_safe_and_reject_reused_keys(tmp_path):
    repository = SQLitePortfolioRepository(tmp_path / "portfolio.db")
    repository.add_to_portfolio("INFY", 2, 100, "2025-01-01", idempotency_key="buy-1")
    repository.add_to_portfolio("INFY", 2, 100, "2025-01-01", idempotency_key="buy-1")

    assert repository.get_portfolio()[0]["quantity"] == 2
    try:
        repository.add_to_portfolio("INFY", 3, 100, "2025-01-01", idempotency_key="buy-1")
    except ValueError as exc:
        assert "different trade" in str(exc)
    else:
        raise AssertionError("Reusing a buy idempotency key with a different payload must fail.")

    first = repository.record_sell(
        "INFY", 2, 120, sell_date="2025-02-01", idempotency_key="sell-1"
    )
    retry = repository.record_sell(
        "INFY", 2, 120, sell_date="2025-02-01", idempotency_key="sell-1"
    )

    assert first["realized_gain"] == 40
    assert retry["already_recorded"] is True
    assert repository.get_portfolio() == []

