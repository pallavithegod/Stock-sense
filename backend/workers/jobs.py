"""Background job definitions independent from their scheduler."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable
import hashlib
import uuid

from backend.app.services import AppServices
from backend.services.daily_market_collection import DailyMarketCollector, SupabaseDailyBarStore

JobFunction = Callable[[AppServices], dict[str, Any] | None]


@dataclass(frozen=True)
class JobDefinition:
    name: str
    interval_seconds: float
    timeout_seconds: float
    max_retries: int
    run: JobFunction


@dataclass(frozen=True)
class JobResult:
    job_name: str
    idempotency_key: str
    ok: bool
    started_at: str
    finished_at: str
    attempts: int
    error: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)


class JobRegistry:
    def __init__(self, jobs: list[JobDefinition] | None = None):
        self._jobs: dict[str, JobDefinition] = {}
        for job in jobs or []:
            self.register(job)

    def register(self, job: JobDefinition) -> None:
        if job.name in self._jobs:
            raise ValueError(f"Duplicate job registered: {job.name}")
        self._jobs[job.name] = job

    def get(self, name: str) -> JobDefinition:
        return self._jobs[name]

    def all(self) -> list[JobDefinition]:
        return list(self._jobs.values())


def build_default_registry() -> JobRegistry:
    return JobRegistry(
        [
            JobDefinition(
                name="market_refresh",
                interval_seconds=180,
                timeout_seconds=25,
                max_retries=1,
                run=refresh_market_snapshot,
            ),
            JobDefinition(
                name="daily_market_snapshot",
                interval_seconds=86400,
                timeout_seconds=300,
                max_retries=1,
                run=collect_daily_market_snapshot,
            ),
            JobDefinition(
                name="prediction_refresh",
                interval_seconds=300,
                timeout_seconds=25,
                max_retries=1,
                run=refresh_prediction_state,
            ),
            JobDefinition(
                name="sentiment_refresh",
                interval_seconds=300,
                timeout_seconds=20,
                max_retries=1,
                run=refresh_sentiment_state,
            ),
            JobDefinition(
                name="model_evaluation",
                interval_seconds=900,
                timeout_seconds=30,
                max_retries=0,
                run=evaluate_prediction_models,
            ),
            JobDefinition(
                name="retention_report",
                interval_seconds=3600,
                timeout_seconds=30,
                max_retries=0,
                run=collect_retention_report,
            ),
        ]
    )


def make_idempotency_key(job_name: str, scheduled_for: datetime | None = None) -> str:
    scheduled = scheduled_for or datetime.now(timezone.utc)
    bucket = scheduled.replace(microsecond=0).isoformat()
    digest = hashlib.sha256(f"{job_name}:{bucket}".encode("utf-8")).hexdigest()[:16]
    return f"{job_name}:{digest}"


def refresh_market_snapshot(services: AppServices) -> dict[str, Any]:
    health = services.market_data.health()
    services.system_cache["market_refresh"] = {
        "provider_health": health,
        "refreshed_at": _utc_now(),
    }
    return {"providers": sorted(health.keys())}


def collect_daily_market_snapshot(services: AppServices) -> dict[str, Any]:
    store = services.system_cache.get("daily_bar_store")
    if store is None:
        store = SupabaseDailyBarStore.from_env()
    collector = DailyMarketCollector(
        market_data=services.market_data,
        store=store,
        symbols=sorted(services.market.symbols),
        logger=services.logger,
    )
    return collector.collect()


def refresh_prediction_state(services: AppServices) -> dict[str, Any]:
    rows = services.predictions.rows()
    services.system_cache["prediction_refresh"] = {
        "rows": len(rows),
        "refreshed_at": _utc_now(),
    }
    return {"rows": len(rows)}


def refresh_sentiment_state(services: AppServices) -> dict[str, Any]:
    services.system_cache["sentiment_refresh"] = {
        "status": "unavailable_without_news_worker_provider",
        "refreshed_at": _utc_now(),
    }
    return {"status": "unavailable"}


def evaluate_prediction_models(services: AppServices) -> dict[str, Any]:
    prediction_history = getattr(services.runtime, "prediction_history", []) or []
    services.system_cache["model_evaluation"] = {
        "matured_rows": 0,
        "history_rows": len(prediction_history),
        "evaluated_at": _utc_now(),
    }
    return {"history_rows": len(prediction_history), "matured_rows": 0}


def collect_retention_report(services: AppServices) -> dict[str, Any]:
    services.system_cache["retention_report"] = {
        "report_id": str(uuid.uuid4()),
        "status": "manual_cleanup_required",
        "collected_at": _utc_now(),
    }
    return {"status": "manual_cleanup_required"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
