"""Research and foresight service helpers for the app-factory path."""

from __future__ import annotations

from typing import Any, Callable


PriceHistoryFetcher = Callable[[str, str, str], Any]
NormalizeSymbol = Callable[[str], str | None]
ResearchDependencyError = (AttributeError, KeyError, TypeError, ValueError, RuntimeError, IndexError)


def _to_yfinance_symbol(raw_symbol: str, base_symbol: str) -> str:
    cleaned = str(raw_symbol or "").upper().strip()
    if cleaned.endswith(".NS") or cleaned.endswith(".BO"):
        return cleaned
    return f"{base_symbol}.NS"


def _empty_payload(symbol: str, section: str, reason: str) -> dict[str, Any]:
    return {
        "success": True,
        "available": False,
        "symbol": symbol,
        section: {
            "available": False,
            "success": False,
            "reason": reason,
            "error": reason,
        },
    }


def build_emotional_state_payload(
    symbol: str,
    *,
    normalize_symbol: NormalizeSymbol,
    fetch_price_history: PriceHistoryFetcher,
    foresight_system: Any,
    logger: Any,
) -> dict[str, Any]:
    """Build a safe emotional-state payload without throwing HTTP 500s."""
    try:
        base_symbol = normalize_symbol(symbol)
        if not base_symbol:
            return _empty_payload(symbol, "emotional_state", "Invalid symbol")

        yf_symbol = _to_yfinance_symbol(symbol, base_symbol)
        df = fetch_price_history(yf_symbol, "1y", "1d")
        if df is None or getattr(df, "empty", True) or "Close" not in df:
            return _empty_payload(
                base_symbol,
                "emotional_state",
                f"No historical price data available for {yf_symbol}",
            )

        emotional_state = foresight_system.emotion_engine.update_emotional_state(df, base_symbol)
        return {
            "success": True,
            "available": True,
            "symbol": base_symbol,
            "emotional_state": emotional_state,
        }
    except ResearchDependencyError as exc:
        logger.error("Emotional state build failed for %s: %s", symbol, exc, exc_info=True)
        return _empty_payload(str(symbol), "emotional_state", str(exc))


def build_futures_analysis_payload(
    symbol: str,
    *,
    normalize_symbol: NormalizeSymbol,
    fetch_price_history: PriceHistoryFetcher,
    foresight_system: Any,
    logger: Any,
) -> dict[str, Any]:
    """Build a safe multi-world futures payload without throwing HTTP 500s."""
    try:
        base_symbol = normalize_symbol(symbol)
        if not base_symbol:
            return _empty_payload(symbol, "futures", "Invalid symbol")

        yf_symbol = _to_yfinance_symbol(symbol, base_symbol)
        df = fetch_price_history(yf_symbol, "1y", "1d")
        if df is None or getattr(df, "empty", True) or "Close" not in df:
            return _empty_payload(base_symbol, "futures", f"No historical price data available for {yf_symbol}")

        current_price = float(df["Close"].iloc[-1])
        base_prediction = {"signal": "HOLD", "confidence": 50}
        emotional_state = foresight_system.emotion_engine.update_emotional_state(df, base_symbol)
        result = foresight_system.futures_engine.generate_worlds(
            current_price=current_price,
            historical_data=df,
            base_prediction=base_prediction,
            emotional_state=emotional_state,
            prediction_horizon_days=5,
        )
        result_success = bool(result.get("success", False)) if isinstance(result, dict) else True
        return {
            "success": True,
            "available": result_success,
            "symbol": base_symbol,
            "current_price": current_price,
            "futures": result,
        }
    except ResearchDependencyError as exc:
        logger.error("Futures analysis build failed for %s: %s", symbol, exc, exc_info=True)
        return _empty_payload(str(symbol), "futures", str(exc))
