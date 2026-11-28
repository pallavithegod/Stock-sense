from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import threading

from backend.db.migrations import apply_migrations, migration_status


def test_concurrent_startups_serialize_migrations_on_a_fresh_database(tmp_path):
    """Several Gunicorn workers run startup() at once against one new SQLite file."""
    db_path = tmp_path / "data" / "stocksense.db"
    workers = 6
    barrier = threading.Barrier(workers)

    def boot():
        barrier.wait()
        return apply_migrations(db_path, backup=False)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(boot) for _ in range(workers)]
        results = [future.result(timeout=60) for future in futures]

    assert migration_status(db_path)["pending_versions"] == []
    # Exactly one process applied each migration; the rest saw them as applied.
    applied = sorted(version for result in results for version in result.applied_versions)
    assert applied == sorted(set(applied))
    assert all(result.pending_versions == [] for result in results)


def test_migrations_are_idempotent_when_rerun(tmp_path):
    db_path = tmp_path / "stocksense.db"
    first = apply_migrations(db_path, backup=False)
    second = apply_migrations(db_path, backup=False)

    assert first.applied_versions
    assert second.applied_versions == []
