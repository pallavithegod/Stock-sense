"""Backfill persisted daily bars for selected symbols using the configured provider."""

from __future__ import annotations

import argparse
import json
import logging

from backend.services.daily_market_collection import (
    DailyMarketCollector,
    PartialCollectionError,
    SupabaseDailyBarStore,
)
from backend.services.market_data import build_market_data_client, normalize_symbol


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", action="append", required=True, help="Symbol to backfill; repeat to add symbols.")
    parser.add_argument("--period", choices=("2y", "5y", "max"), default="2y")
    args = parser.parse_args(argv)

    symbols = list(dict.fromkeys(filter(None, (normalize_symbol(item) for item in args.symbol))))
    if not symbols:
        parser.error("Provide at least one valid --symbol.")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    collector = DailyMarketCollector(
        market_data=build_market_data_client(disabled=False, timeout_seconds=10, cache_ttl_seconds=1),
        store=SupabaseDailyBarStore.from_env(),
        symbols=symbols,
    )
    try:
        result = collector.collect(period=args.period)
    except PartialCollectionError as exc:
        print(json.dumps({"period": args.period, **exc.result, "failures": exc.failures}, sort_keys=True))
        return 1
    print(json.dumps({"period": args.period, **result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
