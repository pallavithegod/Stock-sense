"""Input validation helpers for API mutation endpoints."""

from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Any, Callable, Iterable


SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9&.-]{0,19}$")
MAX_TEXT_LENGTH = 1000
MAX_TICKERS = 100


class ValidationError(ValueError):
    """Raised when a request payload fails validation."""

    def __init__(self, message: str, *, field: str | None = None):
        super().__init__(message)
        self.field = field


def validation_error_payload(exc: Exception) -> dict[str, Any]:
    payload = {"success": False, "status": "error", "error": str(exc)}
    if isinstance(exc, ValidationError) and exc.field:
        payload["field"] = exc.field
    return payload


def require_object(value: Any, *, field: str = "payload") -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError("JSON payload must be an object.", field=field)
    return value


def clean_text(value: Any, *, field: str, required: bool = False, max_length: int = MAX_TEXT_LENGTH) -> str | None:
    if value is None or value == "":
        if required:
            raise ValidationError(f"{field} is required.", field=field)
        return None
    text = str(value).strip()
    if not text:
        if required:
            raise ValidationError(f"{field} is required.", field=field)
        return None
    if len(text) > max_length:
        raise ValidationError(f"{field} is too long.", field=field)
    return text


def parse_number(
    value: Any,
    *,
    field: str,
    required: bool = True,
    min_value: float | None = None,
    max_value: float | None = None,
    default: float | None = None,
) -> float | None:
    if value is None or value == "":
        if required:
            raise ValidationError(f"{field} is required.", field=field)
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be a number.", field=field)
    if not math.isfinite(number):
        raise ValidationError(f"{field} must be finite.", field=field)
    if min_value is not None and number < min_value:
        raise ValidationError(f"{field} must be at least {min_value}.", field=field)
    if max_value is not None and number > max_value:
        raise ValidationError(f"{field} must be at most {max_value}.", field=field)
    return number


def parse_int(
    value: Any,
    *,
    field: str,
    required: bool = True,
    min_value: int | None = None,
    max_value: int | None = None,
    default: int | None = None,
) -> int | None:
    number = parse_number(
        value,
        field=field,
        required=required,
        min_value=min_value,
        max_value=max_value,
        default=default,
    )
    if number is None:
        return None
    if int(number) != number:
        raise ValidationError(f"{field} must be an integer.", field=field)
    return int(number)


def parse_date(value: Any, *, field: str, required: bool = False) -> str | None:
    text = clean_text(value, field=field, required=required, max_length=40)
    if text is None:
        return None
    try:
        normalized = text.replace("Z", "+00:00")
        datetime.fromisoformat(normalized)
        return text
    except ValueError:
        try:
            datetime.strptime(text, "%Y-%m-%d")
            return text
        except ValueError:
            raise ValidationError(f"{field} must be an ISO date.", field=field)


def parse_symbol(value: Any, *, field: str = "symbol", normalize_symbol: Callable[[Any], str | None] | None = None) -> str:
    raw = clean_text(value, field=field, required=True, max_length=24)
    symbol = normalize_symbol(raw) if normalize_symbol else str(raw).upper().replace(".NS", "").replace(".BO", "")
    if not symbol or not SYMBOL_RE.match(str(symbol)):
        raise ValidationError(f"{field} is invalid.", field=field)
    return str(symbol).upper()


def parse_choice(value: Any, *, field: str, choices: Iterable[str], default: str | None = None) -> str:
    text = clean_text(value if value is not None else default, field=field, required=True, max_length=20)
    upper = str(text).upper()
    allowed = {choice.upper() for choice in choices}
    if upper not in allowed:
        raise ValidationError(f"{field} must be one of: {', '.join(sorted(allowed))}.", field=field)
    return upper


def validate_methods(value: Any) -> list[str]:
    if value is None:
        return ["FIFO", "LIFO", "HIFO"]
    if not isinstance(value, list):
        raise ValidationError("methods must be a list.", field="methods")
    if not value:
        raise ValidationError("methods cannot be empty.", field="methods")
    methods = [parse_choice(item, field="methods", choices={"FIFO", "LIFO", "HIFO"}) for item in value]
    return list(dict.fromkeys(methods))


def validate_portfolio_create(
    payload: Any,
    *,
    normalize_symbol: Callable[[Any], str | None],
    known_symbols: set[str],
) -> dict[str, Any]:
    data = require_object(payload)
    symbol = parse_symbol(data.get("symbol"), normalize_symbol=normalize_symbol)
    if symbol not in known_symbols:
        raise ValidationError(f"Unknown symbol: {symbol}", field="symbol")
    return {
        "symbol": symbol,
        "quantity": parse_number(data.get("qty", data.get("quantity")), field="quantity", min_value=0.000001),
        "avg_price": parse_number(data.get("avg_price", data.get("price")), field="avg_price", min_value=0.000001),
        "purchase_date": parse_date(data.get("purchase_date", data.get("added_date")), field="purchase_date"),
        "idempotency_key": clean_text(data.get("idempotency_key"), field="idempotency_key", max_length=100),
    }


def validate_portfolio_update(payload: Any, *, normalize_symbol: Callable[[Any], str | None], symbol: Any) -> dict[str, Any]:
    data = require_object(payload)
    return {
        "symbol": parse_symbol(symbol, normalize_symbol=normalize_symbol),
        "quantity": parse_number(data.get("qty", data.get("quantity")), field="quantity", min_value=0.000001),
        "avg_price": parse_number(data.get("avg_price", data.get("price")), field="avg_price", min_value=0.000001),
        "purchase_date": parse_date(data.get("purchase_date", data.get("added_date")), field="purchase_date"),
    }


def validate_lot_update(payload: Any) -> dict[str, Any]:
    data = require_object(payload)
    quantity = parse_number(data.get("qty", data.get("quantity")), field="quantity", required=False, min_value=0.000001)
    buy_price = parse_number(
        data.get("buy_price", data.get("avg_price", data.get("price"))),
        field="buy_price",
        required=False,
        min_value=0.000001,
    )
    buy_date = parse_date(data.get("buy_date", data.get("purchase_date", data.get("added_date"))), field="buy_date")
    if quantity is None and buy_price is None and buy_date is None:
        raise ValidationError("At least one lot field must be provided.", field="payload")
    return {"quantity": quantity, "buy_price": buy_price, "buy_date": buy_date}


def validate_sell_order(payload: Any, *, normalize_symbol: Callable[[Any], str | None]) -> dict[str, Any]:
    data = require_object(payload)
    return {
        "symbol": parse_symbol(data.get("symbol"), normalize_symbol=normalize_symbol),
        "quantity": parse_number(data.get("qty", data.get("quantity")), field="quantity", min_value=0.000001),
        "sell_price": parse_number(data.get("sell_price", data.get("price")), field="sell_price", min_value=0.000001),
        "sell_date": parse_date(data.get("sell_date"), field="sell_date"),
        "method": parse_choice(data.get("method", "FIFO"), field="method", choices={"FIFO", "LIFO", "HIFO"}),
        "fees": parse_number(data.get("fees", 0), field="fees", required=False, min_value=0, default=0.0),
        "notes": clean_text(data.get("notes"), field="notes", required=False, max_length=500),
        "idempotency_key": clean_text(data.get("idempotency_key"), field="idempotency_key", max_length=100),
        "methods": validate_methods(data.get("methods")),
    }


def validate_user_tickers(payload: Any, *, normalize_symbol: Callable[[Any], str | None]) -> dict[str, list[str]]:
    data = require_object(payload)
    result: dict[str, list[str]] = {}
    for key in ("added", "hidden", "tickers"):
        if key not in data:
            continue
        value = data.get(key)
        if not isinstance(value, list):
            raise ValidationError(f"{key} must be a list.", field=key)
        if len(value) > MAX_TICKERS:
            raise ValidationError(f"{key} can contain at most {MAX_TICKERS} symbols.", field=key)
        result[key] = list(dict.fromkeys(parse_symbol(item, field=key, normalize_symbol=normalize_symbol) for item in value))
    if not result:
        raise ValidationError("Provide added, hidden, or tickers.", field="payload")
    return result


def validate_governance_decision(payload: Any, *, normalize_symbol: Callable[[Any], str | None]) -> dict[str, Any]:
    data = require_object(payload)
    return {
        "symbol": parse_symbol(data.get("symbol"), normalize_symbol=normalize_symbol),
        "base_prediction": require_object(data.get("base_prediction"), field="base_prediction"),
        "emotional_state": require_object(data.get("emotional_state"), field="emotional_state"),
        "multiworld_stats": require_object(data.get("multiworld_stats"), field="multiworld_stats"),
        "model_agreement": parse_number(data.get("model_agreement"), field="model_agreement", min_value=0, max_value=1),
    }


def validate_prediction_execution(payload: Any) -> dict[str, Any]:
    data = require_object(payload)
    return {
        "current_price": parse_number(data.get("current_price", 0), field="current_price", required=False, min_value=0, default=0.0),
        "volume": parse_number(data.get("volume", 0), field="volume", required=False, min_value=0, default=0.0),
        "timestamp": parse_date(data.get("timestamp"), field="timestamp") or datetime.now().isoformat(),
    }


def validate_feedback(payload: Any, *, normalize_symbol: Callable[[Any], str | None]) -> dict[str, Any]:
    data = require_object(payload)
    return {
        "symbol": parse_symbol(data.get("symbol"), normalize_symbol=normalize_symbol),
        "evolved_prediction": require_object(data.get("evolved_prediction"), field="evolved_prediction"),
        "realized_return": parse_number(data.get("realized_return"), field="realized_return", min_value=-100, max_value=1000),
    }
