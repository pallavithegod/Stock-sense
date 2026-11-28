# StockSense Deployment Notes

These notes describe the current production-shaped deployment path for the
Flask API. The React frontend is built and hosted separately from the API.

## Which Instructions To Follow

For the selected Supabase + Render + Vercel launch, follow the numbered steps
under **Supabase Authentication And User Portfolios** in order. The WSGI,
Docker, worker, and SQLite backup sections below are reference instructions;
they are not extra steps for that hosting path. Use the GitHub Actions workflow
for daily collection rather than paying for a Render Cron Job or starting the
continuous scheduler.

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

Gunicorn binds `FLASK_HOST` (default `0.0.0.0`) on the first port it finds in
`PORT`, then `FLASK_PORT`, then `5000`. Render injects `PORT` and routes traffic
to it, so do not set `FLASK_PORT` on Render. Do not set `PORT` yourself unless
you also change the service's port in Render.

The worker count is `GUNICORN_WORKERS`, else `WEB_CONCURRENCY` (Render sets it
from the instance size), else half the CPUs with a minimum of two. Each worker
is a separate process with its own caches and rate-limit counters. SQLite
migrations at startup are serialized across workers with a lock file
(`<db>.migrate-lock` next to the database).

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
2. Apply `supabase/migrations/20261125_market_data_and_portfolios.sql`, then
   `supabase/migrations/20261127_portfolio_trade_ledger.sql`, then
   `supabase/migrations/20261128_enforce_fifo_recorded_sells.sql`. The second
   migration creates user-scoped trade/lot/gain tables and atomically backfills
   existing aggregate positions as opening lots at their saved quantity,
   average price, and date. The third makes the sell RPC reject LIFO/HIFO:
   recorded sells are FIFO-only, while LIFO/HIFO remain simulation-only.
   Apply them before deploying the matching backend.
3. In **Authentication → URL Configuration**, set the Vercel URL as the Site
   URL and add the production URL plus
   `https://<your-vercel-domain>/portfolio`
   to Redirect URLs (or use a narrowly scoped `https://<your-vercel-domain>/**`
   pattern). Add approved preview URLs as needed. Keep email confirmation
   enabled for public self-sign-up. Configure a production SMTP sender before
   inviting real users.
4. Create a Render web service from the repository. Set its root directory to
   the repository root, build command to `pip install -e .`, and start command
   to `gunicorn -c gunicorn.conf.py backend.wsgi:app`. Set the health check
   path to `/health/ready`. Gunicorn binds Render's `PORT` automatically.
5. Set these Render API environment variables:

   ```env
   APP_ENV=production
   REQUIRE_AUTH=True
   FLASK_SECRET_KEY=<random secret, at least 32 characters>
   SUPABASE_URL=https://<project-ref>.supabase.co
   SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
   SUPABASE_SECRET_KEY=sb_secret_...
   ALPHA_VANTAGE_API_KEY=<optional market-data API key>
   FINNHUB_API_KEY=<optional market-data API key>
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
7. Use `.github/workflows/daily-market-snapshot.yml` for daily market history.
   Add these repository secrets under **Settings → Secrets and variables →
   Actions**: `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`,
   `SUPABASE_SECRET_KEY`, `FLASK_SECRET_KEY`, and at least one of
   `FINNHUB_API_KEY` or `ALPHA_VANTAGE_API_KEY`. The snapshot workflow passes
   both market-data secrets to the collector. It also accepts GitHub secret
   aliases `FINNHUB_KEY` and `ALPHA_VANTAGE_KEY`. In a local `.env`, these
   aliases are accepted too. Use the current
   `sb_publishable_...` and `sb_secret_...` API keys. `FLASK_SECRET_KEY` must
   be a random value of at least 32 characters. Never put key values in the
   workflow file. The workflow runs at 10:15 UTC (15:45 IST) Monday-Friday and
   can also be started manually with **Run workflow**. It upserts one row per
   symbol/trading date. It also reports the table row count and oldest/newest
   dates. The agreed policy is to retain daily bars indefinitely; the report
   does not delete data. The Actions run fails when:
   - no symbol returns valid bars, or any configured symbol returns none (the
     valid ones are still saved; the failing symbols and error codes are in the
     step log);
   - the retention report finds a configured symbol with no stored bars
     (`missing`), or whose newest bar trails the latest expected session by
     more than 2 weekdays (`stale`). Sessions are judged in IST and a day's bar
     is expected from 16:00 IST. There is no exchange-holiday calendar, so one
     holiday is tolerated by the 2-weekday allowance and longer closures can
     raise a false alarm that clears on the next collection.
   The monitoring steps use `if: !cancelled()`, so they still run, and still
   report, when the collection step fails. Row-count regressions are not
   detected, because no previous count is stored.
   The workflow also evaluates the experimental five-session momentum candidate
   against a zero-return baseline. To seed enough history for evaluation, run
   the following with the Supabase server environment and configured market
   provider. The daily snapshot requests a rolling 1-year window; this
   backfill command defaults to 2 years, and also supports `--period 5y` or
   `--period max`.

   ```powershell
   python -m scripts.backfill_market_history --symbol INFY --symbol TCS --symbol SBIN --symbol RELIANCE --period 2y
   ```

   The forecast remains hidden
   unless at least 400 daily bars are available, the chronological holdout has
   at least 60 samples, the model improves holdout MAE by at least 5%, and
   directional accuracy exceeds 50%. The candidate has no calibrated confidence
   and is not a trained or investment-grade model.
8. Verify in the deployed site: sign up with two separate email accounts,
   confirm each account, add a distinct holding under each, sign out/in between
   them, and confirm neither account can read, edit, or delete the other's
   positions. Verify a recorded buy creates an open lot; simulate FIFO/LIFO/HIFO;
   record a FIFO sell; and confirm remaining quantity, realized gain, and Indian
   financial-year STCG/LTCG classification. Tax payable is not calculated.
   Also test password reset, public market pages, and API health.

The Supabase portfolio now keeps transaction-level buy/sell history and lots.
Position edits/deletes are replaced by recorded trades so the accounting ledger
cannot silently diverge from holdings. The legacy SQLite demo database is
separate; its temporary migration utility is not part of this deployment path.
Realized P&L and 12-month STCG/LTCG classification are informational only; no
tax amount is calculated. The statistical forecast is experimental and remains
hidden until it clears the out-of-sample validation gate above.

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
For the Render/Vercel path above, the GitHub Actions workflow replaces this
continuous scheduler command.

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
