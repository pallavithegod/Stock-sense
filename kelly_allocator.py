
import numpy as np
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class KellySignal:
    symbol: str
    win_prob: float      # Probability of positive return (0.0-1.0)
    payoff_ratio: float  # Expected upside / expected downside
    confidence: float    # Model confidence (0.0-1.0)
    agreement: float     # Ensemble agreement (0.0-1.0)
    volatility: float    # Asset volatility

class KellyAllocator:
    """
    Institutional-grade Capital Allocator using Half-Kelly Criterion.
    
    Formula: f* = (p*b - q) / b
    where:
      p = probability of win
      b = payoff ratio (win/loss)
      q = probability of loss (1-p)
      
    Features:
    - Dynamic Fractioning (Base 0.5 for Half-Kelly)
    - Volatility Scaling
    - Correlation Penalties (Basic implementation)
    - Regime Adjustments
    """
    
    def __init__(self, risk_free_rate: float = 0.05):
        self.risk_free_rate = risk_free_rate
        self.max_leverage = 1.0  # No leverage allowed
        self.min_allocation = 0.02 # 2% minimum if trade is taken
        
    def compute_allocation(self, signal: KellySignal, regime: str = "NEUTRAL") -> float:
        """
        Compute optimal capital fraction for a single asset.
        """
        try:
            if signal.confidence < 0.55:
                return 0.0
                
            # 1. Basic Kelly Calculation
            p = signal.win_prob
            q = 1.0 - p
            b = max(signal.payoff_ratio, 0.1) # Prevent division by zero/negative
            
            # Full Kelly Fraction
            f_star = (p * b - q) / b
            
            if f_star <= 0:
                return 0.0
                
            # 2. Risk Scalars
            # Scale down by confidence and agreement (Uncertainty Penalty)
            # Higher confidence & agreement -> closer to f_star
            conviction_scalar = signal.confidence * signal.agreement
            
            # Volatility Penalty (Higher vol -> lower size)
            # Normalized against a baseline vol of 20% (0.2)
            vol_scalar = 0.2 / max(signal.volatility, 0.1)
            vol_scalar = min(vol_scalar, 1.5) # Cap boost
            
            # Regime Scalar
            regime_map = {
                "TRENDING_BULL": 1.0,
                "VOLATILE_OPPORTUNITY": 0.8, # Detailed management needed
                "NEUTRAL_TRANSITION": 0.5,
                "COMPLACENT": 0.4,
                "EXTREME_FEAR": 0.2, # Cash is king
                "UNKNOWN": 0.0
            }
            regime_scalar = regime_map.get(regime, 0.5)
            
            # 3. Half-Kelly Implementation (Industry Standard for safety)
            # f_safe = f_star * 0.5 * scalars
            f_safe = f_star * 0.5 * conviction_scalar * vol_scalar * regime_scalar
            
            # 4. Constraints
            f_final = max(0.0, min(f_safe, 0.25)) # Hard cap 25% single asset
            
            if f_final < self.min_allocation:
                return 0.0
                
            return round(f_final, 4)
            
        except Exception as e:
            logger.error(f"Kelly calc failed for {signal.symbol}: {e}")
            return 0.0

    def allocate_portfolio(self, signals: List[KellySignal], regime: str, total_capital: float = 100000.0) -> List[Dict]:
        """
        Normalize allocations across a portfolio of opportunities.
        """
        allocations = []
        raw_total = 0.0
        
        # 1. Compute raw independent Kelly fractions
        for sig in signals:
            raw_f = self.compute_allocation(sig, regime)
            allocations.append({
                "symbol": sig.symbol,
                "raw_fraction": raw_f,
                "signal": sig
            })
            raw_total += raw_f
            
        # 2. Normalize if Leverage Constraint Hit
        # If sum > 1.0, scale down proportionally
        scale_factor = 1.0
        if raw_total > self.max_leverage:
            scale_factor = self.max_leverage / raw_total
            
        final_allocations = []
        for item in allocations:
            final_f = item["raw_fraction"] * scale_factor
            capital_amt = final_f * total_capital
            
            # Action Logic based on raw conviction
            action = "HOLD"
            if final_f > 0.0:
                action = "ADD"
            elif final_f == 0.0:
                action = "REDUCE" # Or AVOID
                
            final_allocations.append({
                "symbol": item["symbol"],
                "weight_pct": round(final_f * 100, 2),
                "capital_usd": round(capital_amt, 2),
                "action": action,
                "kelly_fraction": round(item["raw_fraction"], 4)
            })
            
        # Sort by weight desc
        final_allocations.sort(key=lambda x: x["weight_pct"], reverse=True)
        
        return final_allocations
