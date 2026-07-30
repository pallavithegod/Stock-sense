"""Thread-safe in-memory worker status for local single-process mode."""

from __future__ import annotations

from dataclasses import asdict
from threading import Lock
from typing import Any

from backend.workers.jobs import JobResult


class WorkerStatus:
    def __init__(self) -> None:
        self._lock = Lock()
        self._running: set[str] = set()
        self._last_success: dict[str, JobResult] = {}
        self._last_result: dict[str, JobResult] = {}

    def try_acquire(self, job_name: str) -> bool:
        with self._lock:
            if job_name in self._running:
                return False
            self._running.add(job_name)
            return True

    def release(self, job_name: str) -> None:
        with self._lock:
            self._running.discard(job_name)

    def record(self, result: JobResult) -> None:
        with self._lock:
            self._last_result[result.job_name] = result
            if result.ok:
                self._last_success[result.job_name] = result

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "running": sorted(self._running),
                "last_result": {
                    name: asdict(result) for name, result in self._last_result.items()
                },
                "last_success": {
                    name: asdict(result) for name, result in self._last_success.items()
                },
            }
