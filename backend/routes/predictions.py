"""Prediction API routes."""

from __future__ import annotations

from typing import Any, Mapping

from flask import Blueprint, jsonify, request

from backend.services.prediction_service import (
    build_prediction_intelligence_payload,
    build_predictions_payload,
    get_prediction_rows,
)
from utils import encoding


def configure_predictions_runtime(runtime_globals: Mapping[str, Any]) -> None:
    """Expose legacy app dependencies used by prediction handlers."""
    for name, value in runtime_globals.items():
        if not name.startswith("__"):
            globals()[name] = value





# Legacy prediction and execution route handlers.
def get_evolved_prediction_endpoint(symbol):
    """
    Enhanced prediction endpoint using the Integrated Foresight System.
    """
    try:
        # Standardize symbol
        if not any(symbol.endswith(s) for s in ['.NS', '.BO']):
            symbol = symbol + '.NS'
            
        df = quantum_ai.get_live_stock_data(symbol, period='1y')
        if df is None or df.empty:
            return jsonify({'success': False, 'error': f'No data available for {symbol}'}), 404
            
        current_price = float(df['Close'].iloc[-1])
        # ==============================
        # Technical Context (UI ONLY)
        # ==============================

        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = float(rsi.iloc[-1]) if not rsi.empty else None

        exp1 = df['Close'].ewm(span=12).mean()
        exp2 = df['Close'].ewm(span=26).mean()
        macd = exp1 - exp2
        current_macd = float(macd.iloc[-1])

        sma_50 = float(df['Close'].rolling(50).mean().iloc[-1])
        sma_200 = float(df['Close'].rolling(200).mean().iloc[-1]) if len(df) >= 200 else None

        technical_context = {
            "rsi": current_rsi,
            "macd": current_macd,
            "sma_50": sma_50,
            "sma_200": sma_200
        }

        # Get base prediction from existing models
        ai_result = quantum_ai.get_comprehensive_prediction(symbol, df)
        
        # Calculate model agreement (0-1)
        model_agreement = ai_result.get('confidence', 75) / 100
        
        # Base prediction object for the foresight system
        base_prediction = {
            'signal': ai_result.get('signal', 'HOLD'),
            'confidence': ai_result.get('confidence', 75),
            'models_used': ai_result.get('models_used', ['Quantum Ensemble']),
            'price_target': ai_result.get('target_price', current_price)
        }
        
        # o. NEW: Evolve prediction with ALL intelligence layers
        try:
            evolved_prediction = app.foresight_system.generate_evolved_prediction(
                symbol=symbol,
                current_price=current_price,
                historical_data=df,
                base_prediction=base_prediction,
            )
            
            # o. ENFORCEMENT: Prevent partial UI rendering
            if not evolved_prediction or 'futures' not in evolved_prediction:
                logger.warning(f"Intelligence not ready for {symbol}")
                return jsonify({
                    'success': False,
                    'status': 'INTELLIGENCE_NOT_READY',
                    'error': 'Intelligence core is still initializing. Please retry in a moment.'
                }), 503

            evolved_prediction['technical_context'] = technical_context            
            # Add timestamp
            evolved_prediction['timestamp'] = datetime.now(ZoneInfo("UTC")).isoformat()


            return jsonify({
                'success': True,
                'symbol': symbol.replace('.NS', '').replace('.BO', ''),
                **evolved_prediction,
                'timestamp': datetime.now(ZoneInfo("UTC")).isoformat(),
            })

           
        except Exception as e:
            logger.error(f"Intelligence evolution failed: {e}")
            return jsonify({
                'success': False,
                'error': f'Intelligence evolution failed: {str(e)}'
            }), 500
    
    except Exception as e:
        logger.error(f"Evolved prediction error for {symbol}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def live_predictions(symbol):
    """Live predictions with full error handling"""
    try:
        # Ensure .NS suffix
        if not any(symbol.endswith(s) for s in ['.NS', '.BO']):
            symbol = symbol + '.NS'
        
        # Get live data
        df = quantum_ai.get_live_stock_data(symbol, period='1y')
        
        if df is None or df.empty:
            return jsonify({'success': False, 'error': f'No data available for {symbol}'}), 404
        if is_dataframe_synthetic(df):
            return jsonify({'success': False, 'error': f'Live market data unavailable for {symbol}'}), 503
        
        try:
            if len(df) < 2:
                return jsonify({'success': False, 'error': 'Insufficient data'}), 400
            
            current_price = float(df['Close'].iloc[-1])
            
            # Get base AI prediction
            try:
                ai_result = quantum_ai.get_comprehensive_prediction(symbol, df)
            except Exception as e:
                logger.error(f"Prediction failed for {symbol}: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
            
            # Calculate dynamic predictions
            returns = df['Close'].pct_change().dropna()
            if len(returns) < 2:
                volatility = 0.02
                momentum = 0.001
            else:
                volatility = returns.std()
                momentum = returns.tail(20).mean() if len(returns) >= 20 else returns.mean()
            
            # Dynamic horizon synthesis (engine-aware; avoids rigid hardcoded maps)
            horizon_order = [1, 5, 15, 30, 90, 180, 365]
            horizon_labels = {
                1: '1d',
                5: '5d',
                15: '15d',
                30: '1m',
                90: '3m',
                180: '6m',
                365: '1y'
            }

            predictions = {}
            confidences = {}
            
            base_return = ai_result.get('predicted_return', 0) / 100
            base_conf = float(ai_result.get('confidence', 75))
            conf_norm = float(np.clip(base_conf / 100.0, 0.2, 1.0))
            model_bank = ai_result.get('individual_predictions') or ai_result.get('model_predictions') or {}
            engine_depth = max(1, len(model_bank) if isinstance(model_bank, dict) else 1)
            vol_anchor = float(np.clip(volatility, 0.002, 0.12))

            for days in horizon_order:
                period = horizon_labels[days]
                try:
                    phase = np.log1p(days) / np.log(366)
                    horizon_scale = np.sqrt(max(days, 1) / 30.0)
                    engine_boost = 1.0 + (np.log1p(engine_depth) / 6.0)
                    confidence_boost = 0.65 + (0.70 * conf_norm)
                    base_factor = (0.15 + phase) * engine_boost * confidence_boost

                    scaled_return = base_return * base_factor * horizon_scale
                    momentum_impact = momentum * (days / 12.0) * (0.8 + 0.4 * conf_norm)
                    vol_adj = min(0.35, vol_anchor * np.sqrt(max(days, 1) / 30.0) * (0.35 + min(1.0, vol_anchor * 18.0)))

                    total_return = scaled_return + momentum_impact

                    # Regime damping for long horizons in high-variance contexts.
                    damping = 1.0 / (1.0 + phase * 0.55 * max(0.0, (vol_anchor * 14.0) - 0.5))
                    total_return *= damping

                    predicted_price = max(0.01, current_price * (1 + total_return))
                    
                    predictions[period] = {
                        'target_price': round(predicted_price, 2),
                        'return_percent': round(total_return * 100, 2),
                        'price_range_low': round(predicted_price * (1 - vol_adj), 2),
                        'price_range_high': round(predicted_price * (1 + vol_adj), 2)
                    }
                    
                    time_decay = max(0.3, 1.0 - phase * 0.45)
                    vol_impact = max(0.6, 1.0 - vol_anchor * (0.8 + phase))
                    
                    confidences[period] = round(base_conf * time_decay * vol_impact, 1)
                
                except Exception as e:
                    logger.error(f"Timeframe {period} calculation failed: {e}")
                    phase = np.log1p(days) / np.log(366)
                    fallback_band = min(0.12, vol_anchor * (0.8 + phase))
                    predictions[period] = {
                        'target_price': round(current_price, 2),
                        'return_percent': 0,
                        'price_range_low': round(current_price * (1 - fallback_band), 2),
                        'price_range_high': round(current_price * (1 + fallback_band), 2)
                    }
                    confidences[period] = 50.0
            
            return jsonify({
                'success': True,
                'data': {
                    'symbol': symbol.replace('.NS', '').replace('.BO', ''),
                    'current_price': round(current_price, 2),
                    'predictions': predictions,
                    'target_6m': predictions.get('6m', {}).get('target_price'),
                    'target_1y': predictions.get('1y', {}).get('target_price'),
                    'confidences': confidences,
                    'market_conditions': {
                        'momentum': 'Positive' if momentum > 0.001 else 'Negative' if momentum < -0.001 else 'Neutral',
                        'volatility_level': 'High' if volatility > 0.03 else 'Low' if volatility < 0.015 else 'Medium',
                        'trend_strength': min(100, abs(momentum) * 1000)
                    },
                    'timestamp': datetime.now().isoformat()
                }
            })
        
        except Exception as e:
            logger.error(f"Prediction error for {symbol}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    except Exception as e:
        logger.error(f"Live predictions error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def get_governance_decision():
    """
    Get autonomous TRADE/PAUSE decision for prediction.
    
    POST data:
    {
        "symbol": "SBIN",
        "base_prediction": {...},
        "emotional_state": {...},
        "multiworld_stats": {...},
        "model_agreement": 0.85
    }
    """
    
    try:
        data = validate_governance_decision(request.get_json(silent=True), normalize_symbol=normalize_symbol)
    except ValidationError as exc:
        return jsonify(validation_error_payload(exc)), 400
    
    decision = foresight_system.governance_engine.make_governed_decision(
        symbol=data['symbol'],
        base_prediction=data['base_prediction'],
        emotional_state=data['emotional_state'],
        multiworld_stats=data['multiworld_stats'],
        model_agreement=data['model_agreement'],
    )
    
    return jsonify(decision)


def api_confidence_distribution_chart():
    """Prediction confidence histogram for chart.js."""
    try:
        rows = _get_prediction_rows()
        bins = {"0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}
        for row in rows:
            conf = _safe_float(row.get("confidence", row.get("confidence_score", 0)), 0.0)
            if conf <= 20:
                bins["0-20"] += 1
            elif conf <= 40:
                bins["20-40"] += 1
            elif conf <= 60:
                bins["40-60"] += 1
            elif conf <= 80:
                bins["60-80"] += 1
            else:
                bins["80-100"] += 1
        return jsonify({"success": True, "data": {"labels": list(bins.keys()), "values": list(bins.values())}})
    except Exception as e:
        logger.error(f"Confidence distribution chart error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500



def api_learning_stats():
    """Lightweight continuous-learning stats for predictions UI."""
    try:
        engine = learning_engine if LEARNING_AVAILABLE else None
        payload = {
            "success": True,
            "data": {
                "enabled": bool(engine),
                "queue_size": 0,
                "last_update": datetime.now().isoformat(),
            }
        }
        if engine is not None:
            payload["data"]["queue_size"] = int(getattr(engine, "pending_count", 0) or 0)
            payload["data"]["last_update"] = str(getattr(engine, "last_update", payload["data"]["last_update"]))
            avg = getattr(engine, "avg_accuracy", None)
            if avg is not None:
                payload["data"]["avg_accuracy"] = float(avg)
        return jsonify(payload)
    except Exception as e:
        logger.warning(f"Learning stats error: {e}")
        return jsonify({"success": True, "data": {"enabled": False, "queue_size": 0, "last_update": datetime.now().isoformat()}})


def get_model_accuracy():
    """Get real model accuracy from database"""
    try:
        if quantum_ai.db:
            # Get predictions with actual outcomes
            recent_predictions = quantum_ai.db.get_recent_predictions(limit=100)
            
            accurate_count = 0
            total_count = 0
            
            for pred in recent_predictions:
                if pred.get('actual_price') and pred.get('predicted_price'):
                    error = abs((pred['actual_price'] - pred['predicted_price']) / pred['actual_price'])
                    if error < 0.05:  # Within 5% is considered accurate
                        accurate_count += 1
                    total_count += 1
            
            accuracy = (accurate_count / total_count * 100) if total_count > 0 else None
            
            return jsonify({
                'success': True,
                'accuracy': round(accuracy, 1) if accuracy is not None else None,
                'accuracy_basis': 'matured_predictions' if accuracy is not None else 'unavailable_until_matured_predictions_are_evaluated',
                'total_predictions': total_count,
                'accurate_predictions': accurate_count
            })
        else:
            return jsonify({'success': True, 'accuracy': None, 'accuracy_basis': 'unavailable_until_matured_predictions_are_evaluated'})
    except Exception:
        return jsonify({'success': True, 'accuracy': None, 'accuracy_basis': 'unavailable_until_matured_predictions_are_evaluated'})


def get_live_symbol_prediction(symbol):
    """
    Get live condensed prediction for stock list.
    """
    try:
        # Standardize
        if not symbol.endswith(('.NS', '.BO')):
            symbol += '.NS'
            
        # Quick Cache Check (Optional optimization spot)
        
        # Get Data
        df = quantum_ai.get_live_stock_data(symbol, period='6mo')
        if df is None or df.empty:
            return jsonify({'success': False, 'error': 'No data'}), 404
        if is_dataframe_synthetic(df):
            return jsonify({'success': False, 'error': 'Live market data unavailable'}), 503
            
        current_price = float(df['Close'].iloc[-1])
        
        # Generate Quick Projections (Simplified for speed)
        # Using existing Foreseight system logic but purely for fast retrieval
        
        # Calculate Volatility
        returns = df['Close'].pct_change()
        volatility = returns.std() * np.sqrt(252)
        vol_level = "HIGH" if volatility > 0.3 else ("LOW" if volatility < 0.15 else "NORMAL")
        
        # Momentum
        sma20 = df['Close'].rolling(20).mean().iloc[-1]
        momentum = "BULLISH" if current_price > sma20 else "BEARISH"
        
        # Dynamic horizon projections from realized drift + variance (no rigid multipliers)
        horizon_days = {'1d': 1, '15d': 15, '3m': 90, '6m': 180, '1y': 365}
        trend_bias = (current_price - sma20) / max(abs(sma20), 1e-9)
        signal_dir = 1.0 if trend_bias >= 0 else -1.0
        realized = returns.dropna()
        mean_return = float(realized.tail(30).mean()) if len(realized) else 0.0
        vol_annual = max(0.001, float(volatility))
        conf_anchor = max(0.35, min(0.95, 1.0 - (vol_annual * 0.55)))

        predictions = {}
        for key, days in horizon_days.items():
            phase = np.log1p(days) / np.log(366)
            drift_component = mean_return * (1.0 + phase * 1.8)
            vol_component = (vol_annual * np.sqrt(days / 252.0)) * 0.35
            projected_return = (drift_component + (signal_dir * vol_component)) * (0.45 + phase)
            target_price = max(0.01, current_price * (1 + projected_return))
            predictions[key] = {
                'target_price': round(target_price, 2),
                'return_percent': round(projected_return * 100, 2)
            }

        confidences = {
            '15d': int(max(min(conf_anchor * 100 * (0.85 + min(0.35, abs(trend_bias))), 95), 40))
        }
        
        return jsonify({
            'success': True,
            'data': {
                'symbol': symbol,
                'current_price': current_price,
                'predictions': predictions,
                'target_6m': predictions['6m']['target_price'],
                'target_1y': predictions['1y']['target_price'],
                'confidences': confidences,
                'market_conditions': {
                    'momentum': momentum,
                    'volatility_level': vol_level
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Live prediction error {symbol}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



def execute_prediction(symbol):
    """
    INTELLIGENT AI PREDICTION EXECUTION
    Fully Meta-Intelligent | Self-Restrained | Production-Safe
    """
    try:
        data = validate_prediction_execution(request.get_json(silent=True))
        current_price = data["current_price"]
        volume = data["volume"]
        timestamp = data["timestamp"]

        logger.info(f'Y Executing AI prediction for {symbol}...')

        # -------------------------------------------------
        # CLEAN SYMBOL
        # -------------------------------------------------
        symbol_clean = symbol.replace('.NS', '').replace('.BO', '').upper()

        # -------------------------------------------------
        # FETCH HISTORICAL DATA
        # -------------------------------------------------
        try:
            stock_info = yf.Ticker(f'{symbol_clean}.NS')
            hist = stock_info.history(period='1y')
            if hist.empty:
                stock_info = yf.Ticker(f'{symbol_clean}.BO')
                hist = stock_info.history(period='1y')
        except Exception as e:
            logger.error(f'Data fetch failed for {symbol_clean}: {e}')
            return jsonify({'success': False, 'error': 'Data fetch failed'}), 500

        if hist.empty:
            return jsonify({'success': False, 'error': 'No historical data'}), 404

        # -------------------------------------------------
        # META-INTELLIGENCE ?" REGIME MEMORY
        # -------------------------------------------------
        try:
            if (
                hasattr(quantum_ai, "regime_embedding")
                and hasattr(quantum_ai, "regime_memory")
                and quantum_ai.regime_embedding
                and quantum_ai.regime_memory
            ):
                embedding = quantum_ai.regime_embedding.transform(hist)
                quantum_ai.regime_memory.update(embedding)
        except Exception:
            pass

        # -------------------------------------------------
        # FEATURE ENGINEERING
        # -------------------------------------------------
        df = hist.copy()
        df['MA20'] = df['Close'].rolling(20).mean()
        df['MA50'] = df['Close'].rolling(50).mean()
        df['Returns'] = df['Close'].pct_change()
        df['Volatility'] = df['Returns'].rolling(20).std()

        latest = df.iloc[-1]

        features = np.array([
            float(latest['Close']),
            float(latest['MA20']) if not pd.isna(latest['MA20']) else float(latest['Close']),
            float(latest['MA50']) if not pd.isna(latest['MA50']) else float(latest['Close']),
            float(latest['Volatility']) if not pd.isna(latest['Volatility']) else 0.0,
            float(volume) if volume > 0 else 1_000_000
        ]).reshape(1, -1)

        # -------------------------------------------------
        # MODEL EXECUTION
        # -------------------------------------------------
        predictions = {}
        confidences = {}
        models_used = []

        # META-MODEL TRUST
        try:
            learned_weights = (
                quantum_ai.meta_weighter.compute_weights()
                if hasattr(quantum_ai, "meta_weighter") and quantum_ai.meta_weighter
                else {}
            )
        except Exception:
            learned_weights = {}

        # RF
        if hasattr(quantum_ai, 'rf_model') and quantum_ai.rf_model:
            rf_pred = quantum_ai.rf_model.predict(features)[0]
            rf_conf = max(quantum_ai.rf_model.predict_proba(features)[0]) * 100
            predictions['rf'] = rf_pred
            confidences['rf'] = rf_conf
            models_used.append(f'RF({rf_conf:.1f}%)')

        # GB
        if hasattr(quantum_ai, 'gb_model') and quantum_ai.gb_model:
            gb_pred = quantum_ai.gb_model.predict(features)[0]
            gb_conf = max(quantum_ai.gb_model.predict_proba(features)[0]) * 100
            predictions['gb'] = gb_pred
            confidences['gb'] = gb_conf
            models_used.append(f'GB({gb_conf:.1f}%)')

        # ... 3. QUANTUM LSTM PREDICTION ...
        if (
            hasattr(quantum_ai, "model_status")
            and quantum_ai.model_status.get("lstm", {}).get("active")
        ):
            try:
                lstm_result = quantum_ai._quantum_lstm_model.predict(symbol_clean)
                if isinstance(lstm_result, dict):
                    predictions["lstm"] = lstm_result.get("predictions", 0)
                    confidences["lstm"] = lstm_result.get("confidence", 0.6) * 100
                    models_used.append(f"LSTM({confidences['lstm']:.1f}%)")
            except Exception as e:
                quantum_ai.model_status["lstm"]["active"] = False
                quantum_ai.model_status["lstm"]["reason"] = str(e)

        # RISK
        if hasattr(quantum_ai, '_quantum_risk') and quantum_ai._quantum_risk:
            r = quantum_ai._quantum_risk.predict_signal(symbol_clean)
            if isinstance(r, dict):
                predictions['risk'] = r.get('signal', 0)
                confidences['risk'] = r.get('confidence', 0.7) * 100
                models_used.append(f"Risk({confidences['risk']:.1f}%)")

        if not predictions:
            return jsonify({'success': False, 'error': 'No predictions'}), 503

        # -------------------------------------------------
        # META-WEIGHTED CONTINUOUS SCORE (CRITICAL)
        # -------------------------------------------------
        final_score = 0.0
        weight_sum = 0.0
        # -------------------------------------------------
        # EXTENDED TIMEFRAMES (6M, 1Y)
        # -------------------------------------------------
        # 6M/1Y Target Calculation - Dynamic & Robust
        # -------------------------------------------------
        long_term_projection = 0.0
        
        # 1. Try stronger models first
        if 'gb' in predictions and predictions['gb'] != 0:
            long_term_projection = predictions['gb']
        elif 'rf' in predictions and predictions['rf'] != 0:
            long_term_projection = predictions['rf']
        elif 'lstm' in predictions and predictions['lstm'] != 0:
            long_term_projection = predictions['lstm']
        else:
            # 2. Data-driven fallback from realized trend/volatility (no synthetic random drift)
            try:
                if len(hist) >= 60:
                    start_price = hist['Close'].iloc[-60]
                    hist_trend = (current_price - start_price) / max(start_price, 1e-9)
                    long_term_projection = max(min(hist_trend * 0.5, 0.15), -0.05)
                elif len(hist) >= 20:
                    start_price = hist['Close'].iloc[-20]
                    hist_trend = (current_price - start_price) / max(start_price, 1e-9)
                    long_term_projection = max(min(hist_trend * 0.35, 0.10), -0.04)
                else:
                    realized = hist['Close'].pct_change().dropna()
                    mean_drift = float(realized.mean()) if len(realized) else 0.0
                    long_term_projection = max(min(mean_drift * 20.0, 0.08), -0.03)
            except Exception:
                long_term_projection = 0.0
            
        # Add some noise/variance based on volatility so strictly identical stocks don't look hardcoded
        volatility_factor = hist['Close'].pct_change().std() * np.sqrt(252) if len(hist) > 1 else 0.02
        
        # 6M Target (180 days) 
        # Project linear trend + volatility adjustment
        target_6m = current_price * (1 + (long_term_projection * 2.0) + (volatility_factor * 0.1))
        
        # 1Y Target (365 days)
        # Project longer trend + volatility adjustment
        target_1y = current_price * (1 + (long_term_projection * 3.8) + (volatility_factor * 0.2))

        for m, p in predictions.items():
            w = learned_weights.get(m, 1.0)
            final_score += p * w
            weight_sum += w

        if weight_sum > 0:
            final_score /= weight_sum

        # -------------------------------------------------
        # INTELLIGENCE CORE ?" Advanced Reasoning
        # -------------------------------------------------
        regime = INTELLIGENCE_CORE.update_regime(hist)
        weights = INTELLIGENCE_CORE.compute_model_weights()
        uncertainty = INTELLIGENCE_CORE.simulate_worlds(predictions, confidences)
        allow_trade, trade_reason = INTELLIGENCE_CORE.should_trade(predictions)

        # -------------------------------------------------
        # AI SELF-RESTRAINT
        # -------------------------------------------------
        no_trade_reason = trade_reason if not allow_trade else None

        if abs(final_score) < 0.52 and not no_trade_reason:
            no_trade_reason = "Confidence too low"

        # -------------------------------------------------
        # ENSEMBLE SIGNAL (DIRECTION)
        # -------------------------------------------------
        signal_votes = {}
        for s in predictions.values():
            signal_votes[s] = signal_votes.get(s, 0) + 1

        ensemble_signal = max(signal_votes, key=signal_votes.get)

        avg_confidence = np.mean(list(confidences.values()))

        if ensemble_signal > 0:
            ensemble_confidence = max(avg_confidence, 65)
        elif ensemble_signal < 0:
            ensemble_confidence = max(avg_confidence, 65)
        else:
            ensemble_confidence = min(avg_confidence, 55)

        ensemble_confidence = min(max(ensemble_confidence, 0), 95)

        if no_trade_reason:
            ensemble_signal = "NO_TRADE"

        # -------------------------------------------------
        # RESULT OBJECT
        # -------------------------------------------------
        result = {
            'symbol': symbol_clean,
            'signal': ensemble_signal,
            'confidence': round(ensemble_confidence, 1),
            'model_health': quantum_ai.model_status,
            'regime': regime,
            'uncertainty': uncertainty,
            'no_trade_reason': no_trade_reason,
            'intelligence': {
                'regime': regime,
                'uncertainty': uncertainty,
                'weights': weights
            },
            'models_used': models_used,
            'individual_predictions': predictions,
            'individual_confidences': {k: round(v, 1) for k, v in confidences.items()},
            'num_models': len(predictions),
            'timestamp': timestamp,
            'average_model_confidence': round(avg_confidence, 1),
            'price': current_price,
            'name': getattr(stock_info, 'info', {}).get('longName', symbol_clean), # Full Name
            'target_6m': round(target_6m, 2),
            'target_1y': round(target_1y, 2),
            'direction': (
                'UP' if ensemble_signal > 0
                else 'DOWN' if ensemble_signal < 0
                else 'HOLD'
            )
        }

        result = ensure_dict(result)
        result['confidence'] = apply_confidence_decay(symbol_clean, result['confidence'])
        result['confidence'] = apply_capital_weighting(result['confidence'], 100000)
        result['position_size'] = calculate_position_size(symbol_clean, 100000, result['confidence'])

        result['explanation'] = explain_confidence_change(symbol_clean, avg_confidence, result['confidence'])

        if quantum_ai.db:
            quantum_ai.db.log_prediction(result)

        logger.info(f'o. {symbol_clean}: {ensemble_signal} ({ensemble_confidence:.1f}%)')

        return jsonify({'success': True, 'data': result})

    except ValidationError as e:
        return jsonify(validation_error_payload(e)), 400
    except Exception as e:
        logger.error(f'O Prediction error: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


def get_prediction_audit_endpoint(symbol):
    """Get prediction history for a symbol."""
    try:
        limit = request.args.get('limit', 100, type=int)
        audits = get_prediction_audit(symbol, limit=limit)
        return jsonify({'symbol': symbol, 'count': len(audits), 'audits': audits})
    except Exception as e:
        logger.error(f"Error in audit endpoint: {e}")
        return jsonify({'error': str(e)}), 500


def get_symbol_accuracy(symbol):
    """Get historical accuracy for a symbol."""
    try:
        if symbol not in confidence_memory:
            return jsonify({'symbol': symbol, 'status': 'no_data'})
        
        data = confidence_memory[symbol]
        total = int(data.get('total_predictions', data.get('total', 0)) or 0)
        correct = int(data.get('correct_predictions', data.get('correct', 0)) or 0)
        accuracy = (correct / max(1, total)) * 100
        
        return jsonify({
            'symbol': symbol,
            'accuracy': round(accuracy, 2),
            'total': total,
            'correct': correct,
            'last_updated': data.get('last_updated')
        })
    except Exception as e:
        logger.error(f"Error in accuracy endpoint: {e}")
        return jsonify({'error': str(e)}), 500


def submit_feedback_endpoint():
    try:
        data = validate_feedback(request.get_json(silent=True), normalize_symbol=normalize_symbol)
            
        foresight_system.feedback(
            symbol=data["symbol"],
            evolved_prediction=data["evolved_prediction"],
            realized_return=data["realized_return"]
        )
        return jsonify({'success': True, 'message': 'Feedback processed'})
    except ValidationError as e:
        return jsonify(validation_error_payload(e)), 400
    except Exception as e:
        logger.error(f"Feedback failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500





PREDICTION_ROUTE_SPECS = [
    ("/api/evolved-prediction/<symbol>", "get_evolved_prediction_endpoint", ["GET"]),
    ("/api/predictions/live/<symbol>", "live_predictions", ["GET"]),
    ("/api/governance-decision", "get_governance_decision", ["POST"]),
    ("/api/predictions/confidence-distribution", "api_confidence_distribution_chart", ["GET"]),
    ("/api/learning/stats", "api_learning_stats", ["GET"]),
    ("/api/model/accuracy", "get_model_accuracy", ["GET"]),
    ("/api/predictions/quick/<symbol>", "get_live_symbol_prediction", ["GET"]),
    ("/api/execute-prediction/<symbol>", "execute_prediction", ["POST"]),
    ("/api/prediction/audit/<symbol>", "get_prediction_audit_endpoint", ["GET"]),
    ("/api/symbol/accuracy/<symbol>", "get_symbol_accuracy", ["GET"]),
    ("/api/feedback", "submit_feedback_endpoint", ["POST"]),
]

def create_predictions_blueprint(
    *,
    ai_engine_state: Mapping[str, Any],
    state_cache: Mapping[str, Any],
    system_cache: Mapping[str, Any],
    quantum_ai: Any,
    dynamic_db: Any,
    normalize_symbol: Any,
    realtime_state_builder: Any,
    logger: Any,
) -> Blueprint:
    blueprint = Blueprint("predictions", __name__)

    def _prediction_rows(limit: int = 100) -> list[dict[str, Any]]:
        return get_prediction_rows(
            ai_engine_state=ai_engine_state,
            system_cache=system_cache,
            quantum_ai=quantum_ai,
            dynamic_db=dynamic_db,
            logger=logger,
            limit=limit,
        )

    @blueprint.get("/api/predictions")
    def api_predictions():
        """Read-only predictions from global AI state and database fallbacks."""
        payload = build_predictions_payload(
            ai_engine_state=ai_engine_state,
            rows=_prediction_rows(),
        )
        return jsonify(encoding.sanitize_json(payload))

    @blueprint.get("/api/predictions/intelligence")
    def api_predictions_intelligence():
        """Compatibility endpoint for the dashboard intelligence table."""
        try:
            top_n = max(1, min(int(request.args.get("top_n", 100) or 100), 250))
        except (TypeError, ValueError):
            top_n = 100

        payload = build_prediction_intelligence_payload(
            ai_engine_state=ai_engine_state,
            state_cache=state_cache,
            rows=_prediction_rows(limit=top_n),
            top_n=top_n,
            normalize_symbol=normalize_symbol,
            realtime_state_builder=realtime_state_builder,
            logger=logger,
        )
        return jsonify(encoding.sanitize_json(payload))

    for rule, handler_name, methods in PREDICTION_ROUTE_SPECS:
        blueprint.add_url_rule(
            rule,
            endpoint=handler_name,
            view_func=globals()[handler_name],
            methods=methods,
        )

    return blueprint
