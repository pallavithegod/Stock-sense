# -*- coding: utf-8 -*-
from utils import encoding
import numpy as np
import pandas as pd
import logging
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

# ============================================================
# REGIME MEMORY (UNSUPERVISED, ONLINE)
# ============================================================

class RegimeMemory:
    """
    Continuously learns latent market regimes via online clustering.
    """

    def __init__(self, max_regimes: int = 8, min_buffer: int = 50):
        self.model = MiniBatchKMeans(
            n_clusters=max_regimes,
            batch_size=32
        )
        self.buffer = []
        self.min_buffer = min_buffer
        self.ready = False

    def update(self, embedding: np.ndarray) -> None:
        self.buffer.append(embedding)

        if len(self.buffer) >= self.min_buffer:
            X = np.asarray(self.buffer)
            self.model.partial_fit(X)
            self.ready = True
            self.buffer = self.buffer[-2 * self.min_buffer :]

    def get_regime_id(self, embedding: np.ndarray) -> int:
        if not self.ready:
            return -1
        return int(self.model.predict(embedding.reshape(1, -1))[0])

# ============================================================
# MARKET REGIME DETECTOR (LIVE, STATELESS)
# ============================================================

class MarketRegimeDetector:
    """
    Detects live market regimes using efficiency and volatility structure.
    """

    def detect(self, price_df: pd.DataFrame) -> dict:
        try:
            closes = price_df["Close"].dropna()
            returns = closes.pct_change().dropna()

            if len(returns) < 30:
                return {"regime": "UNKNOWN"}

            volatility = returns.std() * np.sqrt(len(returns))

            directional_move = abs(closes.iloc[-1] - closes.iloc[0])
            total_path = closes.diff().abs().sum()
            efficiency_ratio = directional_move / (total_path + 1e-9)

            if volatility > returns.std() * 1.25:
                regime = "HIGH_VOLATILITY"
            elif efficiency_ratio > 0.35:
                regime = "TRENDING"
            else:
                regime = "RANGING"

            return {
                "regime": regime,
                "volatility": float(volatility),
                "efficiency": float(efficiency_ratio)
            }

        except Exception:
            logger.error("Market regime detection failed", exc_info=True)
            return {"regime": "UNKNOWN"}


# ============================================================
# REGIME EMBEDDING ENGINE (CONTINUOUS, ONLINE)
# ============================================================

class RegimeEmbeddingEngine:
    """
    Learns continuous, unlabeled regime embeddings in real time.
    """

    def __init__(self):
        self.scaler = StandardScaler()
        self.fitted = False

    def transform(self, price_df: pd.DataFrame) -> np.ndarray:
        try:
            returns = price_df["Close"].pct_change().dropna()
            if len(returns) < 30:
                return np.zeros(6, dtype=float)

            features = np.array([
                returns.mean(),
                returns.std(),
                returns.skew(),
                returns.kurtosis(),
                np.abs(returns).mean(),
                (returns > 0).mean()
            ], dtype=float).reshape(1, -1)

            if not self.fitted:
                self.scaler.partial_fit(features)
                self.fitted = True

            return self.scaler.transform(features)[0]

        except Exception:
            logger.error("Regime embedding failed", exc_info=True)
            return np.zeros(6, dtype=float)
