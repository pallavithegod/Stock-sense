from __future__ import annotations

import json
import logging
from pathlib import Path

from backend.app import startup
from backend.workers.jobs import JobDefinition, JobRegistry
from backend.workers.scheduler import Scheduler


def test_health_endpoints_distinguish_liveness_and_readiness(app_module, client):
    app_module.app.config["_STARTUP_COMPLETE"] = False

    live = client.get("/health/live")
    not_ready = client.get("/health/ready")

    assert live.status_code == 200
    assert live.get_json()["status"] == "ok"
    assert not_ready.status_code == 503
    assert not_ready.get_json()["status"] == "not_ready"

    startup(app_module.app)
    ready = client.get("/health/ready")

    assert ready.status_code == 200
    assert ready.get_json()["status"] == "ready"
    assert ready.get_json()["checks"] == {
        "startup": True,
        "database": True,
        "workers_optional": True,
        "providers_optional": True,
    }


def test_security_and_observability_headers_are_present(client):
    response = client.get("/health/live", headers={"X-Request-ID": "phase12-request"})

    assert response.headers["X-Request-ID"] == "phase12-request"
    assert response.headers["Content-Security-Policy"].startswith("default-src")
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_request_observability_writes_json_log(client, app_module):
    log_path = Path(app_module.app.config["STOCKSENSE_LOG_PATH"])

    response = client.get("/health/live", headers={"X-Request-ID": "log-check-phase12"})

    assert response.status_code == 200
    records = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    assert any(
        record["event"] == "http_request"
        and record["request_id"] == "log-check-phase12"
        and record["path"] == "/health/live"
        for record in records
    )


def test_worker_scheduler_logs_structured_job_results(app_module, tmp_path):
    log_path = tmp_path / "worker.jsonl"
    logger = logging.getLogger(f"worker-test-{log_path.name}")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

    registry = JobRegistry([
        JobDefinition(
            "ops_job",
            interval_seconds=60,
            timeout_seconds=5,
            max_retries=0,
            run=lambda _services: {"cache_outcome": "not_applicable"},
        )
    ])
    scheduler = Scheduler(registry=registry, services=app_module.services, logger=logger)

    [result] = scheduler.run_once()

    assert result.ok is True
    handler.close()
    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert records[-1]["event"] == "worker_job"
    assert records[-1]["job_name"] == "ops_job"
    assert records[-1]["ok"] is True
