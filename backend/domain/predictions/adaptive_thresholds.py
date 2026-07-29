"""Adaptive-threshold row mapping helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


THRESHOLD_COLUMNS = (
    "strong_buy_threshold",
    "buy_threshold",
    "strong_sell_threshold",
    "sell_threshold",
    "hold_threshold",
    "rsi_oversold",
    "rsi_overbought",
    "vol_high_risk",
    "vol_medium_risk",
)


@dataclass(frozen=True)
class AdaptiveThresholdRow:
    strong_buy_threshold: float
    buy_threshold: float
    strong_sell_threshold: float
    sell_threshold: float
    hold_threshold: float
    rsi_oversold: float
    rsi_overbought: float
    vol_high_risk: float
    vol_medium_risk: float

    def to_dict(self) -> dict[str, float]:
        return {
            "strong_buy_threshold": self.strong_buy_threshold,
            "buy_threshold": self.buy_threshold,
            "strong_sell_threshold": self.strong_sell_threshold,
            "sell_threshold": self.sell_threshold,
            "hold_threshold": self.hold_threshold,
            "rsi_oversold": self.rsi_oversold,
            "rsi_overbought": self.rsi_overbought,
            "vol_high_risk": self.vol_high_risk,
            "vol_medium_risk": self.vol_medium_risk,
        }


def map_adaptive_threshold_row(row: Mapping[str, Any] | Sequence[Any]) -> AdaptiveThresholdRow:
    if isinstance(row, Mapping):
        values = [row[column] for column in THRESHOLD_COLUMNS]
    else:
        values = list(row)
        if len(values) != len(THRESHOLD_COLUMNS):
            raise ValueError(f"Expected {len(THRESHOLD_COLUMNS)} threshold values, got {len(values)}")
    return AdaptiveThresholdRow(**{column: float(value) for column, value in zip(THRESHOLD_COLUMNS, values)})
