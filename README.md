# StockSense

StockSense is a professional stock market intelligence dashboard for tracking
markets, portfolios, predictions, news, alerts, and research from one
production-shaped application. It combines a polished React trading interface
with a modular Flask API, local persistence, background jobs, and automated
quality checks.

The project is designed to run cleanly on a developer machine while keeping the
same operational shape expected from a deployable web application: API-only
backend, Vite-powered frontend, validated configuration, health checks,
structured logs, database maintenance scripts, and repeatable tests.

## Features

- Live-style market dashboard with indices, opportunity signals, alerts, and
  news feed panels.
- Portfolio desk with holdings, add/edit/delete flows, open lots, sell
  simulation, realized gains, and tax-intelligence views.
- Prediction console with signal, price, target, expected return, confidence,
  allocation, risk, and provenance fields.
- Research and news workspaces for market reports, sentiment, symbol-focused
  coverage, emotional-state analysis, and futures scenarios.
- Stock search with NSE/BSE-aware symbol handling and direct symbol navigation.
- Responsive StockSense terminal UI built for desktop and mobile workflows.
- SQLite-backed local data with schema, backup, cleanup-report, and
  maintenance commands.
- Background worker CLI for scheduled refresh and maintenance jobs.
- CI-friendly frontend and backend test suites, including browser smoke tests.

The Supabase-backed launch path supports authenticated, per-user portfolio
trades, open tax lots, FIFO sells, FIFO/LIFO/HIFO simulation, realized gains,
and Indian financial-year STCG/LTCG classification (without tax calculation).
Daily market snapshots are collected separately. An experimental five-session
statistical forecast is hidden unless it clears a chronological out-of-sample
test against a zero-return baseline; it has no calibrated confidence and is not
an investment-grade model.

## Architecture

```text
frontend/
  React + TypeScript + Vite
  reusable UI components, typed API modules, routing, query/cache layer

backend/
  Flask application factory
  versioned API routes, domain services, providers, workers, health checks

data/
  SQLite databases and audit/runtime files

tests/
  backend unit/integration tests, database hardening tests, frontend unit tests,
  Playwright browser smoke tests
```

Flask serves JSON APIs. Vite serves the browser app during development and
proxies `/api` requests to Flask.

## Tech Stack

- Frontend: React, TypeScript, Vite, Tailwind CSS, Vitest, Playwright.
- Backend: Python, Flask, Flask-SocketIO, Pydantic contracts, SQLite.
- Tooling: Ruff, mypy, pytest, pre-commit, GitHub Actions, Docker, Gunicorn.

## Quick Start

Create and activate the Python environment from the repository root:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

If your environment already has the required build tools and isolated builds
cannot reach PyPI, use:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]" --no-build-isolation
```

Install frontend dependencies:

```powershell
cd frontend
npm install
```

## Run Locally

Start the Flask API from the repository root:

```powershell
.\.venv\Scripts\python.exe app.py
```

Start the React frontend in a second terminal:

```powershell
cd frontend
npm run dev
```

Open:

```text
http://localhost:5173/
```

Vite proxies `/api` to:

```text
http://127.0.0.1:5000
```

Run scheduled jobs manually when needed:

```powershell
.\.venv\Scripts\python.exe -m backend.workers.scheduler_cli --once
```

Collect daily market history after the market closes:

```powershell
.\.venv\Scripts\python.exe -m backend.workers.scheduler_cli --once --job daily_market_snapshot
```

For production, use `.github/workflows/daily-market-snapshot.yml` to run the
one-shot command after the relevant exchange closes. The job requests the most
recent five daily bars for each configured market-universe symbol and upserts
them by symbol/date, so retries do not create duplicate days.

## Configuration

Copy `.env.example` to `.env` and adjust local values:

```env
APP_ENV=development
FLASK_SECRET_KEY=replace_with_a_long_random_secret
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
OPEN_BROWSER=False
DISABLE_STARTUP_NETWORK=True

STOCKSENSE_DB_PATH=data/stocksense.db
STOCKSENSE_MARKET_DB_PATH=data/market_intelligence.db
STOCKSENSE_ADAPTIVE_DB_PATH=data/adaptive_thresholds.db
STOCKSENSE_AUDIT_LOG_PATH=data/prediction_audit.jsonl
```

External provider keys are optional for local development. Add them only when
you want live provider-backed market, news, or model integrations:

```env
ALPHA_VANTAGE_API_KEY=
TWELVE_DATA_API_KEY=
GNEWS_API_KEY=
FINNHUB_API_KEY=
FMP_API_KEY=
DATA_GOV_API_KEY=
HUGGINGFACEHUB_API_TOKEN=
```

Daily market collection tries yfinance first, including bare-symbol, NSE
(`.NS`), and BSE (`.BO`) history lookups, then uses Finnhub and Alpha Vantage
as fallbacks. Set their `*_API_KEY` variables locally and as GitHub Actions
repository secrets; local `.env` also accepts `FINNHUB_KEY` and
`ALPHA_VANTAGE_KEY`.

The API news service uses `GNEWS_API_KEY` for live market and symbol articles.
It serves cached articles when available, or an explicit empty/unavailable
state when the key is missing or GNews cannot be reached.

For Supabase-backed portfolio authentication and daily market snapshots, apply
`supabase/migrations/20261125_market_data_and_portfolios.sql` in the Supabase SQL
Editor. Configure these values on the API and worker servers only:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
SUPABASE_SECRET_KEY=sb_secret_...
REQUIRE_AUTH=True
```

Set the public Supabase URL and publishable key in the frontend as
`VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY`. Never put
`SUPABASE_SECRET_KEY` in Vercel or any frontend environment variables. The
worker stores one upserted OHLCV row per symbol and trading date. Set
`DISABLE_STARTUP_NETWORK=False` in the worker environment so its market-data
provider is enabled; `True` disables provider requests, not just startup calls.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the Supabase, Render, and
Vercel launch sequence, including required environment variables and account
isolation checks.

For an anonymous demo that does not use Supabase Auth, write endpoints can use
the legacy demo token:

```env
REQUIRE_MUTATION_TOKEN=True
DEMO_WRITE_TOKEN=replace_with_a_private_demo_token
```

Clients can provide the token with either `X-Demo-Token` or
`Authorization: Bearer <token>`.
Do not enable this demo-token mode alongside the Supabase-authenticated launch.

## Validation

Backend checks:

```powershell
.\.venv\Scripts\python.exe -m compileall -q app.py backend scripts utils
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest tests\integration\db -q
```

Frontend checks:

```powershell
cd frontend
npm run lint
npm run build
npm run test
npm run test:e2e
```

Quality tooling:

```powershell
.\.venv\Scripts\python.exe -m ruff check app.py backend tests scripts
.\.venv\Scripts\python.exe -m mypy app.py backend scripts
.\.venv\Scripts\pre-commit.exe run --all-files
```

## Database Maintenance

Check the local schema:

```powershell
.\.venv\Scripts\python.exe scripts\sqlite_maintenance.py check
```

Create a backup:

```powershell
.\.venv\Scripts\python.exe scripts\sqlite_maintenance.py backup
```

Generate a cleanup report:

```powershell
.\.venv\Scripts\python.exe scripts\sqlite_maintenance.py cleanup-report
```

Cleanup commands are confirmation-gated and produce a backup path before
modifying the active database.

## Demo Data

Seed deterministic local data:

```powershell
.\.venv\Scripts\python.exe scripts\seed_demo_data.py --db data\stocksense.db
```

Playwright browser checks can also capture workflow screenshots under:

```text
.dev-runtime/screenshots/
```

## Production Entry Points

Gunicorn:

```powershell
gunicorn -c gunicorn.conf.py backend.wsgi:app
```

Docker:

```powershell
docker build -t stocksense .
docker run --env-file .env -p 5000:5000 stocksense
```

Operational details for Docker, health checks, worker execution, backups,
logging, CSP, and graceful shutdown are documented in `docs/DEPLOYMENT.md`.

Health endpoints:

```text
/health/live
/health/ready
```

## Project Layout

```text
backend/
  app/             application factory, config, extensions, contracts
  domain/          market, portfolio, prediction, news, and system services
  routes/          HTTP route modules
  workers/         scheduler and background job runtime

frontend/
  src/api/         typed endpoint modules
  src/components/  reusable UI primitives
  src/layouts/     StockSense shell and navigation
  src/pages/       dashboard, stocks, portfolio, predictions, news, research
  src/query/       lightweight query/cache layer
  tests/           unit and browser workflow tests

scripts/
  database maintenance and deterministic data seeding

tests/
  backend smoke, contract, security, worker, and database checks
```

## Dependency Files

- `pyproject.toml` defines Python runtime, development, and optional ML
  dependency groups.
- `requirements.txt`, `requirements-dev.txt`, and `requirements-ml.txt` are
  compatibility installers for those groups.
- `requirements-lock.txt` records the current Python environment.
- `frontend/package-lock.json` locks the frontend dependency tree.
