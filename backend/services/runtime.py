"""Runtime service orchestration for background workers and live caches."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping
from zoneinfo import ZoneInfo
import threading
import time

from websocket_manager import WebSocketManager, LiveDataProvider

_runtime_globals: dict[str, Any] = {}
runtime_bootstrap_lock = threading.Lock()


def configure_runtime(runtime_globals: Mapping[str, Any]) -> None:
    """Expose app-level dependencies used by legacy runtime workers."""
    _runtime_globals.clear()
    _runtime_globals.update(dict(runtime_globals))
    for name, value in runtime_globals.items():
        if not name.startswith("__"):
            globals()[name] = value


def build_websocket_manager() -> Any:
    """Create the live WebSocket manager using the extracted snapshot provider."""
    return WebSocketManager(LiveDataProvider(live_dashboard_snapshot))


def live_dashboard_snapshot():
    """Real-time data snapshot for WebSocket stream"""
    try:
        global AI_ENGINE_STATE
        with cache_lock:
            dash = STATE_CACHE.get("MARKET_STATE", {}).get("dashboard_cache", {}).get("data") or {}
            health = dict(STATE_CACHE.get("SYSTEM_HEALTH", {}))
            risk_state = dict(STATE_CACHE.get("RISK_STATE", {}))
            cached_pi = STATE_CACHE.get("PORTFOLIO_STATE", {}).get("portfolio_intelligence") or {}

        dash_data = dash.get("data", {}) if isinstance(dash, dict) else {}
        indices = dash_data.get("live_indices") if isinstance(dash_data, dict) else None
        if not isinstance(indices, list) or not indices:
            indices = fetch_live_indices() if 'fetch_live_indices' in globals() else []

        ai_state = AI_ENGINE_STATE.get("cognitive_state", {}) or {}
        if isinstance(cached_pi, dict) and cached_pi.get("positions") is not None:
            ai_state = dict(ai_state)
            ai_state["portfolio_intelligence"] = cached_pi

        return {
            "live_indices": indices,
            "market_status": get_market_status("NSE") if 'get_market_status' in globals() else "CLOSED",
            "ai_state": ai_state, # Unified State
            "system_health": health,
            "risk_state": risk_state,
            "timestamp": datetime.now(ZoneInfo("UTC")).isoformat()
        }
    except Exception as e:
        if 'logger' in globals(): logger.error(f"Dashboard snapshot error: {e}")
        return {'error': str(e), 'timestamp': datetime.now(ZoneInfo("UTC")).isoformat()}

def connect_portfolio_manager_adapters():
    """Bind portfolio adapters to the shared AI engine once the app is live."""
    try:
        portfolio_manager.db = quantum_ai.db
        portfolio_manager.market = quantum_ai
        logger.info("[OK] Portfolio manager connected to quantum_ai")
    except Exception as exc:
        logger.warning(f"Portfolio manager adapter connection failed: {exc}")



def run_sentiment_pulse():
    """Background loop for sentiment pulse."""
    logger.info("[PULSE] Neural Sentiment Pulse - INITIALIZING...")
    while True:
        try:
            with app.app_context():
                fs = getattr(app, 'foresight_system', None)
                if fs and hasattr(fs, 'news_ai'):
                    s = fs.news_ai.get_market_sentiment_analysis()
                    socketio.emit("sentiment_pulse", {
                        "overall_score": s["overall_score"],
                        "confidence": s["confidence"],
                        "label": s["label"],
                        "total_articles": s["total_articles"]
                    })
        except Exception as exc:
            logger.error(f"O Sentiment pulse failed: {exc}")
        socketio.sleep(15)



def ensure_runtime_services_started():
    """Start live runtime producers even when the app is imported by a WSGI server."""
    if getattr(app, "_runtime_services_started", False):
        return

    with runtime_bootstrap_lock:
        if getattr(app, "_runtime_services_started", False):
            return

        ensure_market_universe_loaded()

        if not hasattr(app, "loop_start_time"):
            app.loop_start_time = time.time()

        if not getattr(app, "_market_monitor_started", False):
            logger.info("[STARTUP] Launching Global Market Monitor...")
            threading.Thread(target=continuous_market_monitor_loop, daemon=True).start()
            app._market_monitor_started = True

        if not getattr(app, "_preload_started", False):
            preload_default_stocks()
            app._preload_started = True

        connect_portfolio_manager_adapters()

        if not getattr(app, "_intelligence_loop_started", False):
            threading.Thread(target=continuous_intelligence_loop, daemon=True).start()
            app._intelligence_loop_started = True
            logger.info("o. Continuous intelligence loop started")

        try:
            global ws_manager
            if not getattr(app, "_pulse_started", False):
                socketio.start_background_task(run_sentiment_pulse)
                app._pulse_started = True

            if ws_manager is None:
                ws_manager = WebSocketManager(LiveDataProvider(live_dashboard_snapshot), socketio=socketio)

            ws_manager.socketio = socketio
            ws_manager.state_cache = STATE_CACHE
            ws_manager.portfolio_manager = portfolio_manager

            if not getattr(app, "_ws_manager_started", False):
                ws_manager.start()
                app._ws_manager_started = True
                logger.info("[WS] WebSocket Manager attached to SocketIO & Portfolio")
        except Exception as exc:
            logger.error(f"O Failed to start WebSocket Manager: {exc}")

        app._runtime_services_started = True
        logger.info("[STARTUP] Runtime services ready")


def _refresh_market_snapshot():
    """
    Background worker that refreshes all macro, index, and drivers.
    Uses yf.download for high-performance batch fetching.
    """
    try:
        now = datetime.now()
        index_symbols = get_dynamic_index_symbols()
        # One shared market snapshot powers every dashboard macro card.  The
        # instrument catalogue is declarative metadata (not market values);
        # prices and moves below are always obtained from the provider.
        macro_symbols = {
            'GC=F': 'Gold', 'SI=F': 'Silver', 'NG=F': 'Natural Gas',
            'CL=F': 'Crude Oil (WTI)', 'BZ=F': 'Brent Crude', 'MTF=F': 'Coal',
            'USDINR=X': 'USD/INR', 'GBPINR=X': 'GBP/INR', 'EURINR=X': 'EUR/INR',
            'EURUSD=X': 'EUR/USD', 'GBPUSD=X': 'GBP/USD', 'JPY=X': 'USD/JPY', '^GSPC': 'S&P 500',
            '^IXIC': 'Nasdaq', '^DJI': 'DOW JONES', '^VIX': 'VIX', '^IRX': 'US 13W T-Bill',
            '^NSEI': 'NIFTY 50', '^NSEBANK': 'BANK NIFTY', '^BSESN': 'SENSEX',
            '^CNXINFRA': 'Growth Proxy (Infra)', 'INR1Y=RR': 'India 1Y Yield',
            'BTC-USD': 'Bitcoin', 'ETH-USD': 'Ethereum', 'SOL-USD': 'Solana',
            'BNB-USD': 'BNB', 'XRP-USD': 'XRP'
        }
        
        all_syms = list(index_symbols.keys()) + list(macro_symbols.keys())
        data = yf.download(all_syms, period='5d', interval='1d', group_by='ticker', threads=True, progress=False)
        
        macro_results = {}
        indices_data = []
        
        for sym in all_syms:
            try:
                df = data[sym] if len(all_syms) > 1 else data
                df = df.dropna(subset=['Close'])
                if df.empty: continue
                
                val = float(df['Close'].iloc[-1])
                prev = float(df['Close'].iloc[-2]) if len(df) > 1 else val
                chg = ((val - prev) / prev * 100) if prev else 0
                mean_20 = float(df['Close'].tail(20).mean()) if len(df) > 1 else val
                
                res = {'symbol': sym, 'name': macro_symbols.get(sym, sym), 'value': val, 'change': chg, 'trend': "UP" if val > mean_20 else "DOWN"}
                macro_results[sym] = res
                
                if sym in index_symbols:
                    indices_data.append({
                        'name': index_symbols[sym], 'symbol': sym, 'value': round(val, 2),
                        'change_points': round(val - prev, 2), 'change_percent': round(chg, 2),
                        'status': 'positive' if chg >= 0 else 'negative', 'timestamp': now.isoformat(),
                        'source': 'yfinance-batch-snapshot'
                    })
            except: continue

        # Backfill any missing key indices from the existing individual live-index fetcher.
        try:
            tracked_indices = get_dynamic_index_symbols() or {}
            if tracked_indices:
                existing_symbols = {
                    normalize_market_asset_key(item.get('symbol'))
                    for item in indices_data
                    if isinstance(item, dict) and item.get('symbol')
                }
                live_index_rows = fetch_live_indices() if 'fetch_live_indices' in globals() else []
                live_index_map = {
                    normalize_market_asset_key(item.get('symbol')): item
                    for item in live_index_rows
                    if isinstance(item, dict) and item.get('symbol')
                }
                for idx_symbol, idx_name in tracked_indices.items():
                    base = normalize_market_asset_key(idx_symbol)
                    if not base or base in existing_symbols:
                        continue
                    fallback = live_index_map.get(base)
                    if not fallback:
                        continue
                    indices_data.append({
                        'name': fallback.get('name', idx_name),
                        'symbol': fallback.get('symbol', idx_symbol),
                        'value': round(_safe_float(fallback.get('value')), 2),
                        'change_points': round(_safe_float(fallback.get('change_points', fallback.get('changepoints'))), 2),
                        'change_percent': round(_safe_float(fallback.get('change_percent', fallback.get('changepercent', fallback.get('change')))), 2),
                        'status': fallback.get('status', 'neutral'),
                        'timestamp': fallback.get('timestamp', now.isoformat()),
                        'source': fallback.get('source', 'yfinance-individual-fallback')
                    })
        except Exception as exc:
            logger.debug(f"[MONITOR] Index backfill skipped: {exc}")

        if not indices_data:
            logger.warning("[MONITOR] No provider index data available; using local fallback indices")
            fallback_config = [
                {'symbol': symbol, 'name': name}
                for symbol, name in (index_symbols or {}).items()
            ]
            indices_data = _dashboard_index_fallback_rows(
                fallback_config,
                now=now.replace(tzinfo=ZoneInfo("UTC")) if now.tzinfo is None else now,
                reason="snapshot-provider-empty",
            )

        economic_indicators = fetch_india_economic_indicators()
        macro_watch = []
        cpi = economic_indicators.get('inflation', 4.85)
        oil_val = macro_results.get('CL=F', {}).get('value', 80)
        inf_state = "↑ Sticky" if (cpi > 5.5 or oil_val > 85) else ("Cooling" if cpi < 3.5 else "Neutral")
        macro_watch.append(f"Inflation {inf_state}")
        
        infra_chg = macro_results.get('^CNXINFRA', {}).get('change', 0)
        nifty_chg = macro_results.get('^NSEI', {}).get('change', 0)
        grow_state = "Expansion" if (infra_chg - nifty_chg) > 0.8 else ("Contraction" if (infra_chg - nifty_chg) < -0.8 else "Steady")
        macro_watch.append(f"GDP {grow_state}")
        
        rate_val = macro_results.get('INR1Y=RR', {}).get('value', 7.1)
        rate_trend = macro_results.get('INR1Y=RR', {}).get('trend', 'DOWN')
        rate_state = "Tight" if (rate_val > 7.25 or rate_trend == "UP") else ("Ample" if rate_val < 6.9 else "Neutral")
        macro_watch.append(f"1 Year Interest Rate {rate_state}")

        snapshot = {
            'indices': indices_data,
            'macro_watch': macro_watch,
            'macro_raw': macro_results,
            'economic_indicators': economic_indicators,
            'timestamp': now.isoformat()
        }
        
        with cache_lock:
            STATE_CACHE["MARKET_STATE"]["dashboard_snapshot"] = snapshot
            STATE_CACHE["MARKET_STATE"]["snapshot_timestamp"] = now
        
        logger.info(f"[MONITOR] Market snapshot refreshed: {len(indices_data)} indices")
    except Exception as e:
        logger.error(f"[MONITOR] Snapshot refresh failed: {e}")



def continuous_market_monitor_loop():
    """Background loop for market pulse monitoring"""
    logger.info("[MONITOR] Initializing Global Market Monitor...")
    _refresh_market_snapshot()
    while True:
        try:
            time.sleep(180) 
            _refresh_market_snapshot()
        except Exception as e:
            logger.error(f"[MONITOR] Loop error: {e}")
            time.sleep(30)



def preload_default_stocks():
    """Load default stocks in background thread ?" NO blocking startup"""
    symbols = quantum_ai.get_top_active_stocks(5)

    def background_load():
        logger.info("Y"" Background pre-loading stocks...")
        for sym in symbols:
            try:
                df = quantum_ai.get_live_stock_data(sym, period='1y')
                if df is not None:
                    pred = quantum_ai.get_comprehensive_prediction(sym, df)
                    logger.info(f"o. Pre-loaded {sym}: {pred.get('signal', '?')} ({pred.get('confidence', 0):.1f}%)")
            except Exception as e:
                logger.warning(f"Preload skipped for {sym}: {e}")
        logger.info("o. Background pre-load complete")

    threading.Thread(target=background_load, daemon=True).start()
