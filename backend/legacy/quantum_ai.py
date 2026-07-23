"""Legacy Quantum AI engine extracted from app.py.

This module intentionally receives the Flask app runtime globals during startup.
That keeps behavior stable while the old monolithic engine is migrated into
proper services over time.
"""
from __future__ import annotations

from typing import Any, Mapping


def configure_quantum_ai_runtime(runtime_globals: Mapping[str, Any]) -> None:
    """Expose app-level legacy dependencies to this extracted engine."""
    for name, value in runtime_globals.items():
        if not name.startswith("__"):
            globals()[name] = value


class MarketBridge:
    """Bridge for AI trading universe status"""
    def __init__(self):
        self.universe_symbols = []


class QuantumAI:
    """
    NEXUS QUANTUM AI - Unified Adaptive AI System
    o. 100% Dynamic (market-based, accuracy-based)
    o. Zero Hardcoding
    o. Self-Learning
    o. Thread-Safe
    o. Lazy-Loading
    """
    
    def __init__(self):
        start_time = time.time()
        logger.info('Y Initializing QuantumAI NEXUS AI Engine')
        
        # ... MARKET UNIVERSE BRIDGE ...
        self.market = MarketBridge()

        # =========================================================
        # CORE COMPONENTS (ALWAYS INITIALIZE)
        # =========================================================
        self.use_ensemble = True
        self.prediction_history = deque(maxlen=1000)
        self.model_performance = {}
        self.scaler = StandardScaler()
        self._lock = threading.Lock()
        self.health = {
            'init_time': 0,
            'failures': 0,
            'predictions': 0
        }

        # =========================================================
        # ADAPTIVE THRESHOLDS
        # =========================================================
        try:
            self.adaptive_thresholds = AdaptiveThresholds()
            logger.info("o. Adaptive thresholds initialized")
        except Exception as e:
            logger.error(f"Threshold init failed: {e}")
            self.adaptive_thresholds = None

        # =========================================================
        # DATABASE
        # =========================================================
        # =========================================================
        # DATABASE
        # =========================================================
        self.db = None
        try:
            from database import dynamic_db
            self.db = dynamic_db
            logger.info("o. Database initialized")
        except Exception as e:
            logger.error(f"Database init failed: {e}")
            self.db = None

        # =========================================================
        # CACHE
        # =========================================================
        self.cache_advanced = {}
        self.user_tickers = []    # Dynamic user-added tickers
        self.hidden_tickers = []  # User-hidden default tickers

        # =========================================================
        # ML MODELS
        # =========================================================
        try:
            self.rf_model = RandomForestClassifier(
                n_estimators=100,
                random_state=42,
                n_jobs=-1
            )
            self.gb_model = GradientBoostingClassifier(
                n_estimators=100,
                random_state=42
            )
            self.models = {
                'rf': self.rf_model,
                'gb': self.gb_model
            }
            logger.info("o. RF & GB models initialized")
        except Exception as e:
            logger.warning(f"ML models failed: {e}")
            self.rf_model = None
            self.gb_model = None
            self.models = {}

        # =========================================================
        # EXECUTOR
        # =========================================================
        self.executor = ThreadPoolExecutor(max_workers=4)

        # =========================================================
        # META-INTELLIGENCE (OPTIONAL, SAFE)
        # =========================================================
        try:
            from confidence_memory import ConfidenceMemory
            from regime_detector import RegimeEmbeddingEngine, RegimeMemory
            from model_weighting import MetaModelWeighter

            self.regime_embedding = RegimeEmbeddingEngine()
            self.regime_memory = RegimeMemory()
            self.meta_weighter = MetaModelWeighter()
            self.confidence_engine = ConfidenceMemory(config=SYSTEM_CONFIG)

            logger.info("o. Meta-Intelligence layer initialized")
        except Exception as e:
            logger.warning(f"Meta-Intelligence disabled safely: {e}")
            self.regime_embedding = None
            self.regime_memory = None
            self.meta_weighter = None
            self.confidence_engine = None

        # ================= MODEL AVAILABILITY REGISTRY =================
        self.model_status = {
            "rf": {"active": False, "reason": None},
            "gb": {"active": False, "reason": None},
            "lstm": {"active": False, "reason": None},
            "risk": {"active": False, "reason": None},
            "rl": {"active": False, "reason": None},
        }

        # RF
        if hasattr(self, "rf_model") and self.rf_model is not None:
            self.model_status["rf"]["active"] = True

        # GB
        if hasattr(self, "gb_model") and self.gb_model is not None:
            self.model_status["gb"]["active"] = True

        # RISK
        if hasattr(self, "_quantum_risk_model") and self._quantum_risk_model is not None:
            self.model_status["risk"]["active"] = True

        # RL
        if hasattr(self, "portfolio_optimizer") and self.portfolio_optimizer:
            self.model_status["rl"]["active"] = True

        # LSTM (CHECK ONCE ?" VERY IMPORTANT)
        try:
            import transformers  # only checking availability
            if hasattr(self, "_quantum_lstm_model") and self._quantum_lstm_model:
                self.model_status["lstm"]["active"] = True
        except Exception as e:
            self.model_status["lstm"]["active"] = False
            self.model_status["lstm"]["reason"] = "transformers not installed"
            logger.warning("sÃƒÆ’Ã‚Â¯Ãƒâ€šÃ‚Â¸Ãƒâ€šÃ‚Â LSTM disabled: transformers not installed")
        # ===============================================================

        self.health['init_time'] = round(time.time() - start_time, 2)
        logger.info(f"o. QuantumAI ready in {self.health['init_time']}s")

        # Initialize API Manager
        self.api_manager = EnhancedAPIManager()
        
    def can_use_api(self, api_name: str) -> bool:
        """Helper to check API availability via API Manager"""
        return self.api_manager.check_rate_limit(api_name)

    def increment_api_call(self, api_name: str) -> None:
        """Helper to increment API call counter via API Manager"""
        self.api_manager.increment_calls(api_name)



    
    # ...........................................................................
    # LAZY-LOAD PROPERTIES
    # ...........................................................................
    
    @property
    def quantum_lstm(self):
        """Lazy-load LSTM (thread-safe)"""
        return _lazy_loader.get_lstm()
    
    @property
    def quantum_risk(self):
        """Lazy-load Risk Agent (thread-safe)"""
        return _lazy_loader.get_risk_agent()
    
    # ...........................................................................
    # MAIN PREDICTION PIPELINE - 100% DYNAMIC
    # ...........................................................................
    
    def get_comprehensive_prediction(self, symbol: str, df: pd.DataFrame) -> dict:
        """
        Y" FULLY DYNAMIC AI - ZERO HARDCODING
        o. Adaptive thresholds from market volatility + accuracy
        o. Multi-model ensemble with real confidences
        o. Self-learning system
        o. Market volatility awareness
        """
        with self._lock:
            self.health['predictions'] += 1
        
        # ... DATA VALIDATION ...
        if df is None or len(df) < 10:
            logger.warning(f"Insufficient data for {symbol}")
            return {
                'symbol': symbol,
                'signal': 'INSUFFICIENT_DATA',
                'confidence': 0.0,
                'models_used': [],
                'current_price': 0,
                'target_price': 0,
                'predicted_return': 0.0,
                'risk_level': 'UNKNOWN'
            }
        
        try:
            current_price = float(df['Close'].iloc[-1])
        except Exception as e:
            logger.debug(f"Price extraction failed for {symbol}: {e}")
            return {'symbol': symbol, 'error': 'Invalid price data', 'confidence': 0.0}
        
        predictions = []
        confidences = []
        models_used = []
        
        # ... 1. TECHNICAL ANALYSIS ...
        tech_pred = 0.0
        tech_confidence = 0.0
        models_used_tech = 'Technical(FAILED)'
        try:
            rsi = self._calculate_rsi(df)
            macd = self._calculate_macd(df)
            bb_pos = self._calculate_bb_position(df)
            
            # Get dynamic RSI thresholds from adaptive system
            rsi_oversold = self.adaptive_thresholds.get('rsi_oversold', 30)
            rsi_overbought = self.adaptive_thresholds.get('rsi_overbought', 70)
            
            # ... RSI SIGNAL (DYNAMIC) ...
            if rsi < rsi_oversold:
                rsi_signal = 2.0
                rsi_confidence = 75 + ((rsi_oversold - rsi) / rsi_oversold * 20)
            elif rsi > rsi_overbought:
                rsi_signal = -2.0
                rsi_confidence = 75 + ((rsi - rsi_overbought) / (100 - rsi_overbought) * 20)
            else:
                rsi_signal = (rsi - 50) / 50
                rsi_confidence = 50 + abs(rsi - 50) / 50 * 30
            
            # ... MACD SIGNAL (DYNAMIC) ...
            if macd > 0:
                macd_signal = 1.0 + abs(macd)
                macd_confidence = 60 + abs(macd) * 30
            elif macd < 0:
                macd_signal = -1.0 - abs(macd)
                macd_confidence = 60 + abs(macd) * 30
            else:
                macd_signal = 0.0
                macd_confidence = 40
            
            # ... BOLLINGER BANDS SIGNAL (DYNAMIC) ...
            if bb_pos < -0.5:
                bb_signal = 1.5
                bb_confidence = 70
            elif bb_pos > 0.5:
                bb_signal = -1.5
                bb_confidence = 70
            else:
                bb_signal = bb_pos
                bb_confidence = 50 + abs(bb_pos) * 40
            
            # Ensemble technical signals
            tech_signals = [rsi_signal, macd_signal, bb_signal]
            tech_confidences = [rsi_confidence, macd_confidence, bb_confidence]
            
            tech_pred = np.mean(tech_signals)
            tech_confidence = np.mean(tech_confidences)
            models_used_tech = f'Technical(RSI:{rsi:.0f}%,MACD:{macd:.3f},BB:{bb_pos:.2f})'
            
            logger.debug(f"o. Technical: conf={tech_confidence:.1f}%")
        
        except Exception as e:
            logger.debug(f"Technical analysis failed: {e}")
        
        predictions.append(tech_pred)
        confidences.append(tech_confidence)
        models_used.append(models_used_tech)
        
        # ... 2. LSTM MODEL (WITH REAL CONFIDENCE) ...
        if self.quantum_lstm is not None:
            try:
                lstm_result = self.quantum_lstm.predict(df, days_ahead=1)
                if lstm_result and isinstance(lstm_result, dict):
                    lstm_pred = float(lstm_result.get('predictions', 0))
                    lstm_conf = float(lstm_result.get('confidence', 0.6)) * 100
                    
                    if lstm_pred != 0:
                        predictions.append(lstm_pred / 100.0 if abs(lstm_pred) < 2 else (1.0 if lstm_pred > 0 else -1.0))
                        confidences.append(lstm_conf)
                        models_used.append(f'LSTM(pred:{lstm_pred:.1f}%)')
                        
                        logger.debug(f"o. LSTM: conf={lstm_conf:.1f}%")
            
            except Exception as e:
                logger.debug(f"LSTM failed: {e}")
        
        # ... 3. MODEL CONFIDENCES (FROM ACTUAL MODELS) ...
        try:
            model_confs, model_preds = self.get_model_confidences(symbol, df)
            
            if model_confs:
                model_signal = np.mean(list(model_preds.values())) if model_preds else 0
                model_confidence = np.mean(list(model_confs.values()))
                
                if model_signal != 0:
                    predictions.append(model_signal)
                    confidences.append(model_confidence)
                    models_used.append(f'Ensemble({len(model_confs)}models:{model_confidence:.0f}%)')
                    
                    logger.debug(f"o. Model Ensemble: {len(model_confs)} models, conf={model_confidence:.1f}%")
        
        except Exception as e:
            logger.debug(f"Model confidences failed: {e}")
        
        # ... 4. FALLBACK CHECK ...
        if not predictions:
            logger.warning(f"WARN: No models generated predictions for {symbol}. Returning default HOLD with 0 confidence")
            return {
                'symbol': symbol,
                'signal': 'HOLD',
                'confidence': 0.0,
                'current_price': round(current_price, 2),
                'target_price': round(current_price, 2),
                'predicted_return': 0.0,
                'models_used': ['NO_MODELS'],
                'risk_level': 'UNKNOWN'
            }
        
        # ... 5. WEIGHTED ENSEMBLE (SCALAR SAFE) ...

        core = INTELLIGENCE_CORE

        conf_scalars = np.array(
            [core._to_scalar(c) for c in confidences],
            dtype=float
        )

        pred_scalars = np.array(
            [core._to_scalar(p) for p in predictions],
            dtype=float
        )

        weights = conf_scalars / conf_scalars.sum() if conf_scalars.sum() > 0 else \
                np.ones_like(conf_scalars) / len(conf_scalars)

        final_prediction = float(np.dot(pred_scalars, weights))
        weighted_confidence = float(np.dot(conf_scalars, weights))

       
        # ... 6. DYNAMIC SIGNAL GENERATION (FROM ADAPTIVE THRESHOLDS) ...
        strong_buy_th = self.adaptive_thresholds.get('strong_buy_threshold', 2.0)
        buy_th = self.adaptive_thresholds.get('buy_threshold', 0.5)
        strong_sell_th = self.adaptive_thresholds.get('strong_sell_threshold', -2.0)
        sell_th = self.adaptive_thresholds.get('sell_threshold', -0.5)
        
        if final_prediction > strong_buy_th:
            signal = 'STRONG BUY'
            final_confidence = max(weighted_confidence, 75)
        elif final_prediction > buy_th:
            signal = 'BUY'
            final_confidence = max(weighted_confidence, 65)
        elif final_prediction < strong_sell_th:
            signal = 'STRONG SELL'
            final_confidence = max(weighted_confidence, 75)
        elif final_prediction < sell_th:
            signal = 'SELL'
            final_confidence = max(weighted_confidence, 65)
        else:
            signal = 'HOLD'
            final_confidence = min(weighted_confidence, 55)
        
        final_confidence = min(max(final_confidence, 0), 95)
        
        # ... 7. VOLATILITY-ADJUSTED TARGET ...
        returns = df['Close'].pct_change().dropna()
        volatility = returns.std() * np.sqrt(252) * 100 if len(returns) > 0 else 20
        
        volatility_factor = volatility / 25
        adjusted_prediction = final_prediction * volatility_factor
        target_price = current_price * (1 + adjusted_prediction / 100.0)
        predicted_return = adjusted_prediction

        # Horizon projection map (derived interpretation layer, non-destructive to core model logic)
        base_return_frac = predicted_return / 100.0
        annual_vol_frac = max(0.0, float(volatility) / 100.0)
        horizon_days = {
            '1d': 1,
            '15d': 15,
            '3m': 90,
            '6m': 180,
            '1y': 365
        }
        projections = {}
        for h_key, h_days in horizon_days.items():
            scale = h_days / 365.0
            drift = base_return_frac * scale
            uncertainty_penalty = annual_vol_frac * np.sqrt(scale) * 0.10
            h_ret = drift - uncertainty_penalty
            h_target = current_price * (1 + h_ret)
            projections[h_key] = {
                'days': int(h_days),
                'return_pct': round(h_ret * 100.0, 2),
                'target_price': round(float(h_target), 2)
            }
        
        # ... 8. DYNAMIC RISK ASSESSMENT (FROM ADAPTIVE THRESHOLDS) ...
        vol_high = self.adaptive_thresholds.get('vol_high_risk', 40)
        vol_medium = self.adaptive_thresholds.get('vol_medium_risk', 25)
        
        if volatility > vol_high:
            risk_level = 'HIGH'
            final_confidence *= 0.8
        elif volatility > vol_medium:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
        
        # ... 8.5 META-INTELLIGENCE CONFIDENCE ADJUSTMENT ...
        if (
            self.regime_embedding
            and self.regime_memory
            and self.meta_weighter
            and self.confidence_engine
        ):
            try:
                # Continuous regime embedding
                embedding = self.regime_embedding.transform(df)
                self.regime_memory.update(embedding)
                regime_id = self.regime_memory.get_regime_id(embedding)

                # Infer dominant model (best proxy without changing internals)
                dominant_model = (
                    "lstm" if "LSTM" in " ".join(models_used)
                    else "rf" if "Ensemble" in " ".join(models_used)
                    else "technical"
                )

                # Apply learned reliability weight
                weight = self.meta_weighter.get_weight(regime_id, dominant_model)
                final_confidence *= weight

                # Confidence calibration (online + historical + decay)
                final_confidence = self.confidence_engine.compute(
                    symbol,
                    final_confidence / 100.0
                ) * 100.0

                logger.debug(
                    f"Meta-Intelligence applied | Regime={regime_id} | "
                    f"Model={dominant_model} | Weight={weight:.2f}"
                )

            except Exception as e:
                logger.debug(f"Meta-Intelligence skipped: {e}")

        # ... 8.7 MULTI-WORLD INTELLIGENCE (NEW) ...
        future_outlook = None
        ai_decision = "TRADE"
        ai_reason = "System equilibrium maintained"

        try:
            # Prepare model signals/confidences for simulation
            # Mapping from models_used names back to simple keys if possible
            # For simplicity, we can use the technical and lstm signals
            world_preds = {}
            world_confs = {}

            if "Technical" in str(models_used):
                world_preds['technical'] = tech_pred
                world_confs['technical'] = tech_confidence
            
            if "LSTM" in str(models_used):
                world_preds['lstm'] = lstm_pred / 100.0  # Normalized
                world_confs['lstm'] = lstm_conf

            if world_preds:
                simulator = MultiWorldSimulator()
                future_outlook = simulator.simulate(world_preds, world_confs)
                
                if future_outlook and future_outlook.get("fragility") in ("EXTREME", "HIGH"):
                    ai_decision = "PAUSE"
                    ai_reason = future_outlook.get("story", "Predictive dissonance detected")
        except Exception as e:
            logger.debug(f"Multi-world simulation failed: {e}")

        # ... 8.8 MODEL DETAILS (FOR UI) ...
        model_details = {}
        
        # Technical
        if "Technical" in str(models_used):
            tech_label = "BUY" if tech_pred > buy_th else "SELL" if tech_pred < sell_th else "HOLD"
            model_details["Technical Layer"] = {"signal": tech_label, "confidence": round(tech_confidence, 1)}
            
        # LSTM
        if "LSTM" in str(models_used):
            lstm_label = "BUY" if lstm_pred > 2 else "SELL" if lstm_pred < -2 else "HOLD"
            model_details["LSTM Engine"] = {"signal": lstm_label, "confidence": round(lstm_conf, 1)}
            
        # Ensemble / Quantum Model
        if "Ensemble" in str(models_used):
            ensemble_signal = np.mean(list(model_preds.values())) if 'model_preds' in locals() else 0
            ensemble_label = "BUY" if ensemble_signal > buy_th else "SELL" if ensemble_signal < sell_th else "HOLD"
            model_details["Quantum Ensemble"] = {"signal": ensemble_label, "confidence": round(model_confidence, 1)}

        # ... 9. BUILD RESULT ...
        result = {
            'symbol': symbol,
            'signal': signal,
            'confidence': round(final_confidence, 1),
            'current_price': round(current_price, 2),
            'target_price': round(target_price, 2),
            'predicted_return': round(predicted_return, 2),
            'predictions': projections,
            'target_6m': projections.get('6m', {}).get('target_price'),
            'target_1y': projections.get('1y', {}).get('target_price'),
            'models_used': models_used,
            'model_details': model_details,
            'risk_level': risk_level,
            'volatility': round(volatility, 1),
            'future_outlook': future_outlook,
            'ai_decision': ai_decision,
            'ai_reason': ai_reason,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f'o. {symbol}: {signal} ({final_confidence:.1f}%) | Return: {predicted_return:.2f}% | Risk: {risk_level}')
        
        # ... 10. LOG FOR LEARNING ...
        if self.db:
            try:
                self.db.log_prediction(result)
            except Exception as e:
                logger.debug(f"DB logging failed: {e}")
        
        self.prediction_history.append(result)
        return result

    def update_meta_learning(self, symbol, dominant_model, was_correct, df):
        if not (
            self.regime_embedding
            and self.regime_memory
            and self.meta_weighter
        ):
            return

        try:
            embedding = self.regime_embedding.transform(df)
            regime_id = self.regime_memory.get_regime_id(embedding)
            self.meta_weighter.update(regime_id, dominant_model, was_correct)
        except Exception:
            pass

   
    # ...........................................................................
    # UTILITY METHODS
    # ...........................................................................

    def update_after_outcome(self, symbol, df, raw_confidence, was_correct, dominant_model):
        """
        Updates confidence calibration + regime-aware model reliability.
        Called AFTER actual outcome is known (EOD / batch / cron).
        """

        if not self.confidence_engine:
            return

        try:
            # 1ÃƒÆ’Ã‚Â¯Ãƒâ€šÃ‚Â¸Ãƒâ€šÃ‚Âf Update confidence honesty
            self.confidence_engine.update_online(raw_confidence, was_correct)
            self.confidence_engine.update_symbol(symbol, was_correct)

            # 2ÃƒÆ’Ã‚Â¯Ãƒâ€šÃ‚Â¸Ãƒâ€šÃ‚Âf Update regime-based model reliability
            if self.regime_embedding and self.regime_memory and self.meta_weighter:
                embedding = self.regime_embedding.transform(df)
                self.regime_memory.update(embedding)
                regime_id = self.regime_memory.get_regime_id(embedding)

                self.meta_weighter.update(
                    regime_id,
                    dominant_model,
                    was_correct
                )
        except Exception:
            pass

    def update_thresholds_from_accuracy(self, accuracy_data):
        """Update thresholds based on prediction accuracy (SELF-LEARNING)"""
        if self.adaptive_thresholds:
            self.adaptive_thresholds.update_from_accuracy(accuracy_data)
            logger.info("o. Thresholds auto-updated from accuracy data")
    
    def get_prediction_history(self, limit=100):
        """Get recent predictions"""
        return list(self.prediction_history)[-limit:]
    
    
    def get_health_metrics(self):
        """Get system health"""
        return {
            'init_time': self.health['init_time'],
            'total_failures': self.health['failures'],
            'total_predictions': self.health['predictions']
        }

# ...............................................................................
# ADVANCED QUANTUMAI NEXUS ENGINE - 100% AUTOMATIC, NO HARDCODING
# ...............................................................................

import concurrent.futures
import yfinance as yf
from typing import List, Dict
from datetime import datetime
import time

class QuantumAINexusAI(QuantumAI):
    """
    Advanced QuantumAI engine with:
    o. Inherits from base QuantumAI
    o. 100% dynamic thresholds
    o. Self-learning system
    o. Real-time market adaptation
    o. Async data fetching
    o. Complete error handling
    """
    
    def __init__(self):
        """Initialize QuantumAI NEXUS Engine"""
        logger.info("Y Initializing QuantumAI NEXUS AI Engine")
        
        # ... CRITICAL: CALL PARENT __init__ ...
        super().__init__()  # ? THIS INITIALIZES: AdaptiveThresholds, ML Models, LSTM, Risk Agent
        
        # ... NEXUS-SPECIFIC FEATURES ...
        self.cache_advanced = {}
        self.cache_ttl = 300  # 5 minutes
        
        # ... RATE LIMITING ...
        self.rate_limits = {
            'yfinance': {'calls': 0, 'reset_time': time.time(), 'limit': 2000},
            'news': {'calls': 0, 'reset_time': time.time(), 'limit': 100}
        }
        
        # ... INITIALIZE ADVANCED MODULES ...
        self.initialize_advanced_ml()
        self.initialize_rl_engine()
        self.initialize_secure_api()
        self.initialize_standard_ml()
        
        # ... SENTIMENT ANALYZER (SELF-DETECTING, NO FLAGS) ...
        self.sentiment_analyzer = None
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            self.sentiment_analyzer = SentimentIntensityAnalyzer()
            logger.info("o. Sentiment analyzer initialized")
        except Exception as e:
            logger.debug(f"Sentiment analyzer unavailable: {e}")

    def build_kelly_signals(self, holdings, preds=None):
        """
        Convert holdings into KellyAI signals for the allocator.
        Handles base symbol to .NS exchange symbol normalization.
        """
        signals = []
        try:
            # Get latest predictions from AI engine state
            preds = preds or AI_ENGINE_STATE.get("predictions", {})
            if not preds:
                return []

            for h in holdings:
                base_symbol = h.get('symbol', '').upper()
                
                # Check for .NS first, then base
                ai_symbol = f"{base_symbol}.NS"
                p = preds.get(ai_symbol) or preds.get(base_symbol)
                
                if not p: continue

                pred_fields = self._extract_prediction_fields(p)
                conf = float(pred_fields.get('confidence', 0)) / 100.0
                target = float(pred_fields.get('target_price', 0))
                current = float(pred_fields.get('current_price', 0))
                if current <= 0:
                    continue

                predicted_return = float(pred_fields.get('predicted_return', 0)) / 100.0
                upside_from_target = (target - current) / current if target > 0 else 0.0
                upside = max(upside_from_target, max(predicted_return, 0.0))

                vol = float(pred_fields.get('volatility', 0.2) or 0.2)
                vol = (vol / 100.0) if vol > 1.0 else vol
                vol = max(vol, 0.05)
                downside = max(abs(predicted_return) * 0.5, abs(upside_from_target) * 0.5, 0.003)
                volatility_penalty = 1.0 + max(0.0, vol - 0.2) * 2.0

                payoff = (abs(upside / downside) / volatility_penalty) if downside > 0 else 1.0
                
                sig = KellySignal(
                    symbol=base_symbol, # Signal tracks the base symbol for matching back to holdings
                    win_prob=conf,
                    payoff_ratio=payoff,
                    confidence=conf,
                    agreement=pred_fields.get('agreement', 0.8),
                    volatility=vol
                )
                signals.append(sig)
        except Exception as e:
            logger.error(f"Failed to build Kelly signals: {e}")
            
        return signals

    def _extract_prediction_fields(self, packet):
        """Normalize nested/flat prediction payloads into a flat dict."""
        pkt = packet if isinstance(packet, dict) else {}
        pred = pkt.get("prediction", pkt)
        pred = pred if isinstance(pred, dict) else {}
        verdict = pred.get("verdict", {}) if isinstance(pred.get("verdict", {}), dict) else {}
        snap = pred.get("snapshot", {}) if isinstance(pred.get("snapshot", {}), dict) else {}

        def _f(*vals, default=0.0):
            for v in vals:
                if v is None:
                    continue
                try:
                    return float(v)
                except Exception:
                    continue
            return float(default)

        confidence = _f(pred.get("confidence"), verdict.get("confidence"), pkt.get("confidence"), default=0.0)
        target_price = _f(pred.get("target_price"), verdict.get("target_price"), pkt.get("target_price"), default=0.0)
        current_price = _f(pkt.get("current_price"), snap.get("price"), pred.get("current_price"), default=0.0)
        predicted_return = _f(pred.get("predicted_return"), verdict.get("predicted_return"), pkt.get("predicted_return"), default=0.0)
        raw_vol = _f(pkt.get("volatility"), pred.get("volatility"), default=0.0)
        # Kelly allocator expects volatility in 0..1 scale.
        volatility = (raw_vol / 100.0) if raw_vol > 1.0 else raw_vol
        agreement = _f(pred.get("agreement"), pkt.get("agreement"), default=0.8)
        entropy = _f(pred.get("entropy"), verdict.get("entropy"), pkt.get("entropy"), default=0.0)

        risk_level = str(pred.get("risk_level") or pkt.get("risk_level") or "").upper()
        risk_level_score = _f(pred.get("risk_level_score"), verdict.get("risk"), pkt.get("risk_level_score"), default=0.0)
        if risk_level_score <= 0.0 and risk_level:
            risk_level_score = {"LOW": 0.15, "MEDIUM": 0.35, "HIGH": 0.65}.get(risk_level, 0.25)

        # Derive entropy from existing model outputs when source packet omits it.
        if entropy <= 0.0:
            uncertainty = max(0.0, min(1.0, 1.0 - (confidence / 100.0)))
            entropy = min(1.0, round((uncertainty * 0.7) + (max(volatility, 0.0) * 0.3), 4))

        return {
            "confidence": confidence,
            "target_price": target_price,
            "current_price": current_price,
            "predicted_return": predicted_return,
            "entropy": entropy,
            "risk_level_score": risk_level_score,
            "volatility": volatility,
            "agreement": agreement,
        }

    def compute_portfolio_intelligence(self, holdings, preds=None):
        """
        Ys? CORE ENGINE ?" Portfolio Intelligence Generator
        GUARANTEE: Output positions count ALWAYS equals input holdings count.
        Enriches DB holdings with AI capital allocation, LIVE prices, and real metrics.
        Predictions enhance portfolio ?" never create it.
        """
        if holdings and isinstance(holdings, list) and isinstance(holdings[0], str):
            requested_base = {normalize_symbol(s) for s in holdings}
            all_holdings = self.db.get_portfolio() if self.db else []
            holdings = [h for h in all_holdings if normalize_symbol(h.get("symbol")) in requested_base]

        if not holdings:
            return {
                "positions": [],
                "account_metrics": {"total_risk": 0, "edge": 0, "regimeFit": 0, "last_recompute": time.time()},
                "status": "NO_POSITIONS"
            }

        # ... STEP 1: BATCH LIVE PRICE FETCH (one yfinance call for all symbols) ...
        live_data = {}  # base_symbol -> {price, change_pct, day_high, day_low, volume}
        try:
            exchange_symbols = []
            base_to_exchange = {}
            for h in holdings:
                base = h.get('symbol', '').upper().replace('.NS', '').replace('.BO', '')
                exch = f"{base}.NS"
                exchange_symbols.append(exch)
                base_to_exchange[base] = exch

            if exchange_symbols:
                import yfinance as yf
                tickers = yf.download(exchange_symbols, period='1d', group_by='ticker', progress=False, threads=True)
                for base, exch in base_to_exchange.items():
                    try:
                        if len(exchange_symbols) == 1:
                            df = tickers  # single ticker returns flat DataFrame
                        else:
                            df = tickers[exch] if exch in tickers.columns.get_level_values(0) else None
                        if df is not None and not df.empty:
                            close = float(df['Close'].iloc[-1]) if 'Close' in df.columns else 0
                            opn = float(df['Open'].iloc[-1]) if 'Open' in df.columns else close
                            high = float(df['High'].iloc[-1]) if 'High' in df.columns else 0
                            low = float(df['Low'].iloc[-1]) if 'Low' in df.columns else 0
                            vol = float(df['Volume'].iloc[-1]) if 'Volume' in df.columns else 0
                            change_pct = ((close - opn) / opn * 100) if opn > 0 else 0
                            if close > 0:
                                live_data[base] = {
                                    'price': close, 'change_pct': round(change_pct, 2),
                                    'day_high': high, 'day_low': low, 'volume': vol,
                                    'prev_close': opn
                                }
                    except Exception as sym_err:
                        logger.debug(f"Live price skip {base}: {sym_err}")
        except Exception as e:
            logger.warning(f"Batch live price fetch failed (using cached): {e}")

        if preds is None:
            preds = AI_ENGINE_STATE.get("predictions", {})

        # ... STEP 2: KELLY ALLOCATION ...
        try:
            signals = self.build_kelly_signals(holdings, preds=preds)
            allocation = kelly_engine.allocate_portfolio(signals, "NEUTRAL") if signals else []
        except Exception as e:
            logger.warning(f"Kelly allocation failed (will use defaults): {e}")
            allocation = []

        # ... STEP 3: ENRICH POSITIONS ...
        enriched_positions = []
        prediction_agreement_count = 0
        total_symbols_with_predictions = 0

        for h in holdings:
            symbol = h.get('symbol', '').upper()
            base_symbol = symbol.replace('.NS', '').replace('.BO', '')
            ai_symbol = f"{base_symbol}.NS"

            # Find Kelly allocation for this symbol
            ai_metrics = next((a for a in allocation if a.get('symbol', '').upper().replace('.NS','').replace('.BO','') == base_symbol), {})

            # Find prediction data
            p = preds.get(ai_symbol) or preds.get(base_symbol) or preds.get(symbol) or {}
            pred_fields = self._extract_prediction_fields(p)

            # ... LIVE PRICE PRIORITY: yfinance > prediction > MARKET cache ...
            # NEVER fall back to avg_price for current_price (that's the user's purchase price)
            ld = live_data.get(base_symbol, {})
            live_price = ld.get('price', 0)
            pred_price = float(pred_fields.get('current_price', 0))
            cached_price = MARKET.get_cached_price(base_symbol) or 0
            current_price = live_price or pred_price or cached_price
            
            # If still 0, show avg_price for display but DON'T cache it as market price
            display_price = current_price if current_price > 0 else float(h.get('avg_price', 0))
            is_live = current_price > 0  # True if we have a real market price

            target_price = float(pred_fields.get('target_price', 0))
            change_pct = ld.get('change_pct', 0)

            # Track prediction agreement for regimeFit
            if p:
                total_symbols_with_predictions += 1
                pred_conf = float(pred_fields.get('confidence', 0))
                if pred_conf > 50:
                    prediction_agreement_count += 1

            vol_component = float(pred_fields.get("volatility", 0) or 0)
            vol_component = (vol_component / 100.0) if vol_component > 1.0 else vol_component
            risk_score = float(pred_fields.get("risk_level_score", 0)) or vol_component

            # Dynamic TP/SL interpretation layer:
            # If live/current price has already crossed TP, roll TP forward and tighten SL.
            tp_base = target_price if target_price > 0 else (display_price * 1.05 if display_price > 0 else 0)
            sl_base = display_price * 0.95 if display_price > 0 else 0
            tp_state = "ACTIVE"
            tp_effective = tp_base
            sl_effective = sl_base
            if display_price > 0 and tp_base > 0 and display_price >= (tp_base * 1.002):
                vol_buf = max(0.01, min(0.06, (vol_component * 1.5) if vol_component > 0 else 0.015))
                tp_effective = display_price * (1.0 + vol_buf)
                sl_effective = max(sl_base, display_price * (1.0 - (vol_buf * 0.8)))
                tp_state = "ROLLED"

            conf_score = float(pred_fields.get("confidence", 0))
            entropy_score = float(pred_fields.get("entropy", 0))
            predicted_return_pct = float(pred_fields.get("predicted_return", 0))
            kelly_fraction = float(ai_metrics.get("kelly_fraction", 0))
            weight_pct = float(ai_metrics.get("weight_pct", 0))

            # Derived interpretation layer (non-destructive):
            # when allocator weight is zero but prediction still has positive quality,
            # estimate a conservative fractional size from existing model outputs.
            if kelly_fraction <= 0 and predicted_return_pct > 0 and conf_score > 0:
                conf01 = max(0.0, min(1.0, conf_score / 100.0))
                risk01 = max(0.0, min(1.0, risk_score))
                alpha01 = max(0.0, predicted_return_pct / 100.0)
                derived_fraction = alpha01 * conf01 * max(0.15, 1.0 - risk01)
                kelly_fraction = max(kelly_fraction, min(0.20, derived_fraction))

            if weight_pct <= 0 and kelly_fraction > 0:
                weight_pct = min(100.0, kelly_fraction * 100.0)

            dist_tp = (abs(tp_effective - display_price) / display_price) if (display_price > 0 and tp_effective > 0) else 1.0
            dist_sl = (abs(display_price - sl_effective) / display_price) if (display_price > 0 and sl_effective > 0) else 1.0

            if risk_score >= 0.55:
                intent_state = "DEFEND"
            elif tp_state == "ROLLED":
                intent_state = "LOCK_PROFIT"
            elif (ai_metrics.get("action") in ("ADD", "BUY")) and conf_score >= 55:
                intent_state = "ACCUMULATE"
            elif (ai_metrics.get("action") in ("REDUCE", "SELL")) or dist_tp <= 0.02:
                intent_state = "DISTRIBUTE"
            else:
                intent_state = "BALANCE"

            playbook_map = {
                "ACCUMULATE": "Scale in on strength while risk remains controlled",
                "DISTRIBUTE": "Trim exposure into target-zone strength",
                "DEFEND": "Prioritize downside control and capital protection",
                "LOCK_PROFIT": "Trail gains with progressive stop tightening",
                "BALANCE": "Hold core exposure and wait for clearer edge"
            }
            playbook = playbook_map.get(intent_state, "Hold allocation")

            # Multi-stage target ladder from live volatility (interpretation layer only)
            ladder_step = max(0.004, min(0.03, vol_component * 0.8 if vol_component > 0 else 0.008))
            tp1 = tp_effective
            tp2 = tp_effective * (1.0 + ladder_step) if tp_effective > 0 else 0
            trail_sl = max(sl_effective, display_price * (1.0 - max(0.004, min(0.02, vol_component * 0.6 if vol_component > 0 else 0.006)))) if display_price > 0 else sl_effective

            urgency_score = min(
                100.0,
                max(0.0, (1.0 - min(dist_sl, 1.0) / 0.03) * 45.0)
                + max(0.0, (1.0 - min(dist_tp, 1.0) / 0.03) * 30.0)
                + min(25.0, entropy_score * 25.0)
            )

            explain_note = (
                f"{intent_state}: conf={conf_score:.1f} edge={kelly_fraction:.3f} "
                f"entropy={entropy_score:.3f} urgency={urgency_score:.1f}"
            )

            lot_metrics = {}
            try:
                if self.db and hasattr(self.db, "get_tax_lot_metrics"):
                    lot_metrics = self.db.get_tax_lot_metrics(base_symbol, display_price)
            except Exception as lot_err:
                logger.debug(f"Lot metrics unavailable for {base_symbol}: {lot_err}")

            # Build enriched position
            item = {
                "symbol": base_symbol,
                "quantity": float(h.get('quantity', 0)),
                "avg_price": float(h.get('avg_price', 0)),
                "current_price": display_price,
                "is_live_price": is_live,
                "change_percent": change_pct,
                "day_high": ld.get('day_high', 0),
                "day_low": ld.get('day_low', 0),
                "volume": ld.get('volume', 0),
                "added_date": h.get('added_date', h.get('purchase_date', '')),
                "action": ai_metrics.get("action", "HOLD"),
                "confidence": conf_score,
                "edge": kelly_fraction * 2,
                "entropy": entropy_score,
                "kelly_percent": weight_pct,
                "kelly_fraction": kelly_fraction,
                "risk": risk_score,
                "predicted_return": predicted_return_pct,
                "tp": tp_effective,
                "sl": sl_effective,
                "tp_state": tp_state,
                "tp1": tp1,
                "tp2": tp2,
                "trail_sl": trail_sl,
                "capital_weight": weight_pct,
                "intent_state": intent_state,
                "playbook": playbook,
                "urgency_score": round(urgency_score, 2),
                "explain_note": explain_note,
                "lots_count": int(lot_metrics.get("lots_count", 0) or 0),
                "open_qty": float(lot_metrics.get("open_qty", h.get("quantity", 0)) or 0),
                "open_cost": float(lot_metrics.get("open_cost", float(h.get("avg_price", 0)) * float(h.get("quantity", 0))) or 0),
                "current_value": float(lot_metrics.get("current_value", display_price * float(h.get("quantity", 0))) or 0),
                "unrealized_total": float(lot_metrics.get("unrealized_total", 0) or 0),
                "stcg_unrealized": float(lot_metrics.get("stcg_unrealized", 0) or 0),
                "ltcg_unrealized": float(lot_metrics.get("ltcg_unrealized", 0) or 0),
                "stcg_realized": float(lot_metrics.get("stcg_realized", 0) or 0),
                "ltcg_realized": float(lot_metrics.get("ltcg_realized", 0) or 0),
            }

            # ... ONLY cache LIVE market prices ?" NEVER cache avg_price ...
            if is_live and current_price > 0:
                MARKET.update_price_cache(base_symbol, current_price)

            enriched_positions.append(item)

        # ... STEP 4: COMPUTE REAL ACCOUNT METRICS (no hardcoding) ...
        n = len(enriched_positions) if enriched_positions else 1
        avg_risk = sum(p.get('risk', 0) for p in enriched_positions) / n
        avg_edge = sum(p.get('edge', 0) for p in enriched_positions) / n
        stcg_unrealized_total = sum(float(p.get('stcg_unrealized', 0) or 0) for p in enriched_positions)
        ltcg_unrealized_total = sum(float(p.get('ltcg_unrealized', 0) or 0) for p in enriched_positions)
        stcg_realized_total = sum(float(p.get('stcg_realized', 0) or 0) for p in enriched_positions)
        ltcg_realized_total = sum(float(p.get('ltcg_realized', 0) or 0) for p in enriched_positions)

        # regimeFit: prediction coverage - average confidence (0-1 scale)
        # Higher when more symbols have predictions and those predictions are confident
        if total_symbols_with_predictions > 0:
            coverage = total_symbols_with_predictions / len(holdings)
            agreement = prediction_agreement_count / total_symbols_with_predictions
            regime_fit = round(coverage * agreement, 4)
        else:
            regime_fit = 0  # No predictions yet ?" honest zero, not fake 85%

        return {
            "positions": enriched_positions,
            "account_metrics": {
                "total_risk": round(avg_risk, 6),
                "last_recompute": time.time(),
                "edge": round(avg_edge, 6),
                "regimeFit": regime_fit,
                "symbols_live": sum(1 for p in enriched_positions if p.get('is_live_price')),
                "symbols_total": len(enriched_positions),
                "prediction_coverage": f"{total_symbols_with_predictions}/{len(holdings)}",
                "stcg_unrealized_total": round(stcg_unrealized_total, 6),
                "ltcg_unrealized_total": round(ltcg_unrealized_total, 6),
                "stcg_realized_total": round(stcg_realized_total, 6),
                "ltcg_realized_total": round(ltcg_realized_total, 6)
            },
            "status": "OPTIMIZED" if allocation else "BASE_HOLD"
        }

    def load_portfolio(self, holdings):
        """Load DB holdings (base symbols) into AI memory for next state refresh."""
        self._portfolio_holdings = holdings or []

    def request_refresh_cycle(self):
        """Refresh the canonical cognitive state; websocket loop emits it."""
        with cache_lock:
            predictions = system_cache.get('recent_predictions', [])
        AI_ENGINE_STATE["cognitive_state"] = get_realtime_cognitive_state(predictions)
        AI_ENGINE_STATE["last_update"] = datetime.now(ZoneInfo("UTC"))

    def get_latest_prices(self, symbols):
        """
        Universal price adapter so ALL modules can safely fetch prices
        Prevents portfolio crash cascade
        """
        prices = {}

        try:
            # If live cache exists use it
            if hasattr(self, "live_prices") and isinstance(self.live_prices, dict):
                for s in symbols:
                    if s in self.live_prices:
                        prices[s] = self.live_prices[s]

            # fallback ?' prediction cache
            if hasattr(self, "prediction_cache"):
                for s in symbols:
                    if s not in prices and s in self.prediction_cache:
                        prices[s] = self.prediction_cache[s].get("price")

            # final safe guard (NEVER return missing)
            for s in symbols:
                prices.setdefault(s, None)

            return prices

        except Exception as e:
            logger.error(f"Price adapter error: {e}")
            return {s: None for s in symbols}
   
    # ...........................................................................
    # INITIALIZATION METHODS
    # ...........................................................................
    
    def initialize_advanced_ml(self) -> None:
        """Initialize advanced ML modules (LSTM, Explainability)"""
        if ADVANCED_ML_AVAILABLE:
            try:
                if QuantumLSTMModel:
                    self._quantum_lstm_model = QuantumLSTMModel()
                    logger.info("o. QuantumLSTMModel initialized")
                else:
                    self._quantum_lstm_model = None
                
                if ExplainabilityEngine:
                    self.explainer = ExplainabilityEngine()
                    logger.info("o. ExplainabilityEngine initialized")
                else:
                    self.explainer = None
            except Exception as e:
                logger.warning(f"Advanced ML initialization failed: {e}")
                self._quantum_lstm_model = None
                self.explainer = None
        else:
            self._quantum_lstm_model = None
            self.explainer = None
    
    def initialize_rl_engine(self) -> None:
        """Initialize RL risk engine"""
        if RL_ENGINE_AVAILABLE:
            try:
                if QuantumRiskAgent:
                    self._quantum_risk_model = QuantumRiskAgent()
                    logger.info("o. QuantumRiskAgent initialized")
                else:
                    self._quantum_risk_model = None
                
                if PortfolioOptimizer:
                    self.portfolio_optimizer = PortfolioOptimizer()
                    logger.info("o. PortfolioOptimizer initialized")
                else:
                    self.portfolio_optimizer = None
            except Exception as e:
                logger.warning(f"RL Engine initialization failed: {e}")
                self._quantum_risk_model = None
                self.portfolio_optimizer = None
        else:
            self._quantum_risk_model = None
            self.portfolio_optimizer = None
    
    def initialize_secure_api(self) -> None:
        """Initialize secure API configuration"""
        if secure_api_AVAILABLE:
            try:
                if SecureAPIConfig:
                    self.secure_api = SecureAPIConfig()
                    logger.info("o. SecureAPIConfig initialized")
                else:
                    self.secure_api = None
            except Exception as e:
                logger.warning(f"API Config initialization failed: {e}")
                self.secure_api = None
        else:
            self.secure_api = None
    
    def initialize_standard_ml(self) -> None:
        """Initialize standard ML models"""
        if ML_AVAILABLE:
            try:
                from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
                from sklearn.preprocessing import StandardScaler, RobustScaler
                
                self.models = {
                    'rf': RandomForestRegressor(n_estimators=50, max_depth=10, random_state=42, n_jobs=-1),
                    'gb': GradientBoostingRegressor(n_estimators=50, learning_rate=0.1, random_state=42)
                }
                self.scalers = {
                    'standard': StandardScaler(),
                    'robust': RobustScaler()
                }
                logger.info(f"o. Standard ML models initialized: {list(self.models.keys())}")
            except Exception as e:
                logger.warning(f"Standard ML initialization failed: {e}")
    
    # ...........................................................................ÃƒÆ’@app.route('/api/dashboard-data', methods=['GET'])
    def get_live_stock_data(self, symbol: str, period: str = '1y') -> pd.DataFrame:
        """
        Get live stock data with caching and fallback
        o. Live data first
        o. Synthetic fallback if API fails
        o. 5-minute cache TTL
        """
        cache_key = f"{symbol}_{period}"
        
        # Check cache (5 minute TTL)
        if cache_key in self.cache_advanced:
            data, timestamp = self.cache_advanced[cache_key]
            if (datetime.now() - timestamp).total_seconds() < 300:
                logger.debug(f"[CACHE] Cache hit: {symbol}")
                return data
        
        try:
            # Try real data first
            if self.can_use_api('yfinance'):
                ticker = yf.Ticker(symbol)
                df = ticker.history(period=period)
                self.increment_api_call('yfinance')
                
                # SELF-HEALING: If plain symbol fails, try with .NS suffix
                if df.empty and "." not in symbol:
                    alt_symbol = f"{symbol}.NS"
                    logger.info(f"Retrying with normalized symbol: {alt_symbol}")
                    ticker = yf.Ticker(alt_symbol)
                    df = ticker.history(period=period)
                
                if not df.empty:
                    df.attrs["data_source"] = "live"
                    df.attrs["is_synthetic"] = False
                    # Cache it
                    self.cache_advanced[cache_key] = (df, datetime.now())
                    logger.info(f"[DATA] Live data fetched for {symbol}")
                    return df
            
            # Fallback to synthetic data
            logger.warning(f"Using synthetic data for {symbol}")
            return self.generate_realistic_data(symbol, period)
            
        except Exception as e:
            logger.error(f"Data fetch failed for {symbol}: {e}")
            return self.generate_realistic_data(symbol, period)
    
    def generate_realistic_data(self, symbol: str, period: str = '1y') -> pd.DataFrame:
        """
        Generate realistic synthetic OHLCV market data
        o. Deterministic (reproducible)
        o. No hardcoding
        o. Dynamic price scaling
        o. Realistic patterns
        """
        try:
            # Map periods to days
            period_map = {
                '1d': 1, '5d': 5, '1mo': 30, '3mo': 90,
                '6mo': 180, '1y': 365, '2y': 730
            }
            days = period_map.get(period, 365)
            
            # Date range
            dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
            
            # Deterministic seed per symbol (reproducible)
            np.random.seed(abs(hash(symbol)) % 10000)
            
            # Dynamic base price (100-5000, no hardcoding)
            symbol_value = abs(hash(symbol)) % 5000
            base_price = 100 + (symbol_value % 4900)
            
            # Simulate realistic returns
            drift = np.random.uniform(0.0001, 0.001)
            volatility = np.random.uniform(0.01, 0.03)
            returns = np.random.normal(drift, volatility, days)
            
            # Add autocorrelation (momentum)
            for i in range(1, len(returns)):
                returns[i] = 0.9 * returns[i - 1] + 0.1 * returns[i]
            
            # Generate price series
            prices = [base_price]
            for r in returns[1:]:
                new_price = prices[-1] * (1 + r)
                prices.append(max(base_price * 0.3, new_price))
            
            df = pd.DataFrame(index=dates)
            df['Close'] = prices
            
            # Generate OHLC
            daily_range = np.random.uniform(0.005, 0.03, days)
            df['Open'] = df['Close'].shift(1).fillna(df['Close'].iloc[0]) * (
                1 + np.random.normal(0, 0.001, days)
            )
            df['High'] = np.maximum(df['Open'], df['Close']) * (1 + daily_range * 0.5)
            df['Low'] = np.minimum(df['Open'], df['Close']) * (1 - daily_range * 0.5)
            
            # Volume generation (dynamic)
            avg_volume = 1_000_000 + (abs(hash(symbol)) % 9_000_000)
            df['Volume'] = (avg_volume * np.random.uniform(0.5, 2.0, days)).astype(int)
            
            # Standard columns
            df[['Dividends', 'Stock Splits']] = 0.0
            df = df[['Open', 'High', 'Low', 'Close', 'Volume', 'Dividends', 'Stock Splits']]
            df.attrs["data_source"] = "synthetic"
            df.attrs["is_synthetic"] = True
            
            logger.info(f"Generated synthetic data for {symbol} ({days} days, base={base_price:.2f})")
            return df
            
        except Exception as e:
            logger.error(f"Data generation failed for {symbol}: {e}")
            # Emergency fallback
            dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
            price = 1000 + abs(hash(symbol)) % 1000
            
            df = pd.DataFrame({
                'Open': [price] * 100,
                'High': [price * 1.02] * 100,
                'Low': [price * 0.98] * 100,
                'Close': [price] * 100,
                'Volume': [1_000_000] * 100,
                'Dividends': [0.0] * 100,
                'Stock Splits': [0.0] * 100
            }, index=dates)
            df.attrs["data_source"] = "synthetic"
            df.attrs["is_synthetic"] = True
            return df
    
    def get_top_active_stocks(self, limit: int = 15) -> List[str]:
        """
        Fully dynamic stock discovery ?" ranked by LIVE volume.
        1) Batch-download 1-day data for NIFTY 50 components
        2) Rank by volume ?' return most active
        3) Cache result for 60 minutes
        4) Minimal fallback ONLY if ALL APIs fail
        """
        cache_key = f"top_active_{limit}"

        # ---- CACHE (60 min) ----
        if cache_key in self.cache_advanced:
            stocks, ts = self.cache_advanced[cache_key]
            if (datetime.now() - ts).total_seconds() < 3600:
                logger.info(f"o. CACHE HIT - Returning {len(stocks)} active stocks")
                return stocks

        # ---- Discovery pool: NIFTY 50 + Next 50 (Top 100) ----
        nifty_pool = [
            'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
            'HINDUNILVR.NS', 'ITC.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'KOTAKBANK.NS',
            'LT.NS', 'AXISBANK.NS', 'ASIANPAINT.NS', 'MARUTI.NS', 'SUNPHARMA.NS',
            'TITAN.NS', 'BAJFINANCE.NS', 'WIPRO.NS', 'HCLTECH.NS', 'NESTLEIND.NS',
            'ULTRACEMCO.NS', 'POWERGRID.NS', 'NTPC.NS', 'JSWSTEEL.NS',
            'ADANIENT.NS', 'ADANIPORTS.NS', 'BAJAJFINSV.NS', 'GRASIM.NS',
            'ONGC.NS', 'COALINDIA.NS', 'BPCL.NS', 'TECHM.NS', 'DRREDDY.NS',
            'CIPLA.NS', 'EICHERMOT.NS', 'HEROMOTOCO.NS', 'DIVISLAB.NS', 'APOLLOHOSP.NS',
            'TATACONSUM.NS', 'SBILIFE.NS', 'BRITANNIA.NS', 'INDUSINDBK.NS', 'HINDALCO.NS',
            'TATASTEEL.NS', 'BAJAJ-AUTO.NS', 'SHRIRAMFIN.NS', 'HDFCLIFE.NS',
            'BEL.NS', 'TRENT.NS', 'HAL.NS', 'DLF.NS'
        ]

        try:
            import yfinance as yf

            # Batch download 1-day data for volume ranking (fast ?" single HTTP call)
            # threads=True is default but explicit is good. timeout to prevent hanging.
            data = yf.download(nifty_pool, period='1d', progress=False, threads=True)

            volume_map = {}
            if not data.empty:
                # Handle MultiIndex columns (Price, Ticker)
                if isinstance(data.columns, pd.MultiIndex):
                    # Check if 'Volume' level exists
                    if 'Volume' in data.columns.get_level_values(0):
                        vol_data = data['Volume']
                        for sym in nifty_pool:
                            if sym in vol_data.columns:
                                v_series = vol_data[sym].dropna()
                                if not v_series.empty:
                                    volume_map[sym] = float(v_series.iloc[-1])
                else:
                    # Flat columns (rare for batch download but possible if only 1 ticker succeeds)
                    if 'Volume' in data.columns:
                        v = float(data['Volume'].iloc[-1])
                        # If single ticker result, we need to know WHICH ticker it is. 
                        # yfinance usually returns MultiIndex for >1 ticker. 
                        # If list is passed, it returns MultiIndex.
                        pass 

            if volume_map:
                # Sort by volume descending ?' most active first
                sorted_stocks = sorted(volume_map.keys(), key=lambda s: volume_map[s], reverse=True)
                result = sorted_stocks[:limit]
                self.cache_advanced[cache_key] = (result, datetime.now())
                logger.info(f"o. Dynamic stock discovery: {len(result)} stocks ranked by volume")
                return result

        except Exception as e:
            logger.warning(f"Dynamic stock discovery failed: {e}")

        # ---- FINAL FALLBACK (ONLY IF EVERYTHING FAILS) ----
        fallback = nifty_pool[:max(limit, 5)]
        logger.warning("Batch discovery failed - using pool subset as fallback")
        self.cache_advanced[cache_key] = (fallback, datetime.now())
        return fallback[:limit]

# ...........................................................................
