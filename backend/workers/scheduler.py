"""Small local scheduler for StockSense background jobs."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime, timezone
from threading import Event
from time import monotonic
from typing import Iterable
import logging
import time

from backend.app.services import AppServices
from backend.workers.jobs import JobDefinition, JobRegistry, JobResult, make_idempotency_key
from backend.workers.status import WorkerStatus


class Scheduler:
    def __init__(
        self,
        *,
        registry: JobRegistry,
        services: AppServices,
        logger: logging.Logger | None = None,
        status: WorkerStatus | None = None,
    ):
        self.registry = registry
        self.services = services
        self.logger = logger or logging.getLogger("stocksense.scheduler")
        self.status = status or WorkerStatus()
        self.services.worker_status = self.status
        self.services.runtime.worker_status = self.status
        self._stop = Event()
        self._next_run: dict[str, float] = {
            job.name: 0.0 for job in self.registry.all()
        }

    def run_once(self, names: Iterable[str] | None = None) -> list[JobResult]:
        jobs = self.registry.all() if names is None else [self.registry.get(name) for name in names]
        return [self._run_job(job) for job in jobs]

    def serve_forever(self, *, poll_seconds: float = 1.0) -> None:
        while not self._stop.is_set():
            now = monotonic()
            for job in self.registry.all():
                if now >= self._next_run[job.name]:
                    result = self._run_job(job)
                    self.logger.info(
                        "worker_job_complete name=%s ok=%s attempts=%s",
                        result.job_name,
                        result.ok,
                        result.attempts,
                    )
                    self._next_run[job.name] = monotonic() + job.interval_seconds
            self._stop.wait(poll_seconds)

    def stop(self) -> None:
        self._stop.set()

    def snapshot(self) -> dict[str, object]:
        return self.status.snapshot()

    def _run_job(self, job: JobDefinition) -> JobResult:
        started = datetime.now(timezone.utc)
        idempotency_key = make_idempotency_key(job.name, started)
        if not self.status.try_acquire(job.name):
            result = JobResult(
                job_name=job.name,
                idempotency_key=idempotency_key,
                ok=False,
                started_at=started.isoformat(),
                finished_at=datetime.now(timezone.utc).isoformat(),
                attempts=0,
                error="job_already_running",
            )
            self.status.record(result)
            return result

        try:
            attempts = 0
            last_error: str | None = None
            detail: dict[str, object] = {}
            while attempts <= job.max_retries:
                attempts += 1
                try:
                    detail = self._run_with_timeout(job)
                    result = JobResult(
                        job_name=job.name,
                        idempotency_key=idempotency_key,
                        ok=True,
                        started_at=started.isoformat(),
                        finished_at=datetime.now(timezone.utc).isoformat(),
                        attempts=attempts,
                        detail=dict(detail or {}),
                    )
                    self.status.record(result)
                    return result
                except Exception as exc:
                    last_error = str(exc)
                    if attempts <= job.max_retries:
                        time.sleep(min(2.0, 0.25 * attempts))

            result = JobResult(
                job_name=job.name,
                idempotency_key=idempotency_key,
                ok=False,
                started_at=started.isoformat(),
                finished_at=datetime.now(timezone.utc).isoformat(),
                attempts=attempts,
                error=last_error or "job_failed",
            )
            self.status.record(result)
            return result
        finally:
            self.status.release(job.name)

    def _run_with_timeout(self, job: JobDefinition) -> dict[str, object]:
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"stocksense-{job.name}")
        future = executor.submit(job.run, self.services)
        try:
            return dict(future.result(timeout=job.timeout_seconds) or {})
        except TimeoutError as exc:
            future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)
            raise TimeoutError(f"{job.name} timed out after {job.timeout_seconds}s") from exc
        finally:
            if future.done():
                executor.shutdown(wait=True)
