# ============================================================
# StockSense model intelligence core
# Regime Weights | Meta Learning | Multi-World Simulation
# ============================================================

import logging
import collections
import numpy as np

logger = logging.getLogger(__name__)

# ============================================================
# REGIME-AWARE MODEL WEIGHTING
# ============================================================

class RegimeModelWeighter:
    """
    Dynamically weights existing models based on market regime.
    """

    def get_weights(self, regime: str) -> dict:
        base = {
            "rf": 0.25,
            "gb": 0.25,
            "lstm": 0.25,
            "rl": 0.25
        }

        if regime == "TRENDING":
            base.update({"lstm": 0.45, "rl": 0.20})
        elif regime == "RANGING":
            base.update({"rf": 0.35, "gb": 0.35})
        elif regime == "HIGH_VOLATILITY":
            base.update({"rl": 0.40})

        total = sum(base.values())
        return {k: v / total for k, v in base.items()}

# ============================================================
# META-MODEL WEIGHT LEARNER (EXPERIENCE MEMORY)
# ============================================================

class MetaModelWeighter:
    """
    Learns which model performs better per regime over time.
    """

    def __init__(self):
        self.stats = collections.defaultdict(
            lambda: collections.defaultdict(lambda: {"wins": 0, "losses": 0})
        )

    def update(self, regime_id: str, model_name: str, correct: bool):
        record = self.stats[regime_id][model_name]
        if correct:
            record["wins"] += 1
        else:
            record["losses"] += 1

    def get_weight(self, regime_id: str, model_name: str) -> float:
        record = self.stats[regime_id][model_name]
        total = record["wins"] + record["losses"]
        return record["wins"] / total if total > 0 else 1.0

# ============================================================
# MULTI-WORLD FUTURE SIMULATOR (WHAT-IF ENGINE)
# ============================================================

class MultiWorldSimulator:
    """
    Simulates multiple plausible futures using
    existing model outputs.

    No new models.
    No hardcoding.
    No UI changes.
    """

    def simulate(self, predictions: dict, confidences: dict) -> dict:
        try:
            if not predictions:
                return self._neutral("No active model signals")

            values = np.array(list(predictions.values()), dtype=float)

            expected_path = float(np.mean(values))
            disagreement = float(np.std(values))

            best_case = float(np.max(values))
            worst_case = float(np.min(values))

            confs = np.array(list(confidences.values()), dtype=float) / 100.0
            confidence_spread = float(np.std(confs)) if len(confs) > 1 else 0.0

            black_swan_risk = min(1.0, disagreement + confidence_spread)

            if black_swan_risk > 0.65:
                fragility = "EXTREME"
            elif black_swan_risk > 0.45:
                fragility = "HIGH"
            elif black_swan_risk > 0.25:
                fragility = "MODERATE"
            else:
                fragility = "LOW"

            return {
                "expected_path": round(expected_path, 3),
                "uncertainty": round(disagreement, 3),
                "best_case": best_case,
                "worst_case": worst_case,
                "black_swan_risk": round(black_swan_risk, 2),
                "fragility": fragility,
                "story": self._human_story(fragility)
            }

        except Exception as e:
            logger.error("Multi-world simulation failed", exc_info=True)
            return self._neutral(str(e))

    def _neutral(self, reason: str) -> dict:
        return {
            "expected_path": 0.0,
            "uncertainty": 1.0,
            "best_case": 0.0,
            "worst_case": 0.0,
            "black_swan_risk": 1.0,
            "fragility": "UNKNOWN",
            "story": f"AI paused future simulation: {reason}"
        }

    def _human_story(self, fragility: str) -> str:
        if fragility == "EXTREME":
            return "Markets are unstable. Rare events can dominate. AI advises caution."
        if fragility == "HIGH":
            return "Direction exists but is fragile. News sensitivity is high."
        if fragility == "MODERATE":
            return "Most models align, though uncertainty remains."
        return "Models align well. Market behavior appears stable."
