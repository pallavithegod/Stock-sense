# StockSense Deployment Notes

These notes describe the current production-shaped deployment path for the
Flask API. The React frontend is built and hosted separately from the API.

## Which Instructions To Follow

For the selected Supabase + Render + Vercel launch, follow the numbered steps
under **Supabase Authentication And User Portfolios** in order. The WSGI,
Docker, worker, and SQLite backup sections below are reference instructions;
they are not extra steps for that hosting path. Use the Render Cron Job in the
numbered steps rather than starting the continuous scheduler.

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
REQUIRE_AUTH=True
GUNICORN_WORKERS=2
GUNICORN_THREADS=4
GUNICORN_TIMEOUT=60
GUNICORN_GRACEFUL_TIMEOUT=30
DISABLE_STARTUP_NETWORK=False
OPEN_BROWSER=False
CONTENT_SECURITY_POLICY=default-src 'self'; frame-ancestors 'self'; base-uri 'self'
```

For Supabase-backed production, also set the Supabase variables listed in the
deployment steps below. Do not combine `REQUIRE_AUTH=True` with the legacy
`REQUIRE_MUTATION_TOKEN` demo configuration.

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
  --env-file .env.production `
  -v stocksense-data:/app/data `
  -v stocksense-logs:/app/logs `
  -v stocksense-cache:/app/cache `
  -v stocksense-models:/app/models `
  stocksense-api
```

The image runs as a non-root user and exposes `/health/live` as its Docker
health check.
Keep `.env.production` out of source control; it must contain the production
Supabase settings shown below, including `REQUIRE_AUTH=True`.

No Compose file is included yet because Redis is still deferred. Add Compose
only when a deployment needs multiple web/worker processes, Redis-backed cache,
or shared rate-limit state.

## Health Checks

- `/health/live` returns `200` when the API process can respond.
- `/health/ready` returns `200` only after startup has completed and SQLite can
  be opened. Provider outages and workers are optional for readiness.

The readiness payload is intentionally sanitized and does not expose secrets or
raw exception details.

## Supabase Authentication And User Portfolios

The production API requires Supabase Auth when `APP_ENV=production` unless
`REQUIRE_AUTH` is explicitly overridden. Portfolio API reads and writes require
a valid Supabase access token; Postgres row-level security and explicit
`user_id` filters keep each user's holdings private. Anonymous market browsing
remains available, and the public dashboard omits portfolio data.

1. Create a Supabase project and open **SQL Editor**.
2. Apply `supabase/migrations/20261125_market_data_and_portfolios.sql`.
3. In **Authentication → URL Configuration**, set the Vercel URL as the Site
   URL and add the production URL plus
   `https://<your-vercel-domain>/portfolio`
   to Redirect URLs (or use a narrowly scoped `https://<your-vercel-domain>/**`
   pattern). Add approved preview URLs as needed. Keep email confirmation
   enabled for public self-sign-up. Configure a production SMTP sender before
   inviting real users.
4. Create a Render web service from the repository. Set its root directory to
   the repository root, build command to `pip install -e .`, and start command
   to `gunicorn -c gunicorn.conf.py backend.wsgi:app`.
5. Set these Render API environment variables:

   ```env
   APP_ENV=production
   REQUIRE_AUTH=True
   FLASK_SECRET_KEY=<random secret, at least 32 characters>
   SUPABASE_URL=https://<project-ref>.supabase.co
   SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
   SUPABASE_SECRET_KEY=sb_secret_...
   CORS_ALLOWED_ORIGINS=https://<your-vercel-domain>
   SOCKETIO_CORS_ALLOWED_ORIGINS=https://<your-vercel-domain>
   ```

   Keep the secret key in Render's secret environment only. Do not copy it to
   Vercel, browser code, Git, or chat. Do not set
   `REQUIRE_MUTATION_TOKEN=True` for this Supabase-authenticated API; Supabase
   authentication replaces the legacy demo write-token guard.

   These are the new API keys from **Publishable and secret API keys**. The
   application sends them in the `apikey` header; Supabase user access tokens
   remain JWTs and are sent in the `Authorization: Bearer` header.
6. In Vercel, set the project root to `frontend`, build command to
   `npm run build`, and output directory to `dist`. Set:

   ```env
   VITE_API_BASE_URL=https://<render-service>.onrender.com/api/v1
   VITE_SUPABASE_URL=https://<project-ref>.supabase.co
   VITE_SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
   ```

   The publishable key is public browser configuration; never put the secret
   key here. Redeploy after setting or changing these values.
7. Create a Render Cron Job for daily market history. Use the same backend
   runtime and server-only Supabase variables, set `DISABLE_STARTUP_NETWORK=False`,
   and run:

   ```text
   python -m backend.workers.scheduler_cli --once --job daily_market_snapshot
   ```

   Schedule it after the relevant exchange closes. It upserts one row per
   symbol/trading date. The current small symbol universe stores daily rather
   than intraday bars, but no retention policy is configured yet; monitor table
   growth and provider failures.
8. Verify in the deployed site: sign up with two separate email accounts,
   confirm each account, add a distinct holding under each, sign out/in between
   them, and confirm neither account can read, edit, or delete the other's
   positions. Also test password reset, public market pages, and API health.

Existing SQLite portfolio rows are intentionally not migrated because their
owner has not been identified. The Supabase portfolio currently stores
aggregate positions; realized-gain and tax-lot endpoints are not implemented
for this backend, and sell simulation is disabled until real trade history
exists. These features must not be presented as production-ready. Daily history
collection is implemented, but a validated prediction model consuming those
bars is still a separate, unfinished project gate.

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
For the Render/Vercel path above, the daily Cron Job replaces this continuous
scheduler command.

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
first. These commands apply to local SQLite data, not Supabase portfolio data.
Keep `data/` on a persistent volume for container deployments.

## Graceful Shutdown

Gunicorn uses `GUNICORN_GRACEFUL_TIMEOUT` to allow in-flight requests to finish
before workers exit. Keep scheduled jobs in the separate scheduler process so
API shutdown does not interrupt background work unexpectedly.
