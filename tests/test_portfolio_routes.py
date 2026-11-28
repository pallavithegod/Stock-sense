from __future__ import annotations

from pathlib import Path

import pytest


def unused_portfolio_symbol(client):
    services = client.application.extensions["stocksense_services"]
    held = {row["symbol"] for row in services.portfolio.list_positions()}
    return next(symbol for symbol in services.market.symbols if symbol not in held)


def fresh_symbol(client, monkeypatch, name: str) -> str:
    """Register a test-only symbol so ledger tests never share lots with other tests."""
    services = client.application.extensions["stocksense_services"]
    monkeypatch.setitem(
        services.market.symbols,
        name,
        {"symbol": name, "name": name, "exchange_symbols": [f"{name}.NS"]},
    )
    return name


def test_portfolio_routes_are_registered_by_blueprint(app_module):
    endpoints = {rule.endpoint for rule in app_module.app.url_map.iter_rules()}

    assert "api_v1.portfolio" in endpoints
    assert "api_v1.portfolio_positions" in endpoints
    assert "api_v1.create_portfolio_position" in endpoints
    assert "api_v1.portfolio_sell_simulate" in endpoints
    assert "api_v1.portfolio_forecast" in endpoints
    assert "api_v1.portfolio_governance" in endpoints
    assert "api_v1.portfolio_scorecard" in endpoints


def test_portfolio_create_and_state_use_domain_service(client):
    create_response = client.post(
        "/api/v1/portfolio",
        json={"symbol": "INFY", "quantity": 2, "avg_price": 100},
    )
    assert create_response.status_code == 200
    assert create_response.get_json()["data"]["status"] == "ok"

    list_response = client.get("/api/v1/portfolio/positions")
    assert list_response.status_code == 200
    positions = list_response.get_json()["data"]["positions"]
    assert positions[0]["symbol"] == "INFY"
    assert positions[0]["quantity"] == 2

    state_response = client.get("/api/v1/portfolio")
    assert state_response.status_code == 200
    state = state_response.get_json()["data"]
    assert state["account_metrics"]["total_value"] == 200


def test_portfolio_buy_reports_idempotency_conflicts_as_client_errors(client, monkeypatch):
    services = client.application.extensions["stocksense_services"]

    def reject_conflict(*args, **kwargs):
        raise ValueError("Idempotency key was already used for a different trade.")

    monkeypatch.setattr(services.portfolio, "create_position", reject_conflict)
    response = client.post(
        "/api/v1/portfolio",
        json={"symbol": "INFY", "quantity": 2, "avg_price": 100, "idempotency_key": "duplicate"},
    )

    assert response.status_code == 400
    assert "different trade" in response.get_json()["error"]


def test_portfolio_sell_simulation_is_read_only(client):
    response = client.post(
        "/api/v1/portfolio/sell/simulate",
        json={"symbol": "INFY", "quantity": 1, "sell_price": 120, "methods": ["FIFO"]},
    )

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["status"] == "ok"
    assert payload["data"]["recommended_method"] == "FIFO"


def test_portfolio_sell_records_realized_gain_and_reduces_open_position(client):
    symbol = unused_portfolio_symbol(client)
    client.post(
        "/api/v1/portfolio",
        json={"symbol": symbol, "quantity": 2, "avg_price": 100, "purchase_date": "2026-01-01"},
    )

    response = client.post(
        "/api/v1/portfolio/sell",
        json={
            "symbol": symbol,
            "quantity": 1,
            "sell_price": 125,
            "sell_date": "2026-03-01",
            "fees": 2,
            "method": "FIFO",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["data"]["data"]["realized_gain"] == 23
    positions = client.get("/api/v1/portfolio/positions").get_json()["data"]["positions"]
    position = next(row for row in positions if row["symbol"] == symbol)
    assert position["quantity"] == 1
    gains = client.get("/api/v1/portfolio/realized-gains").get_json()["data"]["data"]
    gain = next(row for row in gains if row["symbol"] == symbol)
    assert gain["gain_type"] == "STCG"
    assert gain["realized_gain"] == 23


def test_portfolio_sell_rejects_overselling(client):
    symbol = unused_portfolio_symbol(client)
    client.post("/api/v1/portfolio", json={"symbol": symbol, "quantity": 1, "avg_price": 100})

    response = client.post(
        "/api/v1/portfolio/sell",
        json={"symbol": symbol, "quantity": 2, "sell_price": 125},
    )

    assert response.status_code == 400
    assert "available open-lot quantity" in response.get_json()["error"]


@pytest.mark.parametrize("method", ["LIFO", "HIFO", "lifo"])
def test_recorded_sell_rejects_non_fifo_without_writing(client, monkeypatch, method):
    symbol = fresh_symbol(client, monkeypatch, f"FIFOREJ{method.upper()}{method.islower():d}")
    client.post(
        "/api/v1/portfolio",
        json={"symbol": symbol, "quantity": 2, "avg_price": 100, "purchase_date": "2026-01-01"},
    )

    response = client.post(
        "/api/v1/portfolio/sell",
        json={"symbol": symbol, "quantity": 1, "sell_price": 125, "sell_date": "2026-03-01", "method": method},
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body["field"] == "method"
    assert "FIFO" in body["error"]
    positions = client.get("/api/v1/portfolio/positions").get_json()["data"]["positions"]
    assert next(row for row in positions if row["symbol"] == symbol)["quantity"] == 2
    gains = client.get("/api/v1/portfolio/realized-gains").get_json()["data"]["data"]
    assert not any(row["symbol"] == symbol for row in gains)


def test_recorded_sell_defaults_to_fifo_when_method_omitted(client, monkeypatch):
    symbol = fresh_symbol(client, monkeypatch, "FIFODEFAULT")
    client.post(
        "/api/v1/portfolio",
        json={"symbol": symbol, "quantity": 1, "avg_price": 100, "purchase_date": "2026-01-01"},
    )
    client.post(
        "/api/v1/portfolio",
        json={"symbol": symbol, "quantity": 1, "avg_price": 200, "purchase_date": "2026-02-01"},
    )

    response = client.post(
        "/api/v1/portfolio/sell",
        json={"symbol": symbol, "quantity": 1, "sell_price": 150, "sell_date": "2026-03-01"},
    )

    assert response.status_code == 200
    data = response.get_json()["data"]["data"]
    assert data["method"] == "FIFO"
    # FIFO consumes the oldest lot (bought at 100), not the newer 200 lot.
    assert data["realized_gain"] == 50


def test_sell_simulation_still_compares_fifo_lifo_hifo(client, monkeypatch):
    symbol = fresh_symbol(client, monkeypatch, "FIFOSIM")
    client.post(
        "/api/v1/portfolio",
        json={"symbol": symbol, "quantity": 1, "avg_price": 100, "purchase_date": "2026-01-01"},
    )
    client.post(
        "/api/v1/portfolio",
        json={"symbol": symbol, "quantity": 1, "avg_price": 200, "purchase_date": "2026-02-01"},
    )

    response = client.post(
        "/api/v1/portfolio/sell/simulate",
        json={"symbol": symbol, "quantity": 1, "sell_price": 150, "sell_date": "2026-03-01", "method": "HIFO"},
    )

    assert response.status_code == 200
    scenarios = {row["method"]: row for row in response.get_json()["data"]["data"]["scenarios"]}
    assert set(scenarios) == {"FIFO", "LIFO", "HIFO"}
    positions = client.get("/api/v1/portfolio/positions").get_json()["data"]["positions"]
    assert next(row for row in positions if row["symbol"] == symbol)["quantity"] == 2


def test_portfolio_service_rejects_non_fifo_record_before_repository(client, monkeypatch):
    services = client.application.extensions["stocksense_services"]
    calls = []
    monkeypatch.setattr(services.portfolio.repository, "record_sell", lambda *a, **k: calls.append(a))

    with pytest.raises(ValueError, match="FIFO"):
        services.portfolio.record_sell(
            {
                "symbol": "INFY",
                "quantity": 1,
                "sell_price": 100,
                "sell_date": None,
                "fees": 0,
                "method": "HIFO",
                "notes": None,
            }
        )

    assert calls == []


def test_fifo_migration_guards_rpc_and_runs_after_ledger_migration():
    migrations = sorted(Path("supabase/migrations").glob("*.sql"))
    names = [path.name for path in migrations]
    fifo = Path("supabase/migrations/20261128_enforce_fifo_recorded_sells.sql")
    sql = fifo.read_text(encoding="utf-8")

    assert names.index(fifo.name) > names.index("20261127_portfolio_trade_ledger.sql")
    assert "create or replace function public.record_portfolio_sell(" in sql
    assert "if v_method <> 'FIFO' then" in sql
    assert "grant execute on function public.record_portfolio_sell(" in sql
    assert "delete from public.market_daily_bars" not in sql


def test_portfolio_intelligence_slices_are_domain_service_payloads(client):
    client.post("/api/v1/portfolio", json={"symbol": "INFY", "quantity": 2, "avg_price": 100})

    suite = client.get("/api/v1/portfolio/intelligence-suite")
    forecast = client.get("/api/v1/portfolio/forecast")
    governance = client.get("/api/v1/portfolio/governance")
    allocation = client.get("/api/v1/portfolio/allocation")

    assert suite.status_code == 200
    assert suite.get_json()["data"]["data"]["data_quality"] == "portfolio_only"
    assert suite.get_json()["data"]["data"]["is_synthetic"] is False
    assert suite.get_json()["data"]["data"]["is_demo"] is False
    assert forecast.status_code == 200
    assert forecast.get_json()["data"]["data"]["status"] == "unavailable_without_market_provider"
    assert governance.status_code == 200
    assert governance.get_json()["data"]["data"]["status"] == "WATCH"
    assert allocation.status_code == 200
    assert "INFY" in allocation.get_json()["data"]["data"]["labels"]


def test_legacy_portfolio_aliases_are_removed(client):
    assert client.get("/api/portfolio").status_code == 404
    assert client.get("/api/portfolio/state").status_code == 404
    assert client.post("/api/portfolio", json={"symbol": "INFY"}).status_code == 404
