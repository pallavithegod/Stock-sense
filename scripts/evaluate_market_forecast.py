"""Evaluate the experimental five-session momentum model against a zero-return baseline."""

from __future__ import annotations

import argparse
import json

from backend.domain.market import normalize_symbol
from backend.domain.predictions.market_model import evaluate_momentum_model
from backend.domain.market.service import MarketUniverse
from backend.services.daily_market_collection import SupabaseDailyBarStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    symbol_options = parser.add_mutually_exclusive_group()
    symbol_options.add_argument("--symbol", action="append", help="Symbol to evaluate; repeat for more.")
    symbol_options.add_argument("--all-universe", action="store_true", help="Evaluate every configured market symbol.")
    parser.add_argument("--limit", type=int, default=1000, help="Maximum recent daily bars to load (1-1000).")
    args = parser.parse_args(argv)
    if args.limit < 1 or args.limit > 1000:
        parser.error("--limit must be between 1 and 1000.")

    raw_symbols = list(MarketUniverse().symbols) if args.all_universe else args.symbol or []
    symbols = list(dict.fromkeys(filter(None, (normalize_symbol(item) for item in raw_symbols))))
    if not symbols:
        parser.error("Provide --symbol or --all-universe.")
    store = SupabaseDailyBarStore.from_env()
    results = {
        symbol: evaluate_momentum_model(store.read_history(symbol, limit=args.limit))
        for symbol in symbols
    }
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
