from __future__ import annotations

import time

from backend.workers.jobs import JobDefinition, JobRegistry, build_default_registry
from backend.workers.scheduler import Scheduler
from backend.workers.status import WorkerStatus


def test_default_registry_defines_independent_jobs():
    registry = build_default_registry()
    names = {job.name for job in registry.all()}

    assert names == {
        "market_refresh",
        "daily_market_snapshot",
        "prediction_refresh",
        "sentiment_refresh",
        "model_evaluation",
        "retention_report",
    }
    assert all(job.interval_seconds > 0 for job in registry.all())
    assert all(job.timeout_seconds > 0 for job in registry.all())


def test_scheduler_records_success_and_attaches_status_to_services(app_module):
    def run_job(services):
        services.system_cache["unit_job"] = "ran"
        return {"cache_key": "unit_job"}

    registry = JobRegistry([
        JobDefinition("unit_job", interval_seconds=60, timeout_seconds=5, max_retries=0, run=run_job)
    ])
    scheduler = Scheduler(registry=registry, services=app_module.services)

    [result] = scheduler.run_once()

    assert result.ok is True
    assert result.attempts == 1
    assert result.detail == {"cache_key": "unit_job"}
    assert app_module.services.system_cache["unit_job"] == "ran"
    assert app_module.services.worker_status is scheduler.status
    assert app_module.services.runtime.worker_status is scheduler.status
    assert scheduler.snapshot()["last_success"]["unit_job"]["ok"] is True


def test_worker_status_prevents_duplicate_job_runs():
    status = WorkerStatus()

    assert status.try_acquire("market_refresh") is True
    assert status.try_acquire("market_refresh") is False

    status.release("market_refresh")

    assert status.try_acquire("market_refresh") is True


def test_scheduler_retries_failures_and_records_last_result(app_module):
    attempts = {"count": 0}

    def flaky_job(_services):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("temporary outage")
        return {"attempt": attempts["count"]}

    registry = JobRegistry([
        JobDefinition("flaky_job", interval_seconds=60, timeout_seconds=5, max_retries=1, run=flaky_job)
    ])
    scheduler = Scheduler(registry=registry, services=app_module.services)

    [result] = scheduler.run_once()

    assert result.ok is True
    assert result.attempts == 2
    assert result.detail == {"attempt": 2}
    assert scheduler.snapshot()["last_result"]["flaky_job"]["ok"] is True


def test_scheduler_timeout_is_recorded_without_marking_success(app_module):
    def slow_job(_services):
        time.sleep(0.2)
        return {"done": True}

    registry = JobRegistry([
        JobDefinition("slow_job", interval_seconds=60, timeout_seconds=0.01, max_retries=0, run=slow_job)
    ])
    scheduler = Scheduler(registry=registry, services=app_module.services)

    [result] = scheduler.run_once()

    assert result.ok is False
    assert "timed out" in str(result.error)
    assert "slow_job" not in scheduler.snapshot()["last_success"]


def test_flask_status_reports_workers_as_optional(app_module, client):
    app_module.services.worker_status = None
    app_module.services.runtime.worker_status = None

    status = client.get("/api/v1/system/status").get_json()["data"]
    diagnostics = client.get("/api/v1/system/diagnostics").get_json()["data"]
    bootstrap = client.get("/api/v1/system/bootstrap/status").get_json()["data"]

    assert status["worker_status"]["mode"] == "not_started_by_flask"
    assert diagnostics["worker_required_for_readiness"] is False
    assert bootstrap["workers_started"] is False
    assert bootstrap["scheduler_command"] == "python -m backend.workers.scheduler_cli"
