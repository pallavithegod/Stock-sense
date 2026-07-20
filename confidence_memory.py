# -*- coding: utf-8 -*-
# ============================================================
# NEXUS AI — CONFIDENCE MEMORY (UNIFIED & PERSISTENT)
# ============================================================
from utils import encoding

import json
import numpy as np
import logging
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ConfidenceMemory:
    """
    Unified confidence intelligence:
    - Online calibration (short-term honesty)
    - Historical accuracy (long-term trust)
    - Time decay (recency awareness)
    """

    def __init__(self, config, window=300):
        self.config = config
        self.window = window

        # Online calibration memory
        self.history = []

        # Persistent accuracy memory
        self.path = Path(
            self.config.get(
                "confidence_memory_file",
                "data/confidence_memory.json"
            )
        )
        self.memory = self._load_memory()

    # --------------------------------------------------------
    # Persistence
    # --------------------------------------------------------

    def _load_memory(self):
        if self.path.exists():
            try:
                with open(self.path, "r") as f:
                    return json.load(f)
            except Exception:
                logger.error("Failed to load confidence memory", exc_info=True)
        return {}

    def _save_memory(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w") as f:
                json.dump(self.memory, f, indent=2)
        except Exception:
            logger.error("Failed to save confidence memory", exc_info=True)

    # --------------------------------------------------------
    # Online calibration (fast learning)
    # --------------------------------------------------------

    def update_online(self, confidence: float, outcome: int):
        """
        outcome: 1 = correct, 0 = wrong
        """
        self.history.append((confidence, outcome))
        if len(self.history) > self.window:
            self.history.pop(0)

    def calibrate_online(self, confidence: float) -> float:
        if len(self.history) < 50:
            return confidence

        conf = np.array([c for c, _ in self.history])
        out = np.array([o for _, o in self.history])

        bias = out.mean() - conf.mean()
        calibrated = confidence + bias

        return float(np.clip(calibrated, 0.01, 0.99))

    # --------------------------------------------------------
    # Long-term accuracy (symbol memory)
    # --------------------------------------------------------

    def update_symbol(self, symbol: str, outcome: int):
        if symbol not in self.memory:
            self.memory[symbol] = {
                "total": 0,
                "correct": 0,
                "last_updated": None
            }

        data = self.memory[symbol]
        data["total"] += 1
        if outcome == 1:
            data["correct"] += 1

        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._save_memory()

    def historical_accuracy(self, symbol: str) -> float:
        data = self.memory.get(symbol)
        if not data or data["total"] == 0:
            return 0.5  # neutral prior
        return data["correct"] / data["total"]

    # --------------------------------------------------------
    # Time decay (recency awareness)
    # --------------------------------------------------------

    def apply_decay(self, symbol: str, confidence: float) -> float:
        data = self.memory.get(symbol)
        if not data or not data.get("last_updated"):
            return confidence

        try:
            last = datetime.fromisoformat(data["last_updated"])
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - last).total_seconds() / 3600

            decay_rate = self.config.get("confidence_decay_rate", 0.95)
            decay_factor = decay_rate ** (age_hours / 24)

            return max(confidence * decay_factor, 0.20)
        except Exception:
            logger.error("Decay failed", exc_info=True)
            return confidence

    # --------------------------------------------------------
    # FINAL CONFIDENCE PIPELINE
    # --------------------------------------------------------

    def compute(self, symbol: str, raw_confidence: float) -> float:
        """
        raw → calibrated → trust-adjusted → decayed
        """

        conf = self.calibrate_online(raw_confidence)
        acc = self.historical_accuracy(symbol)
        conf *= (0.7 + 0.3 * acc)
        conf = self.apply_decay(symbol, conf)

        return round(float(np.clip(conf, 0.01, 0.99)), 3)
