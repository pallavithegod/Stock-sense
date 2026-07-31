# StockSense Deployment Notes

These notes describe the current production-shaped deployment path for the
Flask API. The React frontend is built and hosted separately from the API.

## WSGI Command

Run the API with Gunicorn:

```powershell
gunicorn -c gunicorn.conf.py backend.wsgi:app
```

Useful environment variables:

```env
APP_ENV=production
FLASK_SECRET_KEY=replace_with_at_least_32_random_characters
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
GUNICORN_WORKERS=2
GUNICORN_THREADS=4
GUNICORN_TIMEOUT=60
GUNICORN_GRACEFUL_TIMEOUT=30
DISABLE_STARTUP_NETWORK=True
OPEN_BROWSER=False
REQUIRE_MUTATION_TOKEN=True
DEMO_WRITE_TOKEN=replace_with_a_private_demo_token
CONTENT_SECURITY_POLICY=default-src 'self'; frame-ancestors 'self'; base-uri 'self'
```

The WSGI entry point runs the Flask startup lifecycle once so readiness checks
can verify schema availability before traffic is routed.

## Docker

Build the backend API image:

```powershell
docker build -t stocksense-api .
```

Run it with explicit runtime volumes:

```powershell
docker run --rm -p 5000:5000 `
  -e APP_ENV=production `
  -e FLASK_SECRET_KEY=replace_with_at_least_32_random_characters `
  -e REQUIRE_MUTATION_TOKEN=True `
  -e DEMO_WRITE_TOKEN=replace_with_a_private_demo_token `
  -v stocksense-data:/app/data `
  -v stocksense-logs:/app/logs `
  -v stocksense-cache:/app/cache `
  -v stocksense-models:/app/models `
  stocksense-api
```

The image runs as a non-root user and exposes `/health/live` as its Docker
health check.

No Compose file is included yet because Redis is still deferred. Add Compose
only when a deployment needs multiple web/worker processes, Redis-backed cache,
or shared rate-limit state.

## Health Checks

- `/health/live` returns `200` when the API process can respond.
- `/health/ready` returns `200` only after startup has completed and SQLite can
  be opened. Provider outages and workers are optional for readiness.

The readiness payload is intentionally sanitized and does not expose secrets or
raw exception details.

## Workers

Run scheduled jobs as a separate process:

```powershell
python -m backend.workers.scheduler_cli
```

For one-shot local validation:

```powershell
python -m backend.workers.scheduler_cli --once
```

The Flask app factory does not start workers. This prevents duplicate jobs when
Gunicorn uses multiple web workers.

## Logs And Error Reporting

The API writes structured JSON lines to:

```text
logs/stocksense.jsonl
```

The same JSON records are emitted to stdout outside test mode so hosting
platforms can collect them. Request records include request ID, route, status,
and latency. Market-data records include provider, state, cache outcome, and
latency. Worker records include job name, idempotency key, attempts, outcome,
and error summary.

Local log rotation is controlled with:

```env
STOCKSENSE_LOG_MAX_BYTES=5242880
STOCKSENSE_LOG_BACKUP_COUNT=3
```

For external error reporting, set `SENTRY_DSN` and install `sentry-sdk` in the
runtime image/environment. Without that optional dependency, the app logs a
structured `error_reporting_unavailable` event and continues.

## Backup And Restore

Create a SQLite backup:

```powershell
python scripts/sqlite_maintenance.py backup
```

Validate the current schema:

```powershell
python scripts/sqlite_maintenance.py check
```

Dry-run retention cleanup before deleting any rows:

```powershell
python scripts/sqlite_maintenance.py cleanup-report
```

Database cleanup requires an explicit confirmation token and creates a backup
first. Keep `data/` on a persistent volume for container deployments.

## Graceful Shutdown

Gunicorn uses `GUNICORN_GRACEFUL_TIMEOUT` to allow in-flight requests to finish
before workers exit. Keep scheduled jobs in the separate scheduler process so
API shutdown does not interrupt background work unexpectedly.
