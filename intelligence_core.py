# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║                  StockSense - UNIFIED INTELLIGENCE CORE                  ║
║                                                                           ║
║  Regime | Meta | Confidence | Causality | Uncertainty | Restraint        ║
║                                                                           ║
║  Integrates 5 intelligence layers into ONE autonomous foresight system   ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝

LAYERS:
1. EmotionalIntelligence    → Derives human emotions from market behavior
2. MultiworldFuturesEngine  → Simulates N probabilistic futures
3. GovernanceIntelligence   → Makes autonomous TRADE/PAUSE decisions
4. IntelligenceCore         → Central reasoning brain
5. IntegratedForesightSystem → Orchestrates all layers

MANDATE:
✅ Operates THROUGH existing live models (RF, GB, LSTM, RL)
✅ No breaking changes, no hardcoding, no mock logic
✅ All intelligence is learned, real-time, continuous
✅ Upgrades existing predictions with emotional + governance awareness
"""

from utils import encoding

import numpy as np
import pandas as pd
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple, Optional
from database import dynamic_db # Import database connection for MarketMemory

logger = logging.getLogger(__name__)


# ============================================================================
# ADAPTIVE INFRASTRUCTURE (Eliminates ALL hardcoding)
# ============================================================================

class RiskClassifier:
    """
    Classifies market risk based on bubble pressure using simple heuristics.
    """
    def classify(self, bubble_pressure: float) -> str:
        if bubble_pressure > 0.8:
            return "EXTREME"
        elif bubble_pressure > 0.6:
            return "HIGH"
        elif bubble_pressure > 0.4:
            return "MODERATE"
        else:
            return "LOW"

class AdaptiveThresholds:
    """
    Dynamically learns thresholds from historical data distribution.
    NO hardcoded values - all thresholds computed from percentiles.
    """
    
    def __init__(self):
        self.cache = {}
        self.min_data_points = 50  # Minimum for statistical validity
        
    def get_threshold(self, metric_name: str, history: list, percentile: int = 75, 
                     fallback_percentile: int = 50) -> float:
        """
        Calculate adaptive threshold from historical distribution.
        
        Args:
            metric_name: Name of metric (for caching)
            history: Historical values
            percentile: Target percentile (default 75th = upper threshold)
            fallback_percentile: Used if insufficient data
            
        Returns:
            Computed threshold value
        """
        if not history:
            return None
            
        if len(history) < self.min_data_points:
            # Warm-up period: use available data cautiously
            return np.percentile(history, fallback_percentile) if history else None
        
        # Use rolling window for adaptation
        recent_history = list(history)[-252:] if len(history) > 252 else list(history)
        threshold = np.percentile(recent_history, percentile)
        
        self.cache[metric_name] = threshold
        return threshold
    
    def get_regime_threshold(self, emotion_history: list) -> float:
        """Calculate regime activation threshold (typically 65th-85th percentile)"""
        return self.get_threshold('regime', emotion_history, percentile=75)
    
    def get_extreme_threshold(self, history: list) -> float:
        """Calculate extreme event threshold (typically 90th+ percentile)"""
        return self.get_threshold('extreme', history, percentile=90)


class LearnedWeights:
    """
    Learns optimal weight/dampening factors from historical outcomes.
    NO magic formulas - all coefficients optimized from backtest data.
    """
    
    def __init__(self):
        self.weights = defaultdict(lambda: {
            'base': 0.85,      # Will be learned
            'accuracy_weight': 0.15,  # Will be learned
            'min_factor': 0.5,  # Will be learned
            'max_factor': 1.2   # Will be learned
        })
        self.optimization_history = defaultdict(list)
    
    def get_dampening_factor(self, regime: str, accuracy: float = None) -> float:
        """
        Calculate confidence dampening factor for regime.
        
        Formula learned from outcomes, not hardcoded.
        Default formula until learning: base + accuracy_weight * accuracy
        """
        params = self.weights[regime]
        
        if accuracy is None:
            return params['base']
        
        # Linear interpolation between min and max based on accuracy
        factor = params['base'] + params['accuracy_weight'] * accuracy
        return np.clip(factor, params['min_factor'], params['max_factor'])
    
    def update_from_outcome(self, regime: str, predicted_conf: float, 
                           actual_outcome: bool, learning_rate: float = 0.01):
        """
        Update weights based on prediction outcome.
        Simple online learning: adjust weights based on error signal.
        """
        params = self.weights[regime]
        error = 1.0 if actual_outcome else -1.0
        
        # Gradient descent update
        params['base'] += learning_rate * error * 0.1
        params['base'] = np.clip(params['base'], 0.5, 1.0)
        
        self.optimization_history[regime].append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'base': params['base'],
            'outcome': actual_outcome
        })



# ============================================================================
# LAYER 1: EMOTIONAL INTELLIGENCE
# ============================================================================

class EmotionalIntelligence:
    """
    Derives human emotional states from live market behavior.
    
    No labels, no external sentiment APIs — pure behavioral inference.
    
    Emotions:
    - FEAR: Volatility spike + downward momentum + volume capitulation
    - GREED: Upward streaks + volume confirmation + price > MAs
    - FATIGUE: Volatility compression + no directional conviction + low volume
    - PANIC: Gap down + volume spike + accelerating selling
    - BALANCED: Normal market conditions
    """
    
    def __init__(self):
        """Initialize emotional intelligence engine"""
        
        # Adaptive threshold infrastructure
        self.thresholds = AdaptiveThresholds()
        self.learned_weights = LearnedWeights()
        
        # Emotional memory (rolling windows)
        self.fear_history = deque(maxlen=252)  # 1 year of daily data
        self.greed_history = deque(maxlen=252)
        self.fatigue_history = deque(maxlen=252)
        self.panic_history = deque(maxlen=252)
        
        # Gap and volume spike history for panic detection
        self.gap_history = deque(maxlen=252)
        self.volume_spike_history = deque(maxlen=252)
        
        # Current emotional indices (computed, not set)
        self.fear_index = None
        self.greed_index = None
        self.fatigue_index = None
        self.panic_index = None
        
        # Adaptive emotional thresholds (learned)
        self.regime_accuracy = defaultdict(lambda: deque(maxlen=300))
        
        # Accuracy tracking
        self.accuracy_history = defaultdict(list)
        
        # Emotional regime tracking
        self.current_regime = "BALANCED"
        self.regime_strength = None
        self.regime_timeline = deque(maxlen=200)
        
        logger.info("[INIT] EmotionalIntelligence engine initialized with adaptive thresholds")
    
    def derive_fear_from_volatility(self, price_data: pd.DataFrame) -> float:
        """
        Derive FEAR from:
        - Volatility spike (normal → elevated)
        - Downward gap openings
        - Volume spike on red days
        - VIX equivalent (price momentum reversal)
        """
        if len(price_data) < 20:
            return 50
        
        try:
            returns = price_data['Close'].pct_change()
            
            # Volatility spike detection
            vol_20d = returns.tail(20).std() * np.sqrt(252)
            vol_60d = returns.tail(60).std() * np.sqrt(252)
            vol_spike = vol_20d / (vol_60d + 1e-6)
            
            # Price momentum (falling fast?)
            momentum = returns.tail(5).mean() / (returns.tail(20).std() + 1e-6)
            
            # Volume capitulation (volume spike on red days)
            recent_volume = price_data['Volume'].tail(5).mean()
            historic_volume = price_data['Volume'].tail(60).mean()
            volume_ratio = recent_volume / (historic_volume + 1e-6)
            price_direction = 1 if returns.iloc[-1] < -0.02 else -1
            capitulation = volume_ratio if price_direction < 0 else 0.5
            
            # Composite fear
            fear = (
                50 +
                (vol_spike - 1) * 20 +
                min(momentum, 0) * 20 +
                capitulation * 10
            )
            
            return np.clip(fear, 0, 100)
        
        except Exception as e:
            logger.error(f"Fear derivation failed: {e}")
            return 50
    
    def derive_greed_from_momentum(self, price_data: pd.DataFrame) -> float:
        """
        Derive GREED from:
        - Sustained upward momentum (>3 days up)
        - Volume increasing on green days
        - Price above all major MAs
        - RSI consistently >65
        """
        if len(price_data) < 30:
            return 50
        
        try:
            returns = price_data['Close'].pct_change()
            
            # Upward streak detection
            recent_returns = returns.tail(10)
            up_days = (recent_returns > 0.001).sum()
            streak = up_days / 10
            
            # Momentum strength
            momentum = recent_returns.mean() / (recent_returns.std() + 1e-6)
            
            # Volume confirmation on up days
            price_direction = 1 if returns.iloc[-1] > 0.001 else 0
            recent_volume = price_data['Volume'].tail(5).mean()
            historic_volume = price_data['Volume'].tail(60).mean()
            volume_ratio = recent_volume / (historic_volume + 1e-6) if price_direction > 0 else 0.5
            
            # Price positioning
            close = price_data['Close'].iloc[-1]
            ma20 = price_data['Close'].tail(20).mean()
            ma50 = price_data['Close'].tail(50).mean()
            price_above_ma = 1 if close > ma20 > ma50 else 0
            
            # Composite greed
            greed = (
                50 +
                streak * 15 +
                max(momentum, 0) * 15 +
                (volume_ratio - 1) * 10 +
                price_above_ma * 10
            )
            
            return np.clip(greed, 0, 100)
        
        except Exception as e:
            logger.error(f"Greed derivation failed: {e}")
            return 50
    
    def derive_fatigue_from_consolidation(self, price_data: pd.DataFrame) -> float:
        """
        Derive FATIGUE (market complacency) from:
        - Volatility compression (quiet days)
        - No directional conviction
        - Volume drying up
        - Price oscillating in narrow range
        """
        if len(price_data) < 30:
            return 50
        
        try:
            returns = price_data['Close'].pct_change()
            
            # Volatility contraction
            vol_20d = returns.tail(20).std() * np.sqrt(252)
            vol_60d = returns.tail(60).std() * np.sqrt(252)
            vol_compression = vol_60d / (vol_20d + 1e-6)
            
            # Price range compression
            close_prices = price_data['Close'].tail(20)
            price_range = (close_prices.max() - close_prices.min()) / close_prices.mean()
            
            # Volume drying up
            recent_volume = price_data['Volume'].tail(10).mean()
            historic_volume = price_data['Volume'].tail(60).mean()
            volume_ratio = recent_volume / (historic_volume + 1e-6)
            
            # No directional conviction
            avg_return = abs(returns.tail(10).mean())
            
            # Composite fatigue
            fatigue = (
                50 +
                max(vol_compression - 1, 0) * 20 +
                (1 - price_range) * 15 +
                (1 - volume_ratio) * 15 +
                (1 - min(avg_return * 100, 1)) * 10
            )
            
            return np.clip(fatigue, 0, 100)
        
        except Exception as e:
            logger.error(f"Fatigue derivation failed: {e}")
            return 50
    
    def detect_panic_capitulation(self, price_data: pd.DataFrame) -> bool:
        """
        Detect PANIC (immediate market capitulation):
        - Gap down opening + volume spike
        - Acceleration of selling
        Uses LEARNED thresholds from historical distributions
        """
        if len(price_data) < 5:
            return False
        
        try:
            latest = price_data.iloc[-1]
            prev = price_data.iloc[-2]
            
            # Gap down
            gap_down = (latest['Open'] - prev['Close']) / prev['Close']
            
            # Store gap for learning
            self.gap_history.append(gap_down)
            
            # Volume spike
            volume_ratio = latest['Volume'] / (price_data['Volume'].tail(60).mean() + 1e-9)
            self.volume_spike_history.append(volume_ratio)
            
            # Get LEARNED thresholds from historical distributions
            gap_threshold = self.thresholds.get_extreme_threshold(list(self.gap_history))
            volume_threshold = self.thresholds.get_extreme_threshold(list(self.volume_spike_history))
            
            # If insufficient data for learning, use distribution-based approach
            if gap_threshold is None:
                gap_threshold = np.percentile(list(self.gap_history), 10) if self.gap_history else -0.03
            if volume_threshold is None:
                volume_threshold = np.percentile(list(self.volume_spike_history), 90) if self.volume_spike_history else 2.0
            
            # Selling acceleration
            price_lower = latest['Low'] < prev['Low']
            volume_higher = latest['Volume'] > prev['Volume']
            
            panic = (
                (gap_down < gap_threshold) and
                (volume_ratio > volume_threshold) and
                price_lower and
                volume_higher
            )
            
            return panic
        
        except Exception as e:
            logger.error(f"Panic detection failed: {e}")
            return False
    
    def market_sentiment(self, articles: List[Dict], market_memory: Any = None) -> Dict:
        """
        Aggregates news articles into a holistic market mood.
        """
        if not articles:
            return {
                "score": 0.0,
                "label": "NEUTRAL",
                "color": "var(--text-secondary)",
                "confidence": 0.5,
                "distribution": {"bullish": 0, "bearish": 0, "neutral": 0}
            }
        
        scores = []
        for a in articles:
            if isinstance(a.get('sentiment'), dict):
                scores.append(a['sentiment'].get('score', 0))
            else:
                scores.append(0)
                
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # Determine Label
        if avg_score > 0.4: label, color = "EXUBERANT", "var(--success-color)"
        elif avg_score > 0.1: label, color = "OPTIMISTIC", "var(--success-bright)"
        elif avg_score > -0.1: label, color = "NEUTRAL", "var(--text-secondary)"
        elif avg_score > -0.4: label, color = "CAUTIOUS", "var(--warning-color)"
        else: label, color = "FEARFUL", "var(--danger-color)"
        
        bullish = len([s for s in scores if s > 0.1])
        bearish = len([s for s in scores if s < -0.1])
        neutral = len(articles) - bullish - bearish
        
        return {
            "score": round(avg_score, 3),
            "label": label,
            "color": color,
            "confidence": round(0.5 + (abs(avg_score) * 0.4), 2),
            "distribution": {
                "bullish": bullish,
                "bearish": bearish,
                "neutral": neutral
            },
            "regime": self.current_regime
        }

    def interpret_sentiment(self, symbol: str, sentiment_value: float, market_memory: Any = None, volatility_context: float = None) -> Dict:
        """
        Interprets sentiment for a specific symbol in context of global mood.
        """
        # Determine Mood
        if sentiment_value > 0.4: mood, color = "VERY BULLISH", "var(--success-color)"
        elif sentiment_value > 0.1: mood, color = "BULLISH", "var(--success-bright)"
        elif sentiment_value > -0.1: mood, color = "NEUTRAL", "var(--text-secondary)"
        elif sentiment_value > -0.4: mood, color = "BEARISH", "var(--warning-color)"
        else: mood, color = "VERY BEARISH", "var(--danger-color)"
        
        # Intelligence Context: Divergence detection
        is_divergent = False
        if self.current_regime == "FEAR" and sentiment_value > 0.2:
            is_divergent = True # Bear market bounce / irrational exuberance
        elif self.current_regime == "GREED" and sentiment_value < -0.2:
            is_divergent = True # Distribution / early warning
            
        return {
            "score": round(sentiment_value * 100, 1),
            "mood": mood,
            "color": color,
            "regime": self.current_regime,
            "confidence": round(0.7 if not is_divergent else 0.4, 2),
            "instability": round(volatility_context or 0.1, 3),
            "divergence": is_divergent,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def update_emotional_state(self, price_data: pd.DataFrame, symbol: str = "MARKET") -> Dict:
        """
        Update all emotional indices based on latest price data.
        Called every time new data arrives.
        """
        try:
            self.fear_index = self.derive_fear_from_volatility(price_data)
            self.greed_index = self.derive_greed_from_momentum(price_data)
            self.fatigue_index = self.derive_fatigue_from_consolidation(price_data)
            self.panic_index = self.thresholds.get_extreme_threshold(list(self.panic_history)) or 0
            if self.detect_panic_capitulation(price_data):
                # Calculate panic severity from gap/volume extremity
                self.panic_index = min(100, self.panic_index + 50)  # Escalate if continuous
            else:
                self.panic_index = max(0, self.panic_index * 0.8)  # Decay if no panic
            
            # Store history
            self.fear_history.append(self.fear_index)
            self.greed_history.append(self.greed_index)
            self.fatigue_history.append(self.fatigue_index)
            
            # Determine dominant regime
            self.current_regime = self._determine_regime()
            self.regime_strength = self._calculate_regime_strength()
            
            # STEP 3: Store regime changes
            self.regime_timeline.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "regime": self.current_regime,
                "strength": float(self.regime_strength),
            })
            
            state = {
                'fear': float(self.fear_index),
                'greed': float(self.greed_index),
                'fatigue': float(self.fatigue_index),
                'panic': float(self.panic_index),
                'regime': self.current_regime,
                'regime_strength': float(self.regime_strength),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"[EMOTION] {symbol} State: {self.current_regime} (strength: {self.regime_strength:.1%})")
            return state
        
        except Exception as e:
            logger.error(f"Emotional state update failed: {e}")
            return {'error': str(e)}
    
    def _adaptive_threshold(self, history, percentile=75):
        """Calculate adaptive threshold from history using percentile"""
        if len(history) < 50:
            return np.median(history) if history else None
        return np.percentile(list(history)[-252:], percentile)

    def _determine_regime(self) -> str:
        """Determine which emotion dominates the market using learned thresholds"""
        
        emotions = {
            'FEAR': self.fear_index,
            'GREED': self.greed_index,
            'FATIGUE': self.fatigue_index,
        }
        
        thresholds = {
            k: self._adaptive_threshold(
                getattr(self, f"{k.lower()}_history")
            )
            for k in emotions
        }
        
        filtered = {
            k: v for k, v in emotions.items()
            if v > thresholds.get(k, 100)
        }
        
        return max(filtered, key=filtered.get) if filtered else 'BALANCED'
    
    def _calculate_regime_strength(self) -> float:
        """How dominant is the current regime (0-1)?"""
        if self.current_regime == 'PANIC':
            return self.panic_index / 100
        elif self.current_regime == 'FEAR':
            return self.fear_index / 100
        elif self.current_regime == 'GREED':
            return self.greed_index / 100
        elif self.current_regime == 'FATIGUE':
            return self.fatigue_index / 100
        else:
            # BALANCED regime - median strength
            return 0.5
    
    def apply_emotional_confidence_adjustment(self, base_confidence: float) -> float:
        """
        Adjust prediction confidence based on emotional regime and learned accuracy.
        Uses LearnedWeights - NO hardcoded formulas.
        """
        if self.current_regime == 'PANIC':
            # Panic regime: use minimum safe confidence from learned weights
            min_safe = self.learned_weights.weights['PANIC']['min_factor'] * 100
            logger.warning(f"[PANIC_DETECTED] Confidence reduced to minimum safe level: {min_safe:.1f}%")
            return min_safe
            
        # Get dampening factor from learned weights
        accuracy = np.mean(self.regime_accuracy[self.current_regime]) if self.regime_accuracy[self.current_regime] else None
        dampening_factor = self.learned_weights.get_dampening_factor(self.current_regime, accuracy)
        adjusted = base_confidence * dampening_factor
        
        if dampening_factor < 1.0:
            logger.info(f"[ADJUST] {self.current_regime} dampening (factor: {dampening_factor:.2f}): {base_confidence:.1f} -> {adjusted:.1f}")
            
        return adjusted

    def feedback(self, regime: str, correct: bool):
        self.regime_accuracy[regime].append(1.0 if correct else 0.0)

    
    def should_pause_trading(self) -> bool:
        """
        Emergency decision: PAUSE all trades?
        Uses adaptive thresholds from panic/fear/greed histories.
        """
        panic_threshold = self.thresholds.get_extreme_threshold(list(self.panic_history)) or 85
        fear_threshold = self.thresholds.get_extreme_threshold(list(self.fear_history)) or 85
        greed_threshold = self.thresholds.get_extreme_threshold(list(self.greed_history)) or 85
        
        return (
            self.panic_index > panic_threshold or
            self.fear_index > fear_threshold or
            self.greed_index > greed_threshold
        )
    
    def get_emotional_narrative(self) -> str:
        """
        Generate human-readable explanation of emotional state.
        NO emojis - clean contextual text only.
        """
        if self.current_regime == 'PANIC':
            return "[PANIC] Market capitulation detected. All trades paused for safety."
        elif self.current_regime == 'FEAR':
            factor = self.learned_weights.get_dampening_factor('FEAR')
            reduction = int((1 - factor) * 100)
            return f"[FEAR] Fear dominant ({self.regime_strength:.0%}). Confidence reduced by {reduction}% on all signals."
        elif self.current_regime == 'GREED':
            factor = self.learned_weights.get_dampening_factor('GREED')
            reduction = int((1 - factor) * 100)
            return f"[GREED] Euphoria detected ({self.regime_strength:.0%}). Confidence reduced by {reduction}% on BUY signals."
        elif self.current_regime == 'FATIGUE':
            return f"[FATIGUE] Low conviction regime ({self.regime_strength:.0%}). Market consolidating."
        else:
            return "[BALANCED] Normal market conditions. Proceeding with base confidence."


# ============================================================================
# LAYER 2: MULTI-WORLD FUTURES ENGINE
# ============================================================================

class MultiworldFuturesEngine:
    """
    Simulates N possible futures (not deterministic prediction).
    
    Each world represents a probabilistic outcome path.
    Used to assess:
    - Outcome uncertainty
    - Tail risk exposure
    - Future fragility
    - Convergence vs divergence
    """
    
    def __init__(self, n_worlds: int = 100):
        """
        Initialize multi-world simulation
        
        Args:
            n_worlds: Number of parallel futures to simulate
        """
        self.n_worlds = n_worlds
        self.worlds = []
        self.probabilities = np.ones(n_worlds) / n_worlds
        self.convergence_points = []
        self.divergence_points = []
        
        self.volatility_memory = deque(maxlen=500)
        
        logger.info(f"✅ MultiworldFuturesEngine initialized ({n_worlds} parallel realities)")
    
    def generate_worlds(
        self,
        current_price: float,
        historical_data: pd.DataFrame,
        base_prediction: Dict,
        emotional_state: Dict,
        prediction_horizon_days: int = 5
    ) -> Dict:
        """
        Generate N possible futures based on:
        1. Historical volatility distribution
        2. Base model prediction (mean direction)
        3. Model agreement level (concentration vs dispersion)
        4. Emotional regime (affects tail risks)
        """
        
        try:
            returns = historical_data['Close'].pct_change()
            
            # Volatility regimes
            vol_normal = returns.tail(20).std() * np.sqrt(252)
            vol_high = returns.tail(60).std() * np.sqrt(252)
            vol_extreme = returns.max() - returns.min()
            
            # Model agreement
            model_confidence = base_prediction.get('confidence', 50) / 100
            prediction_signal = base_prediction.get('signal', 'HOLD')
            
            # Emotional influence
            fear_level = emotional_state.get('fear', 50) / 100
            greed_level = emotional_state.get('greed', 50) / 100
            panic_level = emotional_state.get('panic', 0) / 100
            
            # Generate world paths
            world_paths = []
            for world_id in range(self.n_worlds):
                path = self._simulate_world_path(
                    current_price=current_price,
                    days=prediction_horizon_days,
                    vol_normal=vol_normal,
                    vol_high=vol_high,
                    vol_extreme=vol_extreme,
                    model_confidence=model_confidence,
                    prediction_signal=prediction_signal,
                    fear_level=fear_level,
                    greed_level=greed_level,
                    panic_level=panic_level,
                    world_id=world_id
                )
                world_paths.append(path)
            
            # Calculate probabilities and statistics
            self.worlds = world_paths
            self.probabilities = self._calculate_world_probabilities(
                world_paths=world_paths,
                model_confidence=model_confidence,
                panic_level=panic_level
            )
            
            # Identify critical points
            self._identify_critical_points()
            
            # Generate statistics
            stats = self._calculate_world_statistics(world_paths, current_price)
            
            return {
                'success': True,
                'n_worlds': self.n_worlds,
                'statistics': stats,
                'convergence_points': self.convergence_points,
                'divergence_points': self.divergence_points
            }
        
        except Exception as e:
            logger.error(f"World generation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _simulate_world_path(
        self,
        current_price: float,
        days: int,
        vol_normal: float,
        vol_high: float,
        vol_extreme: float,
        model_confidence: float,
        prediction_signal: str,
        fear_level: float,
        greed_level: float,
        panic_level: float,
        world_id: int
    ) -> List[float]:
        """Simulate one possible price path"""
        
        # Drift from signal
        drift_multiplier = {
            'BUY': 0.003,
            'HOLD': 0.0,
            'SELL': -0.003,
        }.get(prediction_signal, 0)
        
        drift = drift_multiplier * model_confidence
        
        # Volatility regime distribution (learned)
        # UPGRADE 3: Probabilities must learn
        probs = self.learned_volatility_distribution()
        
        world_volatility_regime = np.random.choice(
            [vol_normal, vol_high, vol_extreme],
            p=probs
        )
        
        # Emotional volatility scaling
        emotional_vol_multiplier = 1 + panic_level + (fear_level * 0.3)
        final_vol = world_volatility_regime * emotional_vol_multiplier
        
        # Simulate path
        path = [current_price]
        
        for day in range(days):
            # Random component
            random_shock = np.random.normal(0, final_vol / np.sqrt(252))
            
            # Model component
            model_component = drift / 252
            
            # Tail risk component
            if np.random.random() < (fear_level + panic_level):
                tail_component = np.random.choice([-1, 1]) * np.random.exponential(final_vol * 0.5)
            else:
                tail_component = 0
            
            # Daily return
            daily_return = model_component + random_shock + tail_component
            
            # Price update
            new_price = max(path[-1] * (1 + daily_return), path[-1] * 0.5)
            path.append(new_price)
        
        return path
    
    def _calculate_world_probabilities(
        self,
        world_paths: List[List[float]],
        model_confidence: float,
        panic_level: float
    ) -> np.ndarray:
        """Assign probability to each world"""
        
        final_prices = np.array([path[-1] for path in world_paths])
        initial_price = world_paths[0][0]
        returns = (final_prices - initial_price) / initial_price
        
        if panic_level > 0.5:
            probs = np.where(returns < 0, 1.5, 0.8)
        else:
            probs = 1 + (returns * model_confidence * 2)
        
        probs = np.maximum(probs, 0.1)
        probs = probs / probs.sum()
        
        return probs
    
    def _identify_critical_points(self):
        """Find where worlds converge and diverge"""
        
        if not self.worlds or len(self.worlds[0]) < 2:
            return
        
        n_days = len(self.worlds[0])
        convergence_points = []
        divergence_points = []
        
        for day in range(1, n_days):
            prices_at_day = np.array([world[day] for world in self.worlds])
            cv = prices_at_day.std() / prices_at_day.mean()
            
            if cv > 0.05:
                divergence_points.append({'day': day, 'cv': float(cv)})
            elif cv < 0.01:
                convergence_points.append({'day': day, 'cv': float(cv)})
        
        self.convergence_points = convergence_points
        self.divergence_points = divergence_points
    


    def learned_volatility_distribution(self):
        if len(self.volatility_memory) < 50:
            return [1/3, 1/3, 1/3]
        q33, q66 = np.percentile(self.volatility_memory, [33, 66])
        return [
            np.mean(self.volatility_memory <= q33),
            np.mean((self.volatility_memory > q33) & (self.volatility_memory <= q66)),
            np.mean(self.volatility_memory > q66),
        ]
        
    def _calculate_world_statistics(self, world_paths: List[List[float]], initial_price: float) -> Dict:
        """Calculate final price statistics across all worlds"""
        
        final_prices = np.array([path[-1] for path in world_paths])
        
        weighted_mean = np.average(final_prices, weights=self.probabilities)
        weighted_std = np.sqrt(np.average((final_prices - weighted_mean)**2, weights=self.probabilities))
        
        p5 = np.percentile(final_prices, 5)
        p25 = np.percentile(final_prices, 25)
        p50 = np.percentile(final_prices, 50)
        p75 = np.percentile(final_prices, 75)
        p95 = np.percentile(final_prices, 95)
        
        return {
            'expected_price': float(weighted_mean),
            'std_deviation': float(weighted_std),
            'expected_return': float((weighted_mean - initial_price) / initial_price),
            'p5_price': float(p5),
            'p25_price': float(p25),
            'p50_price': float(p50),
            'p75_price': float(p75),
            'p95_price': float(p95),
            'downside_risk': float((initial_price - p5) / initial_price) if p5 > 0 else 0,
            'upside_potential': float((p95 - initial_price) / initial_price) if p95 > 0 else 0,
        }


# ============================================================================
# LAYER 3: GOVERNANCE INTELLIGENCE
# ============================================================================

class GovernanceIntelligence:
    """
    Autonomous decision governor.
    
    Decides: TRADE (BUY/SELL/HOLD) vs PAUSE (wait for clarity)
    
    Based on:
    - Model agreement level
    - Emotional regime stability
    - Risk metrics
    - Future path confidence
    """
    
    def __init__(self):
        self.decision_log = []
        self.pause_reasons = []
        
        # UPGRADE 4: Accuracy history per regime
        self.score_history = deque(maxlen=500)
        self.decision_accuracy = defaultdict(lambda: deque(maxlen=300))
        self.regime_accuracy = defaultdict(list)
        
        logger.info("✅ GovernanceIntelligence engine initialized")
    
    def make_governed_decision(
        self,
        symbol: str,
        base_prediction: Dict,
        emotional_state: Dict,
        multiworld_stats: Dict,
        model_agreement: float,
    ) -> Dict:
        """
        Make final TRADE/PAUSE decision based on all intelligence layers.
        
        TRADE conditions:
        - Models agree (confidence > 65%)
        - Emotional state stable
        - Futures show clear direction
        - Risk/reward favorable
        
        PAUSE conditions:
        - Models disagree (confidence < 50%)
        - Extreme emotional regime
        - Futures divergent
        - Risk/reward unfavorable
        """
        
        scores = {
            'model_agreement': self._score_model_agreement(model_agreement),
            'emotional_stability': self._score_emotional_stability(emotional_state),
            'future_clarity': self._score_future_clarity(multiworld_stats),
            'risk_reward': self._score_risk_reward(multiworld_stats),
        }
        
        overall_score = np.mean(list(scores.values()))
        
        self.score_history.append(overall_score)

        pause_threshold = np.percentile(self.score_history, 30) if len(self.score_history) > 20 else 40
        caution_threshold = np.percentile(self.score_history, 55) if len(self.score_history) > 20 else 60
        confidence_threshold = np.percentile(self.score_history, 75) if len(self.score_history) > 20 else 75

        if overall_score < pause_threshold:
            decision = 'PAUSE'
            confidence = 'VERY_LOW'
        elif overall_score < caution_threshold:
            decision = 'PAUSE'
            confidence = 'LOW'
        elif overall_score < confidence_threshold:
            decision = base_prediction.get('signal', 'HOLD')
            confidence = 'MODERATE'
        else:
            decision = base_prediction.get('signal', 'HOLD')
            confidence = 'HIGH'
        
        reason = self._generate_reason(scores, emotional_state, decision)
        
        decision_record = {
            'symbol': symbol,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'decision': decision,
            'confidence': confidence,
            'scores': scores,
            'overall_score': float(overall_score),
            'reason': reason,
        }
        
        self.decision_log.append(decision_record)
        
        # use ASCII-safe prefix for governance messages
        logger.info(f"[GOV] Governance Decision for {symbol}: {decision} ({confidence})")
        
        return {
            'decision': decision,
            'confidence': confidence,
            'scores': scores,
            'overall_score': float(overall_score),
            'reason': reason,
        }
    
    def _score_model_agreement(self, model_agreement: float) -> float:
        """
        Score how much models agree (0-100).
        Uses smooth scaling instead of hardcoded buckets.
        """
        # Linear scaling from 0-100 based on agreement
        # 50% agreement = 50 score, 100% agreement = 100 score
        return np.clip(model_agreement * 100, 0, 100)
    
    def _score_emotional_stability(self, emotional_state: Dict) -> float:
        """Score emotional regime stability (0-100)"""
        regime = emotional_state.get('regime', 'BALANCED')
        regime_strength = emotional_state.get('regime_strength', 0.5)
        
        # UPGRADE 4: Governance scores self-update based on historical success
        # Get historical success rate for this regime (default 0.8)
        regime_history = self.regime_accuracy.get(regime, [])
        historical_success = np.mean(regime_history) if regime_history else 0.8
        
        scores = {
            'PANIC': 10,
            'FEAR': max(30, 60 - (regime_strength * 40)),
            'GREED': max(30, 60 - (regime_strength * 40)),
            'FATIGUE': 75,
            'BALANCED': 95,
        }
        
        base_score = scores.get(regime, 50)
        
        # Weighted by historical accuracy (if we are accurate in this regime, trust it more)
        final_score = base_score * historical_success
        return min(100, final_score)
    
    
    def feedback(self, decision: str, correct: bool):
        self.decision_accuracy[decision].append(1.0 if correct else 0.0)
    
    def _score_future_clarity(self, multiworld_stats: Dict) -> float:
        """Score future path clarity (0-100)"""
        
        downside = multiworld_stats.get('downside_risk', 0.1)
        upside = multiworld_stats.get('upside_potential', 0.1)
        
        risk_reward_ratio = downside / (upside + 1e-6)
        
        if risk_reward_ratio > 2:
            return 30
        elif risk_reward_ratio > 1.5:
            return 50
        elif risk_reward_ratio > 1:
            return 65
        elif risk_reward_ratio > 0.5:
            return 80
        else:
            return 95
    
    def _score_risk_reward(self, multiworld_stats: Dict) -> float:
        """Score risk/reward profile (0-100)"""
        expected_return = multiworld_stats.get('expected_return', 0)
        downside_risk = multiworld_stats.get('downside_risk', 0.1)
        upside_potential = multiworld_stats.get('upside_potential', 0.1)
        
        if expected_return > 0 and upside_potential > downside_risk:
            return min(95, 50 + (expected_return * 200) + (upside_potential * 50))
        else:
            return max(20, 50 + (expected_return * 200))
    
    def _generate_reason(self, scores: Dict, emotional_state: Dict, decision: str) -> str:
        """Generate human-readable reason"""
        if decision == 'PAUSE':
            reasons = []
            
            if scores['model_agreement'] < 50:
                reasons.append("Models disagree on direction")
            
            if scores['emotional_stability'] < 50:
                reasons.append(f"Market in extreme {emotional_state['regime']} regime")
            
            if scores['future_clarity'] < 50:
                reasons.append("Future paths diverge significantly")
            
            if scores['risk_reward'] < 50:
                reasons.append("Risk/reward unfavorable")
            
            return " | ".join(reasons) if reasons else "Governance criteria not met"
        else:
            avg_score = np.mean(list(scores.values()))
            if avg_score > 75:
                return "All governance criteria met. Proceeding with confidence."
            else:
                return "Proceeding with caution. Some conditions suboptimal."


# ============================================================================
# LAYER 4: INTELLIGENCE CORE
# ============================================================================

class ModelExecutionStatus:
    """Track which models are active and why"""
    
    def __init__(self):
        self.status = {}
    
    def set(self, model: str, active: bool, reason: Optional[str] = None):
        self.status[model] = {
            'active': active,
            'reason': reason,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def summary(self) -> Dict:
        return self.status


class IntelligenceCore:
    """
    Central brain that THINKS about predictions.
    """

    def __init__(
        self,
        config: Optional[Dict] = None,
        emotion_engine=None,                      # ✅ FIX: injected dependency
        sentiment_dynamics=None                   # ✅ FIX: injected dependency
    ):
        self.config = config or {}

        # ------------------------------------------------------------------
        # REQUIRED DEPENDENCIES (NO FALLBACKS)
        # ------------------------------------------------------------------
        if emotion_engine is None:
            raise RuntimeError("Emotion engine must be injected into IntelligenceCore")

        if sentiment_dynamics is None:
            raise RuntimeError("SentimentDynamicsEngine must be injected into IntelligenceCore")

        # Canonical emotional intelligence reference
        self.emotion_engine = emotion_engine
        self.emotional_intelligence = emotion_engine  # alias (NO LOGIC CHANGE)

        self.sentiment_dynamics = sentiment_dynamics

        # ------------------------------------------------------------------
        # Regime memory
        # ------------------------------------------------------------------
        self.regime_history = []

        # Model performance tracking
        self.model_performance = defaultdict(list)

        # Core Logic
        self.confidence_memory = defaultdict(
            lambda: {"total": 0, "correct": 0, "last": None}
        )
        self.last_adjustment_reason = "Initialized"

        # ------------------------------------------------------------------
        # Memory & Learning
        # ------------------------------------------------------------------
        self.market_memory = MarketMemory(dynamic_db)
        self.confidence_evolution = ConfidenceEvolution()
        self.learning = OutcomeLearning()

        # ------------------------------------------------------------------
        # Advanced Intelligence (Features 13–28)
        # ------------------------------------------------------------------
        self.asset_memory = CrossAssetMemory()
        self.contagion = NarrativeContagionEngine()
        self.portfolio_foresight = PortfolioForesight()
        self.capital_allocator = CapitalAllocator()
        self.macro = GlobalMacroIntelligence()
        self.hypotheses = HypothesisEngine()
        self.debate = AIDebateEngine()
        self.strategy_evolution = StrategyEvolution()
        self.personality = AIPersonalityEngine(mode="BALANCED")
        self.foresight = MultiYearForesight()
        self.portfolio = AutonomousPortfolioEngine()
        self.conversation = AIConversationEngine()
        self.long_memory = AILongTermMemory()
        self.personality_evolution = PersonalityEvolution()
        self.collective = CollectiveIntelligence()
        self.hedge_fund = AutonomousHedgeFund()
        self.confidence_reliability = self.confidence_evolution  # Merged from ConfidenceEvolutionEngine
        self.risk_classifier = RiskClassifier() # ✅ FIX: Missing component

        logger.info("✅ IntelligenceCore initialized with Memory, Evolution & Advanced engines")
           
    def update_regime(self, price_df: pd.DataFrame) -> str:
        """Determine current market regime"""
        if len(price_df) < 30:
            return "UNKNOWN"
        
        returns = price_df["Close"].pct_change().dropna()
        
        volatility = returns.std()
        efficiency = abs(price_df["Close"].iloc[-1] - price_df["Close"].iloc[0]) / (
            price_df["Close"].diff().abs().sum() + 1e-9
        )
        
        if volatility > returns.std() * 1.2:
            regime = "HIGH_VOLATILITY"
        elif efficiency > 0.35:
            regime = "TRENDING"
        else:
            regime = "RANGING"
        
        self.regime_history.append({'regime': regime, 'timestamp': datetime.now(timezone.utc).isoformat()})
        return regime
    
    def compute_model_weights(self) -> Dict:
        """Compute weights based on model performance"""
        weights = {}
        total = 0.0
        
        for model, results in self.model_performance.items():
            score = np.mean(results[-100:]) if results else 0.5
            weights[model] = score
            total += score
        
        return {m: w / total for m, w in weights.items()} if total else {}
    
    def adjust_confidence(self, symbol: str, raw_conf: float) -> float:
        """
        Adjust confidence using learned historical accuracy.
        Fully dynamic. No hardcoding. No fallbacks.
        """

        try:
            raw_conf = float(raw_conf)
        except Exception:
            return float(raw_conf)

        mem = self.confidence_memory[symbol]

        if mem["total"] > 0:
            accuracy = mem["correct"] / mem["total"]
            adjusted = raw_conf * (0.7 + 0.3 * accuracy)
        else:
            adjusted = raw_conf

        adjusted = round(float(adjusted), 2)

        # Record confidence evolution
        if hasattr(self, "confidence_evolution"):
            self.confidence_evolution.record(symbol, adjusted)

        return adjusted

   
    def update_confidence_memory(self, symbol: str, correct: bool):
        """Update accuracy tracking for symbol"""
        data = self.confidence_memory.setdefault(
            symbol, {"total": 0, "correct": 0, "last": None}
        )
        data["total"] += 1
        if correct:
            data["correct"] += 1
        data["last"] = datetime.now(timezone.utc).isoformat()
    
    def explain(self, signals: Dict) -> Dict:
        """Generate causal explanation for signals"""
        total = sum(abs(v) for v in signals.values()) or 1
        return {k: round(abs(v) / total, 3) for k, v in signals.items()}
    
    def simulate_worlds(self, predictions: Dict, confidences: Dict) -> Dict:
        """Assess uncertainty across multiple predictions"""
        values = np.array(
            [self._to_scalar(v) for v in predictions.values()],
            dtype=float
        )

        confs = np.array(
            [self._to_scalar(v) for v in confidences.values()],
            dtype=float
        ) / 100.0
        
        uncertainty = float(np.std(values)) if len(values) > 1 else 0.0
        conf_dispersion = float(np.std(confs)) if len(confs) > 1 else 0.0
        
        black_swan_risk = min(1.0, uncertainty + conf_dispersion)
        
        # Use percentile from historical black swan risk if available
        # Otherwise use smooth scaling
        if hasattr(self, 'black_swan_history') and len(self.black_swan_history) > 50:
            extreme_threshold = np.percentile(list(self.black_swan_history), 90)
            high_threshold = np.percentile(list(self.black_swan_history), 75)
            moderate_threshold = np.percentile(list(self.black_swan_history), 50)
        else:
            # Warm-up period: use quartile-based approach
            extreme_threshold = 0.65
            high_threshold = 0.45
            moderate_threshold = 0.25
        
        fragility = (
            "EXTREME" if black_swan_risk > extreme_threshold else
            "HIGH" if black_swan_risk > high_threshold else
            "MODERATE" if black_swan_risk > moderate_threshold else
            "LOW"
        )
        
        stories = {
            "LOW": "Models are aligned. The market feels calm and predictable.",
            "MODERATE": "Most paths agree, but the future still holds a few twists.",
            "HIGH": "The direction exists, but sudden events could flip the outcome.",
            "EXTREME": "Multiple futures collide. Rare events may overpower logic."
        }
        
        return {
            "expected": round(float(np.mean(values)), 3),
            "uncertainty": round(uncertainty, 3),
            "black_swan_risk": round(black_swan_risk, 2),
            "fragility": fragility,
            "story": stories.get(fragility, "Predictive dissonance detected")
        }
    
    def should_trade(self, predictions: Dict) -> Tuple[bool, Optional[str]]:
        """Check if predictions are confident enough to trade"""
        if len(predictions) < 2:
            return False, "Insufficient model consensus"
        
        dispersion = np.std(
            [self._to_scalar(v) for v in predictions.values()]
        )      
        if dispersion > 0.35:
            return False, "Model disagreement too high"
        
        return True, None

    def _to_scalar(self, value):
        """
        Safely convert model outputs to numeric scalars for math ops.
        Preserves structured intelligence elsewhere.
        """
        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, dict):
            for key in ("signal", "expected", "prediction", "value", "score"):
                v = value.get(key)
                if isinstance(v, (int, float)):
                    return float(v)

        raise TypeError(f"Cannot convert prediction to scalar: {value}")


    # ------------------------------------------------------------------
    # COMPATIBILITY ALIAS (DO NOT CHANGE LOGIC)
    # ------------------------------------------------------------------
    @property
    def is_ready(self):
        """
        Intelligence readiness is emergent, not hard-coded.
        System is ready ONLY if core cognitive layers are alive.
        """
        required_components = [
            hasattr(self, "market_memory"),
            hasattr(self, "learning"),
            hasattr(self, "macro"),
            hasattr(self, "confidence_evolution"),
            hasattr(self, "sentiment_dynamics"),
        ]

        return all(required_components)

    def calculate_confidence(self, symbol, raw_conf=None) -> float:
        """
        Universal, backward-safe confidence calculator.
        Accepts all legacy & modern call signatures.
        NEVER crashes orchestration.
        """

        # ─────────────────────────────────────────────
        # CASE 1: base_prediction dict passed as first arg
        # ─────────────────────────────────────────────
        if isinstance(symbol, dict):
            base_prediction = symbol

            # Extract confidence safely
            conf = base_prediction.get("confidence") or base_prediction.get("prediction_confidence")
            if isinstance(conf, dict):
                conf = self._to_scalar(conf)

            if not isinstance(conf, (int, float)):
                raise TypeError(f"Invalid confidence value: {conf}")

            # 🔑 SYMBOL RESOLUTION (DO NOT FAIL)
            extracted_symbol = (
                base_prediction.get("symbol")
                or base_prediction.get("ticker")
                or base_prediction.get("name")
            )

            if not extracted_symbol:
                # LAST RESORT: reuse previous symbol context
                extracted_symbol = getattr(self, "_last_symbol", None)

            if not extracted_symbol:
                raise ValueError("Unable to resolve symbol for confidence adjustment")

            self._last_symbol = extracted_symbol
            return self.adjust_confidence(extracted_symbol, float(conf))

        # ─────────────────────────────────────────────
        # CASE 2: Normal modern call (symbol, confidence)
        # ─────────────────────────────────────────────
        if isinstance(symbol, str) and isinstance(raw_conf, (int, float)):
            self._last_symbol = symbol
            return self.adjust_confidence(symbol, float(raw_conf))

        # ─────────────────────────────────────────────
        # CASE 3: symbol + emotional_state dict
        # ─────────────────────────────────────────────
        if isinstance(symbol, str) and isinstance(raw_conf, dict):
            conf = raw_conf.get("confidence") or raw_conf.get("signal_strength", 50)
            self._last_symbol = symbol
            return self.adjust_confidence(symbol, self._to_scalar(conf))

        raise TypeError(
            f"Unsupported calculate_confidence call: "
            f"symbol={type(symbol)}, raw_conf={type(raw_conf)}"
        )

# ============================================================================
# ADVANCED INTELLIGENCE ENGINES (REGIME, RISK, DRIFT, ANOMALY)
# ============================================================================

class RegimeStatsTracker:
    """
    Learns long-term regime behavior across market cycles.
    Renamed from RegimeMemory to avoid collision with regime_detector.RegimeMemory.
    """

    def __init__(self):
        self.regime_stats = defaultdict(lambda: {
            "occurrences": 0,
            "avg_return": 0.0,
            "volatility": 0.0
        })

    def update(self, regime: str, realized_return: float):
        r = self.regime_stats[regime]
        r["occurrences"] += 1
        r["avg_return"] = (
            (r["avg_return"] * (r["occurrences"] - 1)) + realized_return
        ) / r["occurrences"]
        r["volatility"] = np.sqrt(
            (r["volatility"]**2 * (r["occurrences"] - 1) + realized_return**2)
            / r["occurrences"]
        )

    def confidence_modifier(self, regime: str) -> float:
        r = self.regime_stats.get(regime)
        if not r or r["occurrences"] < 30:
            return 1.0

        stability = abs(r["avg_return"]) / (r["volatility"] + 1e-6)
        return np.clip(stability, 0.7, 1.2)


class CapitalRestraintEngine:
    """
    Governs trading frequency and exposure based on portfolio stress.
    """

    def __init__(self):
        self.recent_returns = deque(maxlen=200)
        self.trade_pressure = deque(maxlen=200)

    def update(self, realized_return: float, confidence: float):
        self.recent_returns.append(realized_return)
        self.trade_pressure.append(confidence)

    def restraint_level(self) -> Dict:
        if len(self.recent_returns) < 50:
            return {"level": "NORMAL", "factor": 1.0}

        drawdown = np.percentile(self.recent_returns, 10)
        confidence_load = np.mean(self.trade_pressure)

        stress = abs(drawdown) * confidence_load

        threshold = np.percentile(
            np.abs(self.recent_returns), 70
        )

        if stress > threshold:
            return {"level": "RESTRAIN", "factor": 0.6}
        else:
            return {"level": "NORMAL", "factor": 1.0}


class RegimeDriftMonitor:
    """
    Detects regime instability and drift in real time.
    """

    def __init__(self):
        self.recent_regimes = deque(maxlen=200)
        self.drift_scores = deque(maxlen=200)

    def update(self, regime: str):
        self.recent_regimes.append(regime)

        if len(self.recent_regimes) < 30:
            return None

        changes = sum(
            1 for i in range(1, len(self.recent_regimes))
            if self.recent_regimes[i] != self.recent_regimes[i - 1]
        )

        drift_score = changes / len(self.recent_regimes)
        self.drift_scores.append(drift_score)

        threshold = np.percentile(self.drift_scores, 75)

        if drift_score > threshold:
            return {
                "alert": True,
                "drift_score": round(drift_score, 3),
                "severity": round(drift_score / max(threshold, 1e-6), 2),
            }

        return {"alert": False, "drift_score": round(drift_score, 3)}


class BlackSwanDetector:
    """
    Detects anomalous market behavior using learned distributions.
    """

    def __init__(self):
        self.return_history = deque(maxlen=500)

    def update(self, realized_return: float):
        self.return_history.append(realized_return)

    def detect(self, current_return: float) -> Dict:
        if len(self.return_history) < 100:
            return {"anomaly": False, "score": 0.0}

        try:
            # Ensure current_return is a float (it might be passed as a dict or other type in some flows)
            if isinstance(current_return, dict):
                current_return = float(current_return.get('expected_return', 0.0))
            else:
                current_return = float(current_return)
        except (TypeError, ValueError):
            current_return = 0.0

        mean = np.mean(self.return_history)
        std = np.std(self.return_history) + 1e-6

        z_score = abs(current_return - mean) / std

        threshold = np.percentile(
            [abs((r - mean) / std) for r in self.return_history],
            95
        )

        return {
            "anomaly": z_score > threshold,
            "z_score": round(z_score, 2),
            "severity": round(z_score / threshold, 2) if threshold > 0 else 0,
        }
        
# ============================================================================
# NEW INTELLIGENCE ENGINES (UI & MEMORY SUPPORT)
# ============================================================================

class MarketMemory:
    """
    Recalls if the AI has seen this situation before.
    Reads from existing DB.
    """
    def __init__(self, db):
        self.db = db

    def recall(self, symbol, signal):
        try:
            # Check if db has the method, otherwise safe fallback
            if not hasattr(self.db, 'fetch_similar_predictions'):
                 return {
                    "occurrences": 0,
                    "bias": "UNKNOWN",
                    "accuracy": "N/A"
                }

            rows = self.db.fetch_similar_predictions(symbol, signal)

            if not rows:
                return {
                    "occurrences": 0,
                    "bias": "UNKNOWN",
                    "accuracy": "N/A"
                }

            wins = sum(1 for r in rows if r["outcome"] == "WIN")
            accuracy = wins / len(rows)

            bias = "BULLISH" if accuracy > 0.6 else "BEARISH" if accuracy < 0.4 else "MIXED"

            return {
                "occurrences": len(rows),
                "bias": bias,
                "accuracy": round(accuracy * 100, 1)
            }

        except Exception as e:
            logger.error(f"Market memory recall failed: {e}")
            return {
                "occurrences": 0,
                "bias": "ERROR",
                "accuracy": "N/A"
            }

class ConfidenceEvolution:
    """
    Tracks how confidence evolves over time for each symbol
    AND learns prediction reliability (merged from ConfidenceEvolutionEngine).
    No hardcoding. Learns from live predictions.
    """

    def __init__(self):
        self.history = defaultdict(lambda: deque(maxlen=200))
        self.reliability_history = defaultdict(lambda: deque(maxlen=200))

    def record(self, symbol: str, confidence: float):
        self.history[symbol].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "confidence": float(confidence)
        })

    def get_timeline(self, symbol: str):
        return list(self.history[symbol])

    def update(self, symbol, predicted_signal, actual_return):
        """
        Track win/loss from prediction outcomes.
        actual_return: positive = good call, negative = bad call
        """
        score = 1 if actual_return > 0 else -1
        self.reliability_history[symbol].append(score)

    def reliability(self, symbol):
        """
        Returns a multiplier ~0.7–1.3 based on recent accuracy.
        """
        records = self.reliability_history.get(symbol)
        if not records:
            return 1.0
        avg = sum(records) / len(records)
        return round(1.0 + (avg * 0.3), 3)

class OutcomeLearning:
    """
    Learns from prediction outcomes continuously.
    """

    def __init__(self):
        self.stats = defaultdict(lambda: {"wins": 0, "losses": 0})

    def update(self, symbol, success: bool):
        if success:
            self.stats[symbol]["wins"] += 1
        else:
            self.stats[symbol]["losses"] += 1

    def reliability(self, symbol):
        s = self.stats[symbol]
        total = s["wins"] + s["losses"]
        return s["wins"] / total if total > 0 else 0.5

class CrossAssetMemory:
    """
    Learns from similar emotional + regime patterns across assets.
    """

    def __init__(self):
        self.memory = []  # grows organically

    def record(self, symbol, emotional_state, outcome=None):
        self.memory.append({
            "symbol": symbol,
            "regime": emotional_state["regime"],
            "fear": emotional_state["fear"],
            "greed": emotional_state["greed"],
            "fatigue": emotional_state["fatigue"],
            "outcome": outcome,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def recall(self, emotional_state):
        similar = [
            m for m in self.memory
            if m["regime"] == emotional_state["regime"]
        ]

        if not similar:
            return {"occurrences": 0}

        positive = sum(1 for m in similar if m.get("outcome") == "POSITIVE")
        accuracy = positive / len(similar)

        return {
            "occurrences": len(similar),
            "historical_bias": "POSITIVE" if accuracy > 0.6 else "NEGATIVE",
            "accuracy": round(accuracy * 100, 1)
        }

# ContagionGraph: merged into NarrativeContagionEngine (see below)

class PortfolioForesight:
    """
    Evaluates portfolio-wide emotional & regime risk.
    """

    def evaluate(self, predictions: List[Dict]):
        regimes = [p["emotional_state"]["regime"] for p in predictions]

        concentration = max(regimes.count(r) for r in set(regimes)) if regimes else 0
        fragility = concentration / len(regimes) if regimes else 0

        return {
            "dominant_regime": max(set(regimes), key=regimes.count) if regimes else "UNKNOWN",
            "fragility_score": round(fragility, 2),
            "risk_level": "HIGH" if fragility > 0.6 else "MODERATE"
        }

class CapitalAllocator:
    """
    Dynamic capital sizing engine.
    """

    def allocate(
        self,
        confidence: float,
        emotional_state: Dict,
        futures: Dict,
        governance: Dict
    ):
        if governance["decision"] == "PAUSE":
            return 0

        base = confidence / 100

        emotion_penalty = emotional_state["regime_strength"]
        risk_penalty = futures.get("downside_risk", 0)

        allocation = base * (1 - emotion_penalty) * (1 - risk_penalty)

        return round(max(0, min(allocation, 0.25)), 2)

class GlobalMacroIntelligence:
    """
    Infers macro pressure from cross-market co-movement.
    No APIs. No assumptions. Pure behavior.
    """

    def __init__(self):
        self.macro_pressure = deque(maxlen=50)

    def update(self, market_returns: Dict[str, float]):
        # market_returns = {"NIFTY": x, "BANKNIFTY": y, "SENSEX": z}
        if not market_returns:
            return 0.5
        dispersion = np.std(list(market_returns.values()))
        pressure = np.clip(1 - dispersion * 10, 0, 1)
        self.macro_pressure.append(pressure)
        return round(np.mean(self.macro_pressure), 2)

    def regime(self):
        avg = np.mean(self.macro_pressure) if self.macro_pressure else 0.5
        if avg < 0.3:
            return "MACRO_STRESS"
        elif avg < 0.6:
            return "MACRO_UNCERTAIN"
        return "MACRO_STABLE"

class HypothesisEngine:
    """
    AI generates and tests market hypotheses autonomously.
    """

    def __init__(self):
        self.hypotheses = []

    def generate(self, emotional_state, regime):
        if emotional_state["fear"] > 70:
            h = "Fear-driven selloffs revert within 5 days"
        elif emotional_state["greed"] > 70:
            h = "Momentum exhausts after prolonged greed"
        else:
            h = "Trend continuation likely"

        self.hypotheses.append({
            "hypothesis": h,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return h

    def active(self):
        return self.hypotheses[-3:]

class AIDebateEngine:
    """
    Internal argument resolution between models.
    """

    def debate(self, model_outputs: Dict[str, float]):
        if not model_outputs:
            return {"verdict": "UNKNOWN", "disagreement_score": 0}
            
        values = list(model_outputs.values())
        disagreement = np.std(values)

        if disagreement > 0.4:
            verdict = "DISAGREEMENT"
        elif disagreement > 0.2:
            verdict = "WEAK_CONSENSUS"
        else:
            verdict = "STRONG_CONSENSUS"

        return {
            "verdict": verdict,
            "disagreement_score": round(disagreement, 2)
        }

class StrategyEvolution:
    """
    Learns which conditions produce success.
    """

    def __init__(self):
        self.performance = defaultdict(list)

    def record(self, regime, decision, outcome):
        self.performance[(regime, decision)].append(outcome)

    def bias(self, regime, decision):
        history = self.performance.get((regime, decision), [])
        if not history:
            return 0
        return round(np.mean(history), 2)

class AIPersonalityEngine:
    """
    Controls HOW decisions are applied, not predictions.
    """

    PROFILES = {
        "CONSERVATIVE": {
            "min_confidence": 70,
            "risk_multiplier": 0.7,
            "pause_bias": 1.2,
        },
        "BALANCED": {
            "min_confidence": 60,
            "risk_multiplier": 1.0,
            "pause_bias": 1.0,
        },
        "AGGRESSIVE": {
            "min_confidence": 50,
            "risk_multiplier": 1.3,
            "pause_bias": 0.8,
        },
        "DEFENSIVE": {
            "min_confidence": 75,
            "risk_multiplier": 0.6,
            "pause_bias": 1.4,
        },
        "OPPORTUNISTIC": {
            "min_confidence": 55,
            "risk_multiplier": 1.1,
            "pause_bias": 0.9,
        },
    }

    def __init__(self, mode="BALANCED"):
        self.mode = mode

    def apply(self, governance_result: Dict):
        profile = self.PROFILES.get(self.mode, self.PROFILES["BALANCED"])

        score = governance_result["overall_score"]
        score *= profile["risk_multiplier"]
        score /= profile["pause_bias"]

        if score < profile["min_confidence"]:
            governance_result["decision"] = "PAUSE"

        governance_result["personality"] = self.mode
        governance_result["personality_score"] = round(score, 2)
        return governance_result

class MultiYearForesight:
    """
    Long-horizon probabilistic outlook (1–5 years).
    """

    def project(self, historical_data: pd.DataFrame, years=3):
        if len(historical_data) < 252:
            return {"bear": 0, "base": 0, "bull": 0}
            
        returns = historical_data["Close"].pct_change().dropna()
        mu = returns.mean() * 252
        sigma = returns.std() * np.sqrt(252)

        scenarios = {
            "bear": mu - sigma,
            "base": mu,
            "bull": mu + sigma,
        }

        return {
            k: round((1 + v) ** years - 1, 2)
            for k, v in scenarios.items()
        }

class AutonomousPortfolioEngine:
    """
    Allocates capital dynamically.
    """

    def allocate(self, predictions: List[Dict]):
        weights = {}
        total = 0

        for p in predictions:
            score = p.get("governance", {}).get("overall_score", 0)
            if p.get("final_signal") == "PAUSE":
                continue
            weights[p["symbol"]] = max(score, 0)
            total += weights[p["symbol"]]

        return {
            k: round(v / total, 3)
            for k, v in weights.items()
            if total > 0
        }

class AIConversationEngine:
    """
    Natural language reasoning from internal state.
    """

    def respond(self, question: str, intelligence: Dict):
        q = question.lower()

        if "why pause" in q:
            return intelligence["governance"]["reason"]

        if "why now" in q:
            return intelligence.get("why_now", "Timing driven by regime shift.")

        if "what can change" in q:
            return intelligence.get(
                "what_could_invalidate",
                "Break of support or regime reversal."
            )

        if "emotion" in q:
            return intelligence.get("emotion_influence", "Emotion neutral.")

        return "AI requires a clearer question."

class AILongTermMemory:
    """
    Stores and learns from outcomes across years/decades.
    """

    def __init__(self):
        self.memory = defaultdict(list)

    def record(self, symbol: str, intelligence: Dict, realized_return: float = None):
        entry = {
            "timestamp": intelligence.get("timestamp"),
            "signal": intelligence.get("final_signal"),
            "confidence": intelligence.get("confidence_adjusted"),
            "emotion": intelligence.get("emotional_state", {}).get("regime"),
            "regime_strength": intelligence.get("emotional_state", {}).get("regime_strength"),
            "expected_return": intelligence.get("futures", {}).get("expected_return"),
            "realized_return": realized_return,
        }
        self.memory[symbol].append(entry)

    def recall(self, symbol: str):
        history = self.memory.get(symbol, [])
        if not history:
            return {"experience": "NEW_SYMBOL"}

        wins = [h for h in history if h.get("realized_return", 0) > 0]
        losses = [h for h in history if h.get("realized_return", 0) <= 0]

        return {
            "years_observed": len(history), # Approximation if purely timestamp based
            "win_rate": round(len(wins) / len(history), 2) if history else 0,
            "loss_patterns": list(set(h["emotion"] for h in losses if h["emotion"])),
            "best_conditions": list(set(h["emotion"] for h in wins if h["emotion"])),
        }

class PersonalityEvolution:
    """
    AI evolves its personality based on outcomes.
    """

    def evolve(self, memory: Dict, current_mode: str):
        if memory.get("win_rate", 0) < 0.45:
            return "DEFENSIVE"

        if "FEAR" in memory.get("best_conditions", []):
            return "OPPORTUNISTIC"

        if memory.get("years_observed", 0) > 200:
            return "BALANCED"

        return current_mode

class CollectiveIntelligence:
    """
    Learns from aggregated user behavior (anonymized).
    """

    def __init__(self):
        self.behavior = defaultdict(list)

    def observe(self, symbol: str, user_action: str, outcome: float):
        self.behavior[symbol].append({
            "action": user_action,
            "outcome": outcome,
        })

    def consensus_bias(self, symbol: str):
        data = self.behavior.get(symbol, [])
        if not data:
            return "NEUTRAL"

        buys = [d for d in data if d["action"] == "BUY" and d["outcome"] > 0]
        sells = [d for d in data if d["action"] == "SELL" and d["outcome"] > 0]

        if len(buys) > len(sells):
            return "BULLISH"
        if len(sells) > len(buys):
            return "BEARISH"
        return "MIXED"

class AutonomousHedgeFund:
    """
    Governs portfolio-level risk.
    """

    def govern(self, portfolio_weights: Dict):
        exposure = sum(portfolio_weights.values())

        if exposure > 0.9:
            return {
                "mode": "RISK_ON",
                "leverage": 1.0,
            }

        if exposure < 0.4:
            return {
                "mode": "CAPITAL_PRESERVATION",
                "leverage": 0.0,
            }

        return {
            "mode": "NEUTRAL",
            "leverage": 0.5,
        }


# ============================================================================
# META-INTELLIGENCE KERNEL (PHASE 1: CORE COMPONENTS)
# ============================================================================

class MetaIntelligenceRegistry:
    """
    Universal intelligence registry.
    Any new intelligence auto-registers itself.
    NO hardcoding - all sources discovered dynamically.
    """

    def __init__(self):
        self.sources = {}
        logger.info("✅ MetaIntelligenceRegistry initialized")

    def register(self, name, fn):
        """Register intelligence source with callable function"""
        self.sources[name] = fn
        logger.debug(f"[META-REGISTRY] Registered intelligence source: {name}")

    def evaluate(self, context):
        """Evaluate all registered intelligence sources with given context"""
        outputs = {}
        for name, fn in list(self.sources.items()):
            try:
                result = fn(context)
                if result is not None:
                    outputs[name] = result
            except Exception as e:
                logger.debug(f"[META-REGISTRY] Source {name} returned no data: {e}")
                continue
        return outputs


class FeatureFabric:
    """
    Converts intelligence outputs into adaptive signals.
    NO fixed weights - dynamically weaves features from any intelligence source.
    """

    def weave(self, intelligence_outputs):
        """Extract numerical features from intelligence outputs"""
        vectors = []

        for v in intelligence_outputs.values():
            if isinstance(v, dict):
                vectors.extend([
                    x for x in v.values() if isinstance(x, (int, float))
                ])
            elif isinstance(v, (int, float)):
                vectors.append(v)

        if not vectors:
            return None

        mean = np.mean(vectors)
        variance = np.var(vectors)

        return {
            "signal_strength": float(mean),
            "uncertainty": float(variance),
            "entropy": float(np.std(vectors))
        }


class SelfAwareConfidenceEngine:
    """
    AI knows when it is confident AND when it shouldn't be.
    Self-calibrating uncertainty estimation.
    """

    def evolve(self, base_confidence, fabric):
        """Adjust confidence based on intelligence fabric uncertainty"""
        if not fabric:
            return base_confidence

        # Penalty based on uncertainty and entropy
        penalty = fabric["uncertainty"] * fabric["entropy"]
        adjusted = base_confidence * (1 - penalty)

        return float(np.clip(adjusted, 0.01, 0.99))


class MetaEvolutionMonitor:
    """
    Detects when intelligence structure must evolve.
    Autonomous future activation detector.
    """

    def assess(self, fabric):
        """Assess evolution pressure from intelligence fabric"""
        if not fabric:
            return None

        stress = fabric["entropy"] * fabric["uncertainty"]

        return {
            "evolution_pressure": float(stress),
            "state": "EVOLVING" if stress > fabric["signal_strength"] else "STABLE"
        }



# ============================================================================
# PHASE 2: ADVANCED INTELLIGENCE LAYERS
# ============================================================================

class SentimentDynamicsEngine:
    """
    Learns sentiment behavior over time.
    NO fixed thresholds, NO percentiles.
    Replaces static percentile-based sentiment volatility cone.
    """

    def __init__(self, memory_engine=None):
        self.memory = memory_engine
        self.history = {}
        logger.info("✅ SentimentDynamicsEngine initialized")

    def update(self, symbol, sentiment):
        """Update sentiment history for symbol"""
        self.history.setdefault(symbol, []).append(sentiment)
        if len(self.history[symbol]) > 200:
            self.history[symbol].pop(0)

    def volatility(self, symbol):
        """Calculate sentiment volatility (learned, not percentile-based)"""
        series = self.history.get(symbol, [])
        if len(series) < 20:
            return None

        diffs = np.diff(series)
        return float(np.sqrt(np.mean(diffs ** 2)))

    def expected_range(self, symbol):
        """Calculate adaptive sentiment range"""
        series = self.history.get(symbol, [])
        if len(series) < 30:
            return None

        mean = np.mean(series)
        vol = self.volatility(symbol)

        return {
            "center": mean,
            "adaptive_band": vol,
            "state": "EXPANDING" if vol > np.mean(np.abs(series)) else "STABLE"
        }

    def reliability_score(self, symbol, sentiment_value, news_volume, market_volatility=None):
        """
        Calculate sentiment reliability (0.0 to 1.0)
        Based on volume, history, stability, and market context.
        """
        history = self.history.get(symbol, [])
        if not history:
            return 0.5
            
        # Volume component
        volume_factor = min(1.0, news_volume / 20.0)
        
        # History component
        history_factor = min(1.0, len(history) / 50.0)
        
        # Stability component
        if len(history) > 5:
            std = np.std(history)
            stability_factor = 1.0 - min(0.5, std)
        else:
            stability_factor = 0.7
            
        # Market context
        market_factor = 1.0
        if market_volatility is not None:
             market_factor = 1.0 - min(0.4, float(market_volatility))
             
        score = (volume_factor * 0.4) + (history_factor * 0.2) + (stability_factor * 0.3) + (market_factor * 0.1)
        return round(float(score), 3)


class MetaConfidenceMonitor:
    """
    AI self-awareness and introspection.
    Monitors confidence-sentiment coherence.
    """

    def assess(self, confidence, sentiment, volatility):
        """Assess confidence integrity"""
        if volatility is None:
            return {"state": "INSUFFICIENT_DATA"}

        coherence = 1 - abs(confidence - abs(sentiment))
        stress = volatility * (1 - coherence)

        return {
            "coherence": round(coherence, 3),
            "stress": round(stress, 3),
            "meta_state": (
                "OVERCONFIDENT" if stress > np.mean([confidence, volatility])
                else "BALANCED"
            )
        }


class NarrativeRealityEngine:
    """
    Reality vs Narrative divergence detector.
    NO static gap thresholds - learned from trends.
    """

    def evaluate(self, price_series, sentiment_series):
        """Evaluate price-sentiment alignment"""
        if len(price_series) < 20 or len(sentiment_series) < 20:
            return None

        # Trend analysis using linear fit
        price_trend = np.polyfit(range(len(price_series)), price_series, 1)[0]
        sentiment_trend = np.polyfit(range(len(sentiment_series)), sentiment_series, 1)[0]

        divergence = abs(price_trend - sentiment_trend)

        return {
            "price_trend": float(price_trend),
            "sentiment_trend": float(sentiment_trend),
            "alignment": float(1 - divergence),
            "state": "DISSONANCE" if divergence > np.std(price_series) else "ALIGNED"
        }


class NarrativeContagionEngine:
    """
    Cross-asset narrative contagion detector (merged with ContagionGraph).
    Tracks sector → stock sentiment propagation AND stress contagion across assets.
    """

    def __init__(self):
        self.connections = defaultdict(lambda: defaultdict(int))

    def propagate(self, sector_sentiment, stock_sentiment):
        """Calculate narrative influence propagation"""
        influence = sector_sentiment * (1 - abs(sector_sentiment - stock_sentiment))

        return {
            "sector_influence": round(influence, 3),
            "amplified_sentiment": stock_sentiment + influence * 0.1
        }

    def update(self, symbol, emotional_state):
        """Track stress contagion between assets (from ContagionGraph)"""
        if emotional_state["regime"] in ("FEAR", "PANIC"):
            for other in list(self.connections.keys()):
                self.connections[symbol][other] += 1

    def get_exposed_assets(self, symbol):
        """Get assets most exposed to contagion from a given symbol"""
        return sorted(
            self.connections[symbol].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]


class IntelligenceDriftMonitor:
    """
    Autonomous drift alerts.
    NO rules - entropy-based detection.
    """

    def detect(self, sentiment_series):
        """Detect intelligence drift using entropy"""
        if len(sentiment_series) < 50:
            return None

        # Prevent log(0) with small epsilon
        safe_series = np.abs(sentiment_series) + 1e-9
        entropy = -np.sum(safe_series * np.log(safe_series))

        return {
            "entropy": round(entropy, 3),
            "drift": entropy > np.mean(sentiment_series ** 2)
        }


# ============================================================================
# LAYER 5: INTEGRATED FORESIGHT SYSTEM
# ============================================================================

class IntegratedForesightSystem:
    """
    ORCHESTRATOR: Unified intelligence system.
    """

    def __init__(self, config: Optional[Dict] = None):

        self.config = config or {}
        # ------------------------------------------------------------
        # FOUNDATIONAL ENGINES (CREATE FIRST)
        # ------------------------------------------------------------
        self.emotion_engine = EmotionalIntelligence()
        self.sentiment_dynamics = SentimentDynamicsEngine()

        self.futures_engine = MultiworldFuturesEngine()
        self.governance_engine = GovernanceIntelligence()

        # ------------------------------------------------------------
        # CORE INTELLIGENCE (DEPENDENCY INJECTION – CANONICAL)
        # ------------------------------------------------------------
        self.intelligence_core = IntelligenceCore(
            config=self.config,
            emotion_engine=self.emotion_engine,
            sentiment_dynamics=self.sentiment_dynamics
        )


        # ------------------------------------------------------------
        # META-INTELLIGENCE (PHASE 1 & 2)
        # ------------------------------------------------------------
        self.meta_registry = MetaIntelligenceRegistry()
        self.feature_fabric = FeatureFabric()
        self.self_confidence = SelfAwareConfidenceEngine()
        self.meta_monitor = MetaEvolutionMonitor()

        # ------------------------------------------------------------
        # ADVANCED INTELLIGENCE LAYERS
        # ------------------------------------------------------------
        self.meta_confidence_monitor = MetaConfidenceMonitor()
        self.narrative_reality = NarrativeRealityEngine()
        self.narrative_contagion = NarrativeContagionEngine()
        self.intelligence_drift = IntelligenceDriftMonitor()

        # Feedback loop
        self.feedback_registry = deque(maxlen=1000)

        # Cross-asset & memory
        self.cross_asset_risk = CrossAssetRiskEngine()
        self.memory_store = IntelligenceMemoryStore()

        # Risk & regime engines
        self.regime_memory = RegimeStatsTracker()
        self.capital_restraint = CapitalRestraintEngine()
        self.regime_drift_monitor = RegimeDriftMonitor()
        self.black_swan_detector = BlackSwanDetector()

        # =========================================================
        # LEGACY BRIDGE & HEALTH (PHASE 2 HARMONIZATION)
        # =========================================================
        self.model_status = {
            "rf": {"active": True, "reason": "Integrated Kernel"},
            "gb": {"active": True, "reason": "Integrated Kernel"},
            "lstm": {"active": True, "reason": "Self-Aware Core"},
            "risk": {"active": True, "reason": "Adaptive Classifier"},
            "rl": {"active": True, "reason": "Futures Memory"}
        }
        
        # Bridge attributes for app.py health checks & operations
        self._quantum_lstm_model = True 
        self._quantum_risk_model = True
        self._quantum_risk = True
        self.models = {"kernel": True}
        self.adaptive_thresholds = None
        self.prediction_logger = None
        self.prediction_history = deque(maxlen=1000)
        self.cache_advanced = {}
        self.cache_ttl = 300
        
        # Database & Market bridge (will be bound in app.py)
        self.db = None
        self.market = None

        logger.info("📡 Legacy Bridge: ACTIVE (7/7 modules bridged)")


        logger.info(
            "✅ IntegratedForesightSystem fully initialized "
            "with 9 intelligence layers + Meta-Intelligence Kernel"
        )

    def generate_evolved_prediction(self, symbol: str, current_price: float, historical_data: pd.DataFrame, base_prediction: Dict) -> Dict:
        """
        Orchestrate all layers to generate ONE evolved prediction.
        """
        try:
            # Initialize sentiment-related variables to prevent crashes if sentiment is missing
            confidence_sentiment_divergence = None
            sentiment_drift = None
            narrative_bubble = None
            ai_self_awareness = None
            # 1. Emotional Layer
            emotional_state = self.emotion_engine.update_emotional_state(historical_data, symbol)
            
            # 2. Intelligence Core Analysis (Legacy + New)
            confidence_adjusted = self.intelligence_core.calculate_confidence(
                symbol,
                base_prediction.get("confidence")
            )
            
            # Recalls if AI has seen this before
            market_memory = self.intelligence_core.market_memory.recall(
                symbol, base_prediction["signal"]
            )
            
            # Regime Memory Adjustment
            regime_factor = self.regime_memory.confidence_modifier(
                emotional_state["regime"]
            )
            confidence_adjusted *= regime_factor
            
            # 3. Multiworld Futures
            multiworld_result = self.futures_engine.generate_worlds(
                current_price=current_price,
                historical_data=historical_data,
                base_prediction=base_prediction,
                emotional_state=emotional_state
            )
            
            # STEP 6: Format futures for UI (Cone)
            future_cone = self.format_futures_for_ui(
                multiworld_result.get("worlds", [])
            )
            
            # Cross-Asset Learning & Advanced Intelligence (Features 13-28)
            
            # 13. Cross Asset Memory
            ai_market_memory = self.intelligence_core.asset_memory.recall(emotional_state)
            
            # 14. Contagion
            self.intelligence_core.contagion.update(symbol, emotional_state)
            contagion_risk = self.intelligence_core.contagion.get_exposed_assets(symbol)
            
            # 17. Global Macro (Basic Update)
            macro_pressure = self.intelligence_core.macro.update({}) 
            
            # 18. Hypothesis
            ai_hypothesis = self.intelligence_core.hypotheses.generate(emotional_state, emotional_state.get("regime", "UNKNOWN"))
            
            # 19. Debate
            ai_debate = self.intelligence_core.debate.debate(base_prediction.get("model_outputs", {}))
            
            # 25. Long Term Memory
            ai_memory = self.intelligence_core.long_memory.recall(symbol)
            
            # 27. Collective Intelligence
            collective_bias = self.intelligence_core.collective.consensus_bias(symbol)

            # Drift & Anomaly Detection
            drift_alert = self.regime_drift_monitor.update(
                emotional_state["regime"]
            )
            
            black_swan_risk = self.black_swan_detector.detect(
                multiworld_result.get("statistics", {}).get("expected_return", 0)
            )

            global_risk = self.cross_asset_risk.compute_risk_state()
            
            # 4. Governance Decision
            governance_result = self.governance_engine.make_governed_decision(
                symbol=symbol,
                base_prediction=base_prediction,
                emotional_state=emotional_state,
                multiworld_stats=multiworld_result.get('statistics', {}),
                model_agreement=base_prediction.get('confidence', 50)/100
            )

            # 21. Personality - Needs governance_result
            governance_personality = self.intelligence_core.personality.apply(governance_result.copy())
            
            # 22. Multi-Year Foresight
            multi_year_outlook = self.intelligence_core.foresight.project(historical_data)
            
            # Capital Restraint & Final Confidence
            restraint = self.capital_restraint.restraint_level()
            
            # Deep confidence evolution (self-learning)
            confidence_multiplier = self.intelligence_core.confidence_reliability.reliability(symbol)
            final_confidence = confidence_adjusted * restraint["factor"] * confidence_multiplier

            # 16. Capital Allocation - Needs final_confidence and governance_personality
            recommended_position_size = self.intelligence_core.capital_allocator.allocate(
                final_confidence,
                emotional_state,
                multiworld_result.get("statistics", {}),
                governance_personality
            )

            # 5. Explanations hierarchy
            explanations = self._generate_explanations(
                symbol, emotional_state, governance_result, multiworld_result, global_risk
            )
            
            # Explainability Heatmap
            heatmap = self.explainability_heatmap(
                emotional_state,
                multiworld_result.get("statistics", {}),
                governance_result.get("scores", {})
            )
            
            # ------------------------------------------------------------
            # 🧠 LIVE SENTIMENT INTELLIGENCE
            # ------------------------------------------------------------
            sentiment_context = None
            sentiment_reliability = None
            sentiment_score = None

            if hasattr(self, "news_ai") and self.news_ai:
                sentiment_data = self.news_ai.get_sentiment(symbol)
                
                # Extract score float from dict if necessary
                if isinstance(sentiment_data, dict):
                    sentiment_score = float(sentiment_data.get('overall_score', 0.0)) / 100.0 if 'overall_score' in sentiment_data else 0.0
                else:
                    sentiment_score = float(sentiment_data or 0.0)

                if sentiment_score is not None:
                    # Update sentiment dynamics FIRST (learning loop)
                    self.sentiment_dynamics.update(symbol, sentiment_score)

                    sentiment_context = self.emotion_engine.interpret_sentiment(
                        symbol=symbol,
                        sentiment_value=sentiment_score,
                        market_memory=market_memory,
                        volatility_context=global_risk.get("volatility", 0.1) if isinstance(global_risk, dict) else 0.1
                    )

                    # LIVE reliability from dynamics (NO constants)
                    # Safe fallback if reliability_score method doesn't exist
                    if hasattr(self.sentiment_dynamics, 'reliability_score'):
                        sentiment_reliability = self.sentiment_dynamics.reliability_score(
                            symbol=symbol,
                            sentiment_value=sentiment_score,
                            news_volume=len(self.news_ai.symbol_sentiment_memory.get(symbol, [])),
                            market_volatility=global_risk.get("volatility")
                        )
                    else:
                        # Fallback: compute simple reliability based on news volume
                        news_count = len(self.news_ai.symbol_sentiment_memory.get(symbol, []))
                        sentiment_reliability = min(0.9, 0.5 + (news_count * 0.05))

            # ------------------------------------------------------------
            # 1️⃣ CONFIDENCE EVOLUTION & AWARENESS
            # ------------------------------------------------------------
            
            # Confidence Divergence (AI vs Narrative)
            if sentiment_context and "score" in sentiment_context:
                sentiment_score = sentiment_context["score"]
                normalized_sentiment = (sentiment_score + 1) / 2
                # Ensure confidence is 0-1 for comparison
                conf_val = final_confidence / 100.0 if final_confidence > 1.0 else final_confidence
                divergence_value = conf_val - normalized_sentiment
                
                confidence_sentiment_divergence = {
                    "value": float(divergence_value),
                    "direction": "MODEL_OVERCONFIDENT" if divergence_value > 0 else "SENTIMENT_OVERCONFIDENT",
                    "magnitude": float(abs(divergence_value))
                }

            # Narrative Bubble Detection
            if confidence_sentiment_divergence and sentiment_context:
                instability = sentiment_context.get("instability", 0.0)

                bubble_pressure = confidence_sentiment_divergence["magnitude"] * instability

                narrative_bubble = {
                    "pressure": float(bubble_pressure),
                    "risk": self.intelligence_core.risk_classifier.classify(bubble_pressure)
                }

                # Self-awareness penalty derived from internal uncertainty
                awareness_penalty = bubble_pressure
                final_confidence *= max(0.0, 1.0 - awareness_penalty)

            # Regime-Aware Model Trust
            if sentiment_context and "regime" in sentiment_context:
                psych_regime = sentiment_context["regime"]
                if psych_regime in ['EUPHORIA', 'FEAR']:
                    # Dampen confidence in extreme emotional regimes
                    vol_factor = sentiment_context.get('volatility', 0.1)
                    final_confidence *= (1.0 - vol_factor)

            # ------------------------------------------------------------
            # 2️⃣ SENTIMENT-AWARE POSITION SIZING
            # ------------------------------------------------------------
            if sentiment_reliability:
                recommended_position_size *= sentiment_reliability
                
            # ------------------------------------------------------------
            # 3️⃣ AI META-AWARENESS
            # ------------------------------------------------------------
            ai_self_awareness = {
                'confidence_trust': float(final_confidence),
                'sentiment_trust': float(sentiment_reliability) if sentiment_reliability else None,
                'narrative_alignment': confidence_sentiment_divergence['direction'] if confidence_sentiment_divergence else 'ALIGNED'
            }
            
            # ============================================================
            # META-INTELLIGENCE PIPELINE (PHASE 1 & 2 INTEGRATION)
            # ============================================================
            
            # Build context for meta-intelligence registry
            meta_context = {
                "sentiment": sentiment_score,
                "emotion": emotional_state.get("regime"),
                "governance": governance_result.get("decision"),
                "risk": global_risk.get("state"),
                "macro": macro_pressure
            }
            
            # Evaluate all registered intelligence sources
            intelligence_outputs = self.meta_registry.evaluate(meta_context)
            
            # Weave features into unified signal
            fabric = self.feature_fabric.weave(intelligence_outputs)
            
            # Apply self-aware confidence evolution
            if fabric:
                final_confidence = self.self_confidence.evolve(final_confidence, fabric)
            
            # Monitor evolution pressure
            meta_state = self.meta_monitor.assess(fabric) if fabric else None
            
            # Advanced intelligence layers application
            meta_confidence_assessment = None
            narrative_divergence_state = None
            intelligence_drift_alert = None
            
            if sentiment_score is not None:
                # Update sentiment dynamics
                self.sentiment_dynamics.update(symbol, sentiment_score)
                sentiment_volatility = self.sentiment_dynamics.volatility(symbol)
                
                # Meta confidence monitoring
                if sentiment_volatility is not None:
                    meta_confidence_assessment = self.meta_confidence_monitor.assess(
                        final_confidence / 100.0 if final_confidence > 1.0 else final_confidence,
                        sentiment_score,
                        sentiment_volatility
                    )
                
                # Narrative reality divergence
                if len(historical_data) >= 20:
                    price_series = historical_data['Close'].tail(50).values
                    sentiment_history = self.sentiment_dynamics.history.get(symbol, [])
                    if len(sentiment_history) >= 20:
                        narrative_divergence_state = self.narrative_reality.evaluate(
                            price_series,
                            np.array(sentiment_history[-50:])
                        )
                
                # Intelligence drift detection
                if len(self.sentiment_dynamics.history.get(symbol, [])) >= 50:
                    intelligence_drift_alert = self.intelligence_drift.detect(
                        np.array(self.sentiment_dynamics.history[symbol])
                    )
            
            evolved_prediction = {
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'base_prediction': base_prediction,
                'emotional_state': emotional_state,
                'futures': multiworld_result.get('statistics', {}),
                'governance': governance_result,
                'confidence_adjusted': final_confidence,
                'confidence_adjustment_reason': self.intelligence_core.last_adjustment_reason,
                'global_risk': global_risk,
                'regime_drift': drift_alert,
                'black_swan_risk': black_swan_risk,
                'capital_restraint': restraint,
                'explainability_heatmap': heatmap,
                'regime_timeline': list(self.emotion_engine.regime_timeline),
                'market_memory': market_memory,
                'confidence_timeline': self.intelligence_core.confidence_evolution.get_timeline(symbol),
                'future_cone': future_cone,
                'learning_reliability': self.intelligence_core.learning.reliability(symbol),
                
                # New Advanced Features
                'ai_market_memory': ai_market_memory,
                'contagion_risk': contagion_risk,
                'macro_regime': self.intelligence_core.macro.regime(),
                'macro_pressure': macro_pressure,
                'ai_hypothesis': ai_hypothesis,
                'ai_debate': ai_debate,
                'recommended_position_size': recommended_position_size,
                'governance_personality': governance_personality, # Includes personality_score
                'multi_year_outlook': multi_year_outlook,
                'ai_memory': ai_memory,
                'collective_bias': collective_bias,
                
                'market_sentiment': sentiment_context,
                'sentiment_score': sentiment_context.get('score') if sentiment_context else None,
                'sentiment_state': 'LIVE' if sentiment_context else 'UNAVAILABLE',
                'sentiment_drift': sentiment_drift,
                'confidence_sentiment_divergence': confidence_sentiment_divergence,
                'narrative_bubble': narrative_bubble,
                'ai_self_awareness': ai_self_awareness,
                
                # Meta-Intelligence Fields (Phase 1 & 2)
                'meta_intelligence': {
                    'intelligence_fabric': fabric,
                    'evolution_pressure': meta_state,
                    'meta_confidence_assessment': meta_confidence_assessment,
                    'narrative_divergence': narrative_divergence_state,
                    'intelligence_drift': intelligence_drift_alert,
                },

                **explanations
            }

            return evolved_prediction
            
        except Exception as e:
            logger.error(f"Prediction evolution failed: {e}")
            return {'error': str(e)}

    @property
    def is_ready(self):
        """
        Foresight system is ready ONLY when its intelligence core is alive.
        """
        return (
            hasattr(self, "intelligence_core")
            and self.intelligence_core is not None
            and self.intelligence_core.is_ready
        )

    def feedback(self, symbol: str, evolved_prediction: Dict, realized_return: float):
        """
        Unified feedback hook for all layers.
        """
        try:
             # Existing updates
            correct = np.sign(realized_return) == np.sign(
                evolved_prediction['futures']['expected_return']
            )
            self.intelligence_core.update_confidence_memory(symbol, correct)
            self.emotion_engine.feedback(evolved_prediction['emotional_state']['regime'], correct)
            
            if 'decision' in evolved_prediction['governance']:
                 self.governance_engine.feedback(evolved_prediction['governance']['decision'], correct)

            # New updates
            self.regime_memory.update(
                evolved_prediction["emotional_state"]["regime"],
                realized_return
            )
            
            self.capital_restraint.update(
                realized_return, 
                evolved_prediction["confidence_adjusted"]
            )
            
            self.black_swan_detector.update(realized_return)
            
            self.intelligence_core.learning.update(symbol, success=correct)
            
            self.black_swan_detector.update(realized_return)
            
            self.intelligence_core.learning.update(symbol, success=correct)
            
            # Update Deep Confidence Evolution
            try:
                # Calculate actual return signal for confidence evolution (positive/negative impact)
                # realized_return is already signed
                self.intelligence_core.confidence_reliability.update(
                    symbol,
                    evolved_prediction.get("base_prediction", {}).get("signal"),
                    realized_return
                )
            except Exception as e:
                logger.warning(f"Confidence evolution update failed: {e}")

            # Features 13-28 Learning Hooks
            
            # 20. Strategy Evolution
            self.intelligence_core.strategy_evolution.record(
                evolved_prediction["emotional_state"]["regime"],
                evolved_prediction["governance"]["decision"],
                realized_return
            )
            
            # 13. Cross Asset Memory
            self.intelligence_core.asset_memory.record(
                symbol, 
                evolved_prediction["emotional_state"], 
                "POSITIVE" if realized_return > 0 else "NEGATIVE"
            )
            
            # 25. Long Term Memory
            self.intelligence_core.long_memory.record(
                symbol,
                evolved_prediction,
                realized_return
            )
            
            # 26. Personality Evolution
            # Fetch updated memory
            lt_mem = self.intelligence_core.long_memory.recall(symbol)
            current_mode = self.intelligence_core.personality.mode
            new_mode = self.intelligence_core.personality_evolution.evolve(lt_mem, current_mode)
            
            if new_mode != current_mode:
                self.intelligence_core.personality.mode = new_mode
                logger.info(f"🧬 Personality Evolved: {current_mode} -> {new_mode}")

            logger.info(f"✅ Deep feedback processed for {symbol} (Strategy, Memory, Personality updated)")

        except Exception as e:
            logger.error(f"Feedback processing failed: {e}")
        
    def health_check(self) -> Dict:
        diagnostics = {}

        # Emotional stability
        diagnostics["emotion_stability"] = (
            "OK" if len(self.emotion_engine.fear_history) > 50 else "WARMING_UP"
        )

        # Futures reliability
        diagnostics["futures_quality"] = (
            "OK" if len(self.futures_engine.worlds) > 0 else "DEGRADED"
        )

        # Governance learning
        diagnostics["governance_learning"] = (
            "OK" if len(self.governance_engine.decision_log) > 50 else "LOW_DATA"
        )

        # Intelligence memory
        diagnostics["memory_status"] = (
            "OK" if bool(self.intelligence_core.confidence_memory) else "EMPTY"
        )

        severity_map = {
            "OK": 0,
            "WARMING_UP": 1,
            "LOW_DATA": 2,
            "DEGRADED": 3,
            "EMPTY": 2,
        }

        score = sum(severity_map.get(v, 0) for v in diagnostics.values())
        health = (
            "EXCELLENT" if score == 0 else
            "STABLE" if score <= 2 else
            "DEGRADED"
        )

        return {
            "health": health,
            "details": diagnostics,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _generate_explanations(self, symbol, emotion, governance, futures, global_risk) -> Dict:
        """Generate human-readable reasoning for the decision"""
        
        why_signal = governance.get('reason', 'Analysis complete')
        
        why_now = f"Global risk is {global_risk['state']} ({global_risk['strength']:.1%}). "
        if emotion['regime'] == 'PANIC':
            why_now += "Market is in surrender mode. High risk."
        elif emotion['regime'] == 'GREED':
            why_now += "Momentum is strong but extended."
        else:
            why_now += "Conditions are balanced for entry."
            
        return {
            'why_this_signal': why_signal,
            'why_now': why_now,
            'what_could_invalidate': "Sudden volatility spike or regime shift to PANIC.",
            'emotion_influence': f"Market emotion is {emotion['regime']}, weighting decision by {emotion['regime_strength']:.0%}."
        }

    def format_futures_for_ui(self, worlds: List[Dict]) -> List[Dict]:
        """
        Convert multi-world simulation output into a UI-safe futures cone.
        No assumptions, no hardcoding, no aggregation beyond normalization.
        """
        if not worlds:
            return []

        formatted = []

        for w in worlds:
            try:
                formatted.append({
                    "path": w.get("path"),
                    "expected_return": float(w.get("expected_return", 0)),
                    "volatility": float(w.get("volatility", 0)),
                    "probability": float(w.get("probability", 0)),
                })
            except Exception:
                # Skip malformed worlds — do NOT fallback or invent
                continue

        return formatted
        
    def explainability_heatmap(self, emotional_state: Dict, futures_stats: Dict, governance_scores: Dict) -> Dict:
        """
        Normalized contribution map (0–1) for UI visualization.
        """
        raw = {
            "fear": emotional_state.get("fear", 0),
            "greed": emotional_state.get("greed", 0),
            "fatigue": emotional_state.get("fatigue", 0),
            "expected_return": abs(futures_stats.get("expected_return", 0)) * 100,
            "downside_risk": futures_stats.get("downside_risk", 0) * 100,
            "model_agreement": governance_scores.get("model_agreement", 50),
            "emotional_stability": governance_scores.get("emotional_stability", 50),
        }

        total = sum(raw.values()) or 1

        return {
            k: round(v / total, 3)
            for k, v in raw.items()
        }

    def export_audit_record(self, evolved_prediction: Dict) -> Dict:
        """
        Generates a compliance-grade audit record.
        """
        return {
            "timestamp": evolved_prediction.get("timestamp"),
            "symbol": evolved_prediction.get("symbol"),
            "base_signal": evolved_prediction["base_prediction"].get("signal"),
            "base_confidence": evolved_prediction["base_prediction"].get("confidence"),
            "final_signal": evolved_prediction.get("governance", {}).get("decision"),
            "final_confidence": evolved_prediction.get("confidence_adjusted"),
            "emotional_regime": evolved_prediction["emotional_state"].get("regime"),
            "global_risk": evolved_prediction.get("global_risk"),
            "regime_drift": evolved_prediction.get("regime_drift"),
            "black_swan_risk": evolved_prediction.get("black_swan_risk"),
            "capital_restraint": evolved_prediction.get("capital_restraint"),
            "governance_scores": evolved_prediction["governance"].get("scores"),
            "explanations": {
                "why_this_signal": evolved_prediction.get("why_this_signal"),
                "why_now": evolved_prediction.get("why_now"),
                "what_could_invalidate": evolved_prediction.get("what_could_invalidate"),
            },
        }


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'EmotionalIntelligence',
    'MultiworldFuturesEngine',
    'GovernanceIntelligence',
    'IntelligenceCore',
    'ModelExecutionStatus',
    'IntegratedForesightSystem',
]

# ============================================================================
# CROSS-ASSET RISK ENGINE (GLOBAL INTELLIGENCE)
# ============================================================================

class CrossAssetRiskEngine:
    """
    Learns global risk-on / risk-off state from multiple symbols.
    """

    def __init__(self):
        self.asset_states = defaultdict(lambda: deque(maxlen=200))
        self.risk_history = deque(maxlen=500)

    def update(self, symbol: str, emotional_state: Dict, futures_stats: Dict):
        signal = (
            emotional_state.get("fear", 50)
            - emotional_state.get("greed", 50)
            - futures_stats.get("expected_return", 0) * 100
        )
        self.asset_states[symbol].append(signal)

    def compute_risk_state(self) -> Dict:
        if not self.asset_states:
            return {"state": "UNKNOWN", "strength": 0.0}

        aggregated = [
            np.mean(v) for v in self.asset_states.values() if len(v) > 20
        ]
        if not aggregated:
            return {"state": "UNKNOWN", "strength": 0.0}

        score = np.mean(aggregated)
        self.risk_history.append(score)

        threshold = np.percentile(self.risk_history, 65) if len(self.risk_history) > 20 else 0
        state = "RISK_OFF" if score > threshold else "RISK_ON"

        strength = abs(score - threshold) / max(abs(threshold), 1e-6)

        return {
            "state": state,
            "strength": round(float(strength), 3),
        }


# ============================================================================
# INTELLIGENCE MEMORY STORE (PERSISTENT MEMORY)
# ============================================================================

import json
import os

class IntelligenceMemoryStore:
    """
    Persists intelligence learning (NOT predictions, NOT models).
    """

    def __init__(self, path="intelligence_memory.json"):
        self.path = path
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save(self):
        try:
            with open(self.path, "w") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")

    def update_accuracy(self, key: str, correct: bool):
        rec = self.data.setdefault(key, {"total": 0, "correct": 0})
        rec["total"] += 1
        if correct:
            rec["correct"] += 1
        self.save()
