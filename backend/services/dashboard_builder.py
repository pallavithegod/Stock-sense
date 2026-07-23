"""Dashboard payload builders extracted from the Flask app.

The module still accepts legacy runtime globals so the current Flask app can be
migrated incrementally without changing endpoint behavior.
"""
from __future__ import annotations

from typing import Any, Mapping


def configure_dashboard_builder_runtime(runtime_globals: Mapping[str, Any]) -> None:
    """Expose app-level dependencies used by the legacy dashboard builder."""
    for name, value in runtime_globals.items():
        if not name.startswith("__"):
            globals()[name] = value


def _safe_float(value, default=0.0):
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)



def _build_dashboard_macro_sections(snapshot):
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    macro_raw = snapshot.get('macro_raw') if isinstance(snapshot.get('macro_raw'), dict) else {}
    live_indices = snapshot.get('indices') if isinstance(snapshot.get('indices'), list) else []

    def _asset(symbol, fallback_name=None):
        row = macro_raw.get(symbol)
        if not isinstance(row, dict):
            return None
        value = _safe_float(row.get('value'))
        change_pct = _safe_float(row.get('change'))
        name = str(row.get('name') or fallback_name or symbol)
        return {
            'symbol': symbol,
            'name': name,
            'value': round(value, 4),
            'change_percent': round(change_pct, 4),
            'change': round(change_pct, 4),
            'trend': row.get('trend'),
            'timestamp': snapshot.get('timestamp'),
        }

    commodities = [
        item for item in [
            _asset('GC=F', 'Gold'),
            _asset('SI=F', 'Silver'),
            _asset('CL=F', 'Crude Oil (WTI)'),
            _asset('BZ=F', 'Brent Crude'),
            _asset('NG=F', 'Natural Gas'),
            _asset('MTF=F', 'Coal'),
        ]
        if item
    ]
    forex = [
        item for item in [
            _asset('USDINR=X', 'USD/INR'),
            _asset('GBPINR=X', 'GBP/INR'),
            _asset('EURINR=X', 'EUR/INR'),
            _asset('EURUSD=X', 'EUR/USD'),
            _asset('GBPUSD=X', 'GBP/USD'),
            _asset('JPY=X', 'USD/JPY'),
        ]
        if item
    ]
    crypto = [
        item for item in [
            _asset('BTC-USD', 'Bitcoin'),
            _asset('ETH-USD', 'Ethereum'),
            _asset('SOL-USD', 'Solana'),
            _asset('BNB-USD', 'BNB'),
            _asset('XRP-USD', 'XRP'),
        ]
        if item
    ]
    interest_rates = [
        item for item in [
            _asset('INR1Y=RR', 'India 1Y Yield'),
            _asset('^IRX', 'US 13W T-Bill'),
        ]
        if item
    ]
    global_sync = [
        item for item in [
            _asset('^GSPC', 'S&P 500'),
            _asset('^IXIC', 'Nasdaq'),
            _asset('^NSEI', 'NIFTY 50'),
        ]
        if item
    ]

    return {
        'live_indices': live_indices,
        'global_sync': global_sync,
        'commodities': commodities,
        'forex': forex,
        'crypto': crypto,
        'interest_rates': interest_rates,
        'macro_watch': list(snapshot.get('macro_watch') or []),
        'details': snapshot.get('economic_indicators') if isinstance(snapshot.get('economic_indicators'), dict) else {},
    }



def _build_dashboard_news_intelligence(snapshot, prediction_rows):
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    prediction_rows = [row for row in (prediction_rows or []) if isinstance(row, dict)]

    with cache_lock:
        perf = dict(STATE_CACHE.get("PREDICTION_STATE", {}).get("system_cache", {}).get("ai_performance", {}) or {})

    cognitive_state = AI_ENGINE_STATE.get("cognitive_state", {}) or {}
    state_market = cognitive_state.get("market_state", {}) if isinstance(cognitive_state.get("market_state"), dict) else {}
    sentiment = cognitive_state.get("market_sentiment", {}) if isinstance(cognitive_state.get("market_sentiment"), dict) else {}

    regime = (
        cognitive_state.get("current_regime")
        or state_market.get("regime")
        or perf.get("regime")
        or "SYNCHRONIZING"
    )
    confidence = _safe_float(
        state_market.get("system_confidence", perf.get("accuracy", 0.0)),
        0.0
    )

    market_context = {
        "market_status": get_market_status("NSE"),
        "live_indices": snapshot.get("indices", []),
        "regime": regime,
    }

    derived = {}
    fs = getattr(app, 'foresight_system', None)
    if fs and hasattr(fs, 'news_ai') and fs.news_ai and sentiment:
        try:
            derived = fs.news_ai._derive_market_intelligence(
                sentiment=sentiment,
                narratives=[],
                market_context=market_context,
                prediction_rows=prediction_rows,
            ) or {}
        except Exception as exc:
            logger.debug(f"[DASHBOARD] News intelligence derivation fallback used: {exc}")

    return {
        "market_regime": str(derived.get("market_regime") or regime or "SYNCHRONIZING").upper(),
        "regime_confidence": round(confidence, 2),
        "market_pressure_index": round(_safe_float(derived.get("market_pressure_index"), 0.0), 4),
        "macro_bias": derived.get("macro_bias"),
        "next_market_event": derived.get("next_market_event"),
        "impact_strength": _safe_float(derived.get("impact_strength"), 0.0),
    }


def _resolve_dashboard_ai_performance(now):
    """Derive dashboard performance from the existing live cache without static defaults."""
    with cache_lock:
        perf = dict(STATE_CACHE.get("PREDICTION_STATE", {}).get("system_cache", {}).get("ai_performance", {}) or {})
        recent_predictions = [
            item for item in (STATE_CACHE.get("PREDICTION_STATE", {}).get("system_cache", {}).get("recent_predictions", []) or [])
            if isinstance(item, dict) and str(item.get("data_source") or "").lower() != "synthetic"
        ]

    confidence_values = [
        _safe_float(item.get("confidence") or (item.get("prediction") or {}).get("confidence"), None)
        for item in recent_predictions
        if isinstance(item, dict)
    ]
    confidence_values = [value for value in confidence_values if value is not None]

    accuracy_percent = _safe_float(perf.get("accuracy"), None)
    if accuracy_percent is None and confidence_values:
        accuracy_percent = round(sum(confidence_values) / len(confidence_values), 2)

    models_active = perf.get("active_models")
    if models_active is None:
        models_active = len(getattr(quantum_ai, "models", {}) or {})

    ai_mode = str(AI_ENGINE_STATE.get("ai_mode") or "").upper()
    system_status = "LIVE" if ai_mode == "LIVE_MODE" else ("WARM" if ai_mode == "WARM_MODE" else "INITIALIZING")

    last_update = AI_ENGINE_STATE.get("last_update")
    if hasattr(last_update, "isoformat"):
        last_update = last_update.isoformat()

    return {
        "accuracy": round(float(accuracy_percent), 2) if accuracy_percent is not None else None,
        "accuracy_percent": round(float(accuracy_percent), 2) if accuracy_percent is not None else None,
        "prediction_accuracy": round(float(accuracy_percent), 2) if accuracy_percent is not None else None,
        "models_active": int(models_active or 0),
        "active_models": int(models_active or 0),
        "data_points": len(recent_predictions),
        "data_points_min": len(recent_predictions),
        "data_points_per_minute": len(recent_predictions),
        "system_status": system_status,
        "last_sync": perf.get("last_updated") or last_update or now.isoformat(),
    }



def _get_prediction_rows(limit=100):
    """Compatibility adapter for legacy dashboard/chart helpers."""
    return collect_prediction_rows(
        ai_engine_state=AI_ENGINE_STATE,
        system_cache=system_cache,
        quantum_ai=quantum_ai,
        dynamic_db=dynamic_db,
        logger=logger,
        limit=limit,
    )



def _derive_dashboard_liquidity_score(*, indices=None, top_stocks=None, performance=None):
    """Build a 0-100 liquidity proxy from dashboard market movement when no service value exists."""
    performance = performance if isinstance(performance, dict) else {}
    existing = _safe_float(
        performance.get("liquidity_score", performance.get("liquidityScore")),
        None,
    )
    if existing is not None:
        return round(max(0.0, min(100.0, existing)), 2)

    market_rows = []
    for collection in (indices, top_stocks):
        if isinstance(collection, list):
            market_rows.extend(item for item in collection if isinstance(item, dict))

    change_values = [
        abs(_safe_float(
            item.get("change_percent", item.get("changePercent", item.get("percent"))),
            0.0,
        ))
        for item in market_rows
    ]
    change_values = [value for value in change_values if value > 0]

    if not change_values:
        return 50.0

    avg_move = min(float(np.mean(change_values)), 5.0)
    coverage_bonus = min(len(change_values) * 2.5, 20.0)
    stability_score = max(0.0, 80.0 - (avg_move * 10.0))
    return round(max(0.0, min(100.0, stability_score + coverage_bonus)), 2)



def _build_dashboard_top_stocks(snapshot, prediction_rows, limit=10):
    """Build dashboard recommendations from live prediction rows, with dynamic market fallbacks only."""
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    macro_raw = snapshot.get("macro_raw") if isinstance(snapshot.get("macro_raw"), dict) else {}
    last_price_map = AI_ENGINE_STATE.get("last_market_price_map", {}) or {}

    rows = [row for row in (prediction_rows or []) if isinstance(row, dict)]
    rows.sort(
        key=lambda row: _safe_float(
            row.get("confidence") or (row.get("prediction") or {}).get("confidence"),
            -1.0
        ),
        reverse=True
    )

    top_stocks = []
    seen = set()

    for row in rows:
        if len(top_stocks) >= limit:
            break

        symbol = row.get("symbol")
        base = normalize_symbol(symbol)
        if not base or base in seen:
            continue

        price = _safe_float(row.get("current_price") or row.get("price"), None)
        if price is None:
            price = _safe_float((macro_raw.get(f"{base}.NS") or macro_raw.get(f"{base}.BO") or {}).get("value"), None)
        if price is None:
            price = _safe_float(last_price_map.get(base), None)

        change = _safe_float(
            row.get("price_change_percent")
            or row.get("change_percent")
            or row.get("change_pct")
            or row.get("predicted_return"),
            None
        )
        confidence = _safe_float(row.get("confidence") or (row.get("prediction") or {}).get("confidence"), None)
        signal = row.get("signal") or (row.get("prediction") or {}).get("signal")

        top_stocks.append({
            "symbol": base,
            "name": row.get("name") or row.get("company_name") or base,
            "exchange": row.get("exchange") or row.get("market") or "NSE",
            "current_price": price,
            "price_change_percent": change,
            "signal": signal,
            "confidence": confidence,
            "target_price": _safe_float(row.get("target_price") or (row.get("prediction") or {}).get("target_price"), None),
            "allocation_pct": _safe_float(row.get("allocation_pct") or row.get("allocation"), None),
            "volume": _safe_float(row.get("volume"), None),
        })
        seen.add(base)

    if top_stocks:
        return top_stocks

    try:
        dynamic_symbols = quantum_ai.get_top_active_stocks(limit) or []
    except Exception:
        dynamic_symbols = []

    for symbol in dynamic_symbols:
        if len(top_stocks) >= limit:
            break
        base = normalize_symbol(symbol)
        if not base or base in seen:
            continue
        raw = macro_raw.get(f"{base}.NS") or macro_raw.get(f"{base}.BO") or {}
        price = _safe_float(raw.get("value"), None)
        if price is None:
            price = _safe_float(last_price_map.get(base), None)
        top_stocks.append({
            "symbol": base,
            "name": base,
            "exchange": "NSE",
            "current_price": price,
            "price_change_percent": _safe_float(raw.get("change"), None),
            "signal": None,
            "confidence": None,
            "target_price": None,
            "allocation_pct": None,
            "volume": _safe_float(raw.get("volume"), None),
        })
        seen.add(base)

    return top_stocks


def get_dashboard_data():
    """
    QuantumAI NEXUS Reactive Dashboard API (V12 - SNAPSHOT BASED)
    A'A+?TA?sA,A_A'A,A?sA,AA'A,A?sA,Ao. Zero Network I/O in request thread
    A'A+?TA?sA,A_A'A,A?sA,AA'A,A?sA,Ao. Instant sub-50ms response
    A'A+?TA?sA,A_A'A,A?sA,AA'A,A?sA,Ao. Backed by background Global Market Monitor
    """
    request_started_at = time.perf_counter()
    try:
        # STEP 1: LOAD FROM SNAPSHOT
        with cache_lock:
            snapshot = STATE_CACHE["MARKET_STATE"].get("dashboard_snapshot")
            
        # STEP 2: EMERGENCY REFRESH (Only if server just booted and monitor hasn't run)
        if not snapshot:
            logger.info("[DASHBOARD] Snapshot missing (Cold Boot) - Performing emergency refresh...")
            _refresh_market_snapshot()
            with cache_lock:
                snapshot = STATE_CACHE["MARKET_STATE"].get("dashboard_snapshot")

        if not snapshot:
            return jsonify({'success': False, 'error': 'Snapshot unavailable'}), 503

        # STEP 3: DYNAMIC ENRICHMENT (Lightweight, non-blocking)
        now = datetime.now()
        market_status = get_market_status("NSE")

        with cache_lock:
            portfolio_state = dict(STATE_CACHE.get("PORTFOLIO_STATE", {}) or {})
            pred_state = list(STATE_CACHE.get("PREDICTION_STATE", {}).get("system_cache", {}).get("recent_predictions", []) or [])
        try:
            portfolio_intelligence = _get_portfolio_intelligence_payload() or {}
            if isinstance(portfolio_intelligence, dict):
                portfolio_state = portfolio_intelligence
        except Exception as portfolio_err:
            logger.warning(f"[DASHBOARD] Portfolio state refresh failed: {portfolio_err}")
            portfolio_intelligence = portfolio_state if isinstance(portfolio_state, dict) else {}
        if not isinstance(portfolio_state, dict):
            portfolio_state = {}
        portfolio_metrics = portfolio_state.get('account_metrics') if isinstance(portfolio_state.get('account_metrics'), dict) else {}
        portfolio_positions = portfolio_state.get('positions') if isinstance(portfolio_state.get('positions'), list) else []
        positions_value = sum(
            _safe_float(
                position.get('current_value', position.get('market_value', position.get('value'))),
                0.0,
            )
            for position in portfolio_positions
            if isinstance(position, dict)
        )
        portfolio_value = next(
            (
                value for value in [
                    portfolio_metrics.get('total_value'),
                    portfolio_metrics.get('portfolio_value'),
                    portfolio_metrics.get('current_value'),
                    portfolio_metrics.get('market_value'),
                    portfolio_state.get('total_value'),
                    portfolio_state.get('portfolio_value'),
                    positions_value if positions_value > 0 else None,
                ]
                if value not in (None, '')
            ),
            0,
        )

        prediction_rows = _get_prediction_rows()
        ai_performance = _resolve_dashboard_ai_performance(now)
        top_stocks = _build_dashboard_top_stocks(snapshot, prediction_rows, limit=10)
        liquidity_score = _derive_dashboard_liquidity_score(
            indices=snapshot.get('indices') if isinstance(snapshot, dict) else [],
            top_stocks=top_stocks,
            performance=ai_performance,
        )
        ai_performance['liquidity_score'] = liquidity_score
        ai_performance['liquidityScore'] = liquidity_score

        macro_sections = _build_dashboard_macro_sections(snapshot)
        news_intelligence = _build_dashboard_news_intelligence(snapshot, prediction_rows or pred_state)

        # 3C. Sentiment (Simplified consensus)
        macro_raw = snapshot.get('macro_raw') if isinstance(snapshot.get('macro_raw'), dict) else {}
        vix_val = _safe_float((macro_raw.get('^VIX') or {}).get('value'), 0.0)
        sentiment_label = "NEUTRAL"
        if vix_val < 13: sentiment_label = "RISK-ON"
        elif vix_val > 20: sentiment_label = "RISK-OFF"

        # Assemble Final Response
        response_data = {
            'success': True,
            'timestamp': now.isoformat(),
            'portfolio_value': portfolio_value,
            'portfolioValue': portfolio_value,
            'active_positions': len(portfolio_positions),
            'activePositions': len(portfolio_positions),
            'liquidity_score': liquidity_score,
            'liquidityScore': liquidity_score,
            'live_indices': snapshot['indices'],
            'market_status': market_status,
            'top_stocks': top_stocks,
            'topStocks': top_stocks,
            'stocks': prediction_rows[:100],
            'predictions': prediction_rows[:100],
            'ai_performance': ai_performance,
            'aiPerformance': ai_performance,
            'ai_engine': dict(AI_ENGINE_STATE.get("cognitive_state", {}) or {}),
            'cognitive_state': dict(AI_ENGINE_STATE.get("cognitive_state", {}) or {}),
            'news_intelligence': news_intelligence,
            'PORTFOLIO_STATE': portfolio_state,
            'portfolio_intelligence': portfolio_state,
            'portfolio_metrics': portfolio_metrics,
            'portfolioMetrics': portfolio_metrics,
            'positions': portfolio_positions,
            'signal_quality': {
                'liquidity_score': liquidity_score,
                'liquidityScore': liquidity_score,
                'directional_accuracy': ai_performance.get('accuracy'),
                'directionalAccuracy': ai_performance.get('accuracy'),
            },
            'signalQuality': {
                'liquidity_score': liquidity_score,
                'liquidityScore': liquidity_score,
                'directional_accuracy': ai_performance.get('accuracy'),
                'directionalAccuracy': ai_performance.get('accuracy'),
            },
            'data': {
                'live_indices': snapshot['indices'],
                'market_status': market_status,
                'top_stocks': top_stocks,
                'stocks': prediction_rows[:100],
                'predictions': prediction_rows[:100],
                'ai_performance': ai_performance,
                'ai_engine': dict(AI_ENGINE_STATE.get("cognitive_state", {}) or {}),
                'cognitive_state': dict(AI_ENGINE_STATE.get("cognitive_state", {}) or {}),
                'news_intelligence': news_intelligence,
                'market_sentiment': {
                    'vix': round(vix_val, 2),
                    'label': sentiment_label
                },
                'MARKET_STATE': snapshot,
                'PORTFOLIO_STATE': portfolio_state,
                'portfolio_intelligence': portfolio_state,
                'portfolio_metrics': portfolio_metrics,
                'portfolioMetrics': portfolio_metrics,
                'positions': portfolio_positions,
                'portfolio_value': portfolio_value,
                'portfolioValue': portfolio_value,
                'active_positions': len(portfolio_positions),
                'activePositions': len(portfolio_positions),
                'liquidity_score': liquidity_score,
                'liquidityScore': liquidity_score,
                'signal_quality': {
                    'liquidity_score': liquidity_score,
                    'liquidityScore': liquidity_score,
                    'directional_accuracy': ai_performance.get('accuracy'),
                    'directionalAccuracy': ai_performance.get('accuracy'),
                },
                'signalQuality': {
                    'liquidity_score': liquidity_score,
                    'liquidityScore': liquidity_score,
                    'directional_accuracy': ai_performance.get('accuracy'),
                    'directionalAccuracy': ai_performance.get('accuracy'),
                },
                'system_health': {'status': 'ONLINE', 'api_status': 'REACTIVE'},
                'macro': macro_sections,
                'metadata': {
                    'data_freshness': snapshot['timestamp'],
                    'latency_ms': round((time.perf_counter() - request_started_at) * 1000, 2),
                    'architecture': 'REACTIVE_SNAPSHOT_V12'
                }
            }
        }

        return jsonify(encoding.sanitize_json(response_data))

    except Exception as e:
        logger.error(f"[DASHBOARD] API Error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


