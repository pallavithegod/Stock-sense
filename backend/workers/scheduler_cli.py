"""Command-line entry point for the local StockSense scheduler."""

from __future__ import annotations

import argparse
import logging

from backend.app import create_app, startup
from backend.app.config import Settings
from backend.workers.jobs import build_default_registry
from backend.workers.scheduler import Scheduler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run StockSense background jobs outside Flask.")
    parser.add_argument("--once", action="store_true", help="Run selected jobs once and exit.")
    parser.add_argument("--job", action="append", dest="jobs", help="Job name to run. May be repeated.")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings.from_env({"enable_workers": True})
    app = create_app(settings)
    startup(app)
    services = app.extensions["stocksense_services"]
    scheduler = Scheduler(registry=build_default_registry(), services=services)

    if args.once:
        failed = False
        for result in scheduler.run_once(args.jobs):
            status = "ok" if result.ok else f"failed: {result.error}"
            print(f"{result.job_name}: {status} attempts={result.attempts}")
            failed = failed or not result.ok
        return 1 if failed else 0

    scheduler.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
