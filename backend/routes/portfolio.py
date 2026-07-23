"""Portfolio route handlers and blueprint wiring."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping
from zoneinfo import ZoneInfo
import time

from flask import Blueprint, jsonify, request


def configure_portfolio_runtime(runtime_globals: Mapping[str, Any]) -> None:
    """Expose legacy app dependencies used by portfolio handlers."""
    for name, value in runtime_globals.items():
        if not name.startswith("__"):
            globals()[name] = value


def create_portfolio():
    """Portfolio REST create"""
    try:
        ensure_market_universe_loaded()
        data = validate_portfolio_create(
            request.get_json(silent=True),
            normalize_symbol=normalize_symbol,
            known_symbols=set(MARKET.symbols.keys()),
        )
        symbol = data["symbol"]
        qty = data["quantity"]
        price = data["avg_price"]
        date = data["purchase_date"]

        if not symbol:
            return jsonify({"status": "error", "error": "invalid symbol"}), 400

        if symbol not in MARKET.symbols:
            return jsonify({"status": "error", "error": f"Unknown symbol: {symbol}"}), 400

        # choose an exchange symbol for reporting
        entry = MARKET.symbols[symbol]
        if "exchange_symbol" in entry:
            exchange_symbol = entry["exchange_symbol"]
        else:
            ex_list = entry.get("exchange_symbols", [])
            # prefer NSE if available
            if ex_list:
                exchange_symbol = next((e for e in ex_list if e.endswith(".NS")), ex_list[0])
            else:
                exchange_symbol = f"{symbol}.NS"

        if qty <= 0:
            return jsonify({"status": "error", "error": "invalid quantity"}), 400
        if price <= 0:
            return jsonify({"status": "error", "error": "invalid avg_price"}), 400

        # DB uses base symbol
        quantum_ai.db.add_to_portfolio(symbol, qty, price, date)

        trigger_ai_recompute()

        # inform caller which exchange symbol was used (helps with BSE vs NSE)
        return jsonify({"status": "ok", "exchange_symbol": exchange_symbol})

    except ValidationError as e:
        return jsonify(validation_error_payload(e)), 400
    except Exception as e:
        logger.exception("PORTFOLIO ADD FAILED")
        return jsonify({"status": "error", "error": str(e)}), 500


def create_portfolio_legacy():
    return create_portfolio()


def api_portfolio_state():
    """Reactive portfolio snapshot endpoint sourced from STATE_CACHE."""
    started_at = time.perf_counter()
    try:
        with cache_lock:
            pf_state = STATE_CACHE.get("PORTFOLIO_STATE", {})
            cached_pi = pf_state.get("portfolio_intelligence") or {}
            cached_positions = cached_pi.get("positions") if isinstance(cached_pi, dict) else None
        if isinstance(cached_positions, list) and pf_state.get("last_updated"):
            return jsonify({
                "success": True,
                "positions": cached_pi.get("positions", []),
                "account_metrics": cached_pi.get("account_metrics", {})
            })

        holdings = quantum_ai.db.get_portfolio() or []
        if not holdings:
            return jsonify({"success": True, "positions": [], "account_metrics": {}})

        preds = AI_ENGINE_STATE.get("predictions", {}) or {}
        if not preds:
            try:
                recent = system_cache.get("recent_predictions", []) or []
                preds = {p.get("symbol"): p for p in recent if p.get("symbol")}
            except Exception:
                preds = {}

        pi = quantum_ai.compute_portfolio_intelligence(holdings, preds=preds)
        with cache_lock:
            pf_state = STATE_CACHE.get("PORTFOLIO_STATE", {})
            pf_state["portfolio_intelligence"] = pi or {"positions": [], "account_metrics": {}}
            pf_state["last_updated"] = datetime.now(ZoneInfo("UTC")).isoformat()
            STATE_CACHE["SYSTEM_HEALTH"]["portfolio_latency_ms"] = round((time.perf_counter() - started_at) * 1000.0, 2)
        return jsonify({"success": True, "positions": pi.get("positions", []), "account_metrics": pi.get("account_metrics", {})})
    except Exception as e:
        logger.error(f"Portfolio state error: {e}")
        with cache_lock:
            stale_pi = STATE_CACHE.get("PORTFOLIO_STATE", {}).get("portfolio_intelligence") or {}
        if isinstance(stale_pi, dict) and stale_pi:
            return jsonify({
                "success": True,
                "positions": stale_pi.get("positions", []),
                "account_metrics": stale_pi.get("account_metrics", {}),
                "stale": True
            })
        return jsonify({"success": False, "positions": [], "error": str(e)}), 500


def api_get_portfolio():
    """Debug holdings list"""
    try:
        holdings = quantum_ai.db.get_portfolio()
        return jsonify(holdings)
    except Exception as e:
        logger.error(f"Portfolio List error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

def api_get_portfolio_lots():
    """Return open/all tax lots for one symbol or entire portfolio."""
    try:
        symbol = normalize_symbol(request.args.get("symbol")) if request.args.get("symbol") else None
        only_open = str(request.args.get("only_open", "1")).strip().lower() not in {"0", "false", "no"}
        page = max(1, int(request.args.get("page", 1) or 1))
        page_size = max(10, min(200, int(request.args.get("page_size", 50) or 50)))
        lots = quantum_ai.db.get_portfolio_lots(symbol=symbol, only_open=only_open)
        total = len(lots)
        start = (page - 1) * page_size
        end = start + page_size
        paged = lots[start:end]
        pages = max(1, (total + page_size - 1) // page_size)
        return jsonify({
            "status": "ok",
            "data": paged,
            "count": len(paged),
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages
        })
    except Exception as e:
        logger.error(f"Portfolio lots error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

def api_update_portfolio_lot(lot_id):
    """Update specific open lot (purchase date/price/qty)."""
    try:
        data = validate_lot_update(request.get_json(silent=True))

        result = quantum_ai.db.update_open_lot(
            lot_id=lot_id,
            quantity=data["quantity"],
            buy_price=data["buy_price"],
            buy_date=data["buy_date"]
        )
        trigger_ai_recompute()
        return jsonify({"status": "ok", "data": result})
    except ValidationError as e:
        return jsonify(validation_error_payload(e)), 400
    except Exception as e:
        logger.error(f"Portfolio lot update error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

def api_delete_portfolio_lot(lot_id):
    """Delete one unsold open lot."""
    try:
        result = quantum_ai.db.delete_open_lot(lot_id=lot_id)
        trigger_ai_recompute()
        return jsonify({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Portfolio lot delete error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

def api_get_realized_gains():
    """Return realized gains ledger (STCG/LTCG) from matched sell lots."""
    try:
        symbol = normalize_symbol(request.args.get("symbol")) if request.args.get("symbol") else None
        from_date = request.args.get("from")
        to_date = request.args.get("to")
        limit = max(10, min(500, int(request.args.get("limit", 120) or 120)))
        cursor = request.args.get("cursor")
        rows = quantum_ai.db.get_realized_gains(symbol=symbol, from_date=from_date, to_date=to_date)
        start = 0
        if cursor is not None:
            try:
                start = max(0, int(cursor))
            except Exception:
                start = 0
        end = start + limit
        paged = rows[start:end]
        next_cursor = str(end) if end < len(rows) else None
        return jsonify({
            "status": "ok",
            "data": paged,
            "count": len(paged),
            "total": len(rows),
            "cursor": str(start),
            "next_cursor": next_cursor
        })
    except Exception as e:
        logger.error(f"Realized gains error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

def api_delete_portfolio(symbol):
    """Portfolio REST delete"""
    try:
        base_symbol = normalize_symbol(symbol)
        if not base_symbol:
            return jsonify({"status": "error", "error": "invalid symbol"}), 400

        quantum_ai.db.delete_portfolio_position(base_symbol)
        trigger_ai_recompute()

        return jsonify({"status": "deleted"})
    except Exception as e:
        logger.error(f"Portfolio Delete error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


def api_modify_portfolio(symbol):
    """Portfolio REST modify ?" update qty, price, or date for existing position"""
    try:
        data = validate_portfolio_update(
            request.get_json(silent=True),
            normalize_symbol=normalize_symbol,
            symbol=symbol,
        )
        base_symbol = data["symbol"]
        qty = data["quantity"]
        price = data["avg_price"]
        date = data["purchase_date"]

        # INSERT OR REPLACE keyed on symbol ?" effectively an update
        quantum_ai.db.update_portfolio_position_summary(base_symbol, qty, price, date)
        trigger_ai_recompute()

        return jsonify({"status": "ok", "message": f"{base_symbol} updated"})
    except ValidationError as e:
        return jsonify(validation_error_payload(e)), 400
    except Exception as e:
        logger.error(f"Portfolio Modify error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

def api_sell_portfolio():
    """Sell lots with FIFO/LIFO/HIFO matching and realized gain accounting."""
    try:
        data = validate_sell_order(request.get_json(silent=True), normalize_symbol=normalize_symbol)
        base_symbol = data["symbol"]
        qty = data["quantity"]
        price = data["sell_price"]
        sell_date = data["sell_date"]
        method = data["method"]
        fees = data["fees"]
        notes = data["notes"]

        result = quantum_ai.db.sell_from_portfolio(
            base_symbol,
            qty,
            price,
            sell_date=sell_date,
            method=method,
            fees=fees,
            notes=notes
        )
        journal = {
            "symbol": base_symbol,
            "action": "SELL_EXECUTED",
            "method": method,
            "quantity": qty,
            "sell_price": price,
            "realized_gain": float(result.get("realized_gain", 0) or 0),
            "realized_stcg": float(result.get("realized_stcg", 0) or 0),
            "realized_ltcg": float(result.get("realized_ltcg", 0) or 0),
            "matched_lots": len(result.get("matched_lots", []) or []),
            "timestamp": datetime.now().isoformat()
        }
        trigger_ai_recompute()
        return jsonify({"status": "ok", "data": result, "journal": journal})
    except ValidationError as e:
        return jsonify(validation_error_payload(e)), 400
    except Exception as e:
        logger.error(f"Portfolio Sell error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

def api_sell_simulation():
    """Simulate sell outcomes across FIFO/LIFO/HIFO without mutating holdings."""
    try:
        data = validate_sell_order(request.get_json(silent=True), normalize_symbol=normalize_symbol)
        base_symbol = data["symbol"]
        qty = data["quantity"]
        price = data["sell_price"]
        sell_date = data["sell_date"]
        fees = data["fees"]
        methods = data["methods"]

        result = quantum_ai.db.compare_sell_methods(
            symbol=base_symbol,
            quantity=qty,
            sell_price=price,
            sell_date=sell_date,
            fees=fees,
            methods=methods
        )
        return jsonify({"status": "ok", "data": result})
    except ValidationError as e:
        return jsonify(validation_error_payload(e)), 400
    except Exception as e:
        logger.error(f"Portfolio sell simulation error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

def api_portfolio_tax_summary():
    """Financial year realized STCG/LTCG summary from lot-matched ledger."""
    try:
        fy_start = request.args.get("fy_start")
        fy_start_year = int(fy_start) if fy_start not in (None, "") else None
        summary = quantum_ai.db.get_financial_year_realized_summary(fy_start_year=fy_start_year)
        return jsonify({"status": "ok", "data": summary})
    except Exception as e:
        logger.error(f"Portfolio tax summary error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

def api_portfolio_ltcg_alerts():
    """Lots that are close to LTCG threshold (default <= 30 days)."""
    try:
        symbol = normalize_symbol(request.args.get("symbol")) if request.args.get("symbol") else None
        days = int(request.args.get("days", 30) or 30)
        rows = quantum_ai.db.get_near_ltcg_lots(symbol=symbol, threshold_days=days)
        return jsonify({"status": "ok", "data": rows, "count": len(rows)})
    except Exception as e:
        logger.error(f"Portfolio LTCG alerts error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

def api_portfolio_lot_insights():
    """Compact lot intelligence packet for expander and reports."""
    try:
        symbol = normalize_symbol(request.args.get("symbol")) if request.args.get("symbol") else None
        days = int(request.args.get("days", 45) or 45)
        fy_start = request.args.get("fy_start")
        fy_start_year = int(fy_start) if fy_start not in (None, "") else None

        open_lots = quantum_ai.db.get_portfolio_lots(symbol=symbol, only_open=True)
        all_lots = quantum_ai.db.get_portfolio_lots(symbol=symbol, only_open=False)
        near_ltcg = quantum_ai.db.get_near_ltcg_lots(symbol=symbol, threshold_days=days)
        fy_summary = quantum_ai.db.get_financial_year_realized_summary(fy_start_year=fy_start_year)
        return jsonify({
            "status": "ok",
            "data": {
                "symbol": symbol,
                "open_lots": open_lots,
                "all_lots": all_lots,
                "near_ltcg": near_ltcg,
                "fy_summary": fy_summary
            }
        })
    except Exception as e:
        logger.error(f"Portfolio lot insights error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500



def api_portfolio_forecast():
    """Read-only probabilistic portfolio forecast."""
    try:
        suite = _compute_portfolio_intelligence_suite()
        return jsonify({
            "status": "ok",
            "generated_on": suite.get("generated_on"),
            "generated_at": suite.get("generated_at"),
            "data": suite.get("forecast", {})
        })
    except Exception as e:
        logger.error(f"Portfolio forecast error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


def api_portfolio_survival():
    """Read-only survival stress engine."""
    try:
        suite = _compute_portfolio_intelligence_suite()
        return jsonify({
            "status": "ok",
            "generated_on": suite.get("generated_on"),
            "generated_at": suite.get("generated_at"),
            "data": suite.get("survival", {})
        })
    except Exception as e:
        logger.error(f"Portfolio survival error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


def api_portfolio_intelligence_suite():
    """Read-only suite: forecast + survival + backtesting + drift + governance + explainability."""
    try:
        suite = _compute_portfolio_intelligence_suite()
        return jsonify({"status": "ok", "data": suite})
    except Exception as e:
        logger.error(f"Portfolio intelligence suite error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


def _suite_slice_response(slice_key):
    suite = _compute_portfolio_intelligence_suite()
    return jsonify({
        "status": "ok",
        "generated_on": suite.get("generated_on"),
        "generated_at": suite.get("generated_at"),
        "data": suite.get(slice_key, {})
    })


def api_portfolio_backtesting():
    """Read-only portfolio backtesting diagnostics."""
    try:
        return _suite_slice_response("backtesting")
    except Exception as e:
        logger.error(f"Portfolio backtesting error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


def api_portfolio_drift():
    """Read-only drift detection snapshot."""
    try:
        return _suite_slice_response("drift")
    except Exception as e:
        logger.error(f"Portfolio drift error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


def api_portfolio_governance():
    """Read-only capital governance layer."""
    try:
        return _suite_slice_response("governance")
    except Exception as e:
        logger.error(f"Portfolio governance error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


def api_portfolio_explainability():
    """Read-only explainability layer for portfolio recommendations."""
    try:
        return _suite_slice_response("explainability")
    except Exception as e:
        logger.error(f"Portfolio explainability error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


def api_portfolio_scorecard():
    """Read-only capital intelligence module scorecard."""
    try:
        return _suite_slice_response("scorecard")
    except Exception as e:
        logger.error(f"Portfolio scorecard error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


def api_portfolio_allocation_chart():
    """Portfolio allocation chart data."""
    try:
        holdings = quantum_ai.db.get_portfolio() if getattr(quantum_ai, "db", None) else []
        labels = []
        values = []
        for h in holdings or []:
            symbol = normalize_symbol(h.get("symbol") if isinstance(h, dict) else h["symbol"])
            qty = _safe_float((h.get("quantity") if isinstance(h, dict) else h["quantity"]), 0.0)
            avg_price = _safe_float((h.get("avg_price") if isinstance(h, dict) else h["avg_price"]), 0.0)
            price = MARKET.get_cached_price(symbol) or avg_price
            if symbol and qty > 0 and price > 0:
                labels.append(symbol)
                values.append(round(qty * price, 2))
        return jsonify({"success": True, "data": {"labels": labels, "values": values}})
    except Exception as e:
        logger.error(f"Portfolio allocation chart error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500




ROUTE_SPECS = [
    ("/api/portfolio", "create_portfolio", ["POST"]),
    ("/api/portfolio/add", "create_portfolio_legacy", ["POST"]),
    ("/api/portfolio/state", "api_portfolio_state", ["GET"]),
    ("/api/portfolio", "api_get_portfolio", ["GET"]),
    ("/api/portfolio/lots", "api_get_portfolio_lots", ["GET"]),
    ("/api/portfolio/lots/<int:lot_id>", "api_update_portfolio_lot", ["PUT"]),
    ("/api/portfolio/lots/<int:lot_id>", "api_delete_portfolio_lot", ["DELETE"]),
    ("/api/portfolio/realized-gains", "api_get_realized_gains", ["GET"]),
    ("/api/portfolio/<symbol>", "api_delete_portfolio", ["DELETE"]),
    ("/api/portfolio/<symbol>", "api_modify_portfolio", ["PUT"]),
    ("/api/portfolio/sell", "api_sell_portfolio", ["POST"]),
    ("/api/portfolio/sell/simulate", "api_sell_simulation", ["POST"]),
    ("/api/portfolio/tax-summary", "api_portfolio_tax_summary", ["GET"]),
    ("/api/portfolio/ltcg-alerts", "api_portfolio_ltcg_alerts", ["GET"]),
    ("/api/portfolio/lot-insights", "api_portfolio_lot_insights", ["GET"]),
    ("/api/portfolio/forecast", "api_portfolio_forecast", ["GET"]),
    ("/api/portfolio/survival", "api_portfolio_survival", ["GET"]),
    ("/api/portfolio/intelligence-suite", "api_portfolio_intelligence_suite", ["GET"]),
    ("/api/portfolio/backtesting", "api_portfolio_backtesting", ["GET"]),
    ("/api/portfolio/drift", "api_portfolio_drift", ["GET"]),
    ("/api/portfolio/governance", "api_portfolio_governance", ["GET"]),
    ("/api/portfolio/explainability", "api_portfolio_explainability", ["GET"]),
    ("/api/portfolio/scorecard", "api_portfolio_scorecard", ["GET"]),
    ("/api/portfolio/allocation", "api_portfolio_allocation_chart", ["GET"]),
]

def create_portfolio_blueprint(*, handlers: Mapping[str, object] | None = None) -> Blueprint:
    blueprint = Blueprint("portfolio", __name__)
    handler_map = dict(handlers or {})

    for rule, handler_name, methods in ROUTE_SPECS:
        view_func = handler_map.get(handler_name) or globals()[handler_name]
        blueprint.add_url_rule(
            rule,
            endpoint=handler_name,
            view_func=view_func,
            methods=methods,
        )

    return blueprint
