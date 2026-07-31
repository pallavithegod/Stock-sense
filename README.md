# StockSense Nexus

StockSense Nexus is a local/demo stock intelligence dashboard built as a
modular monolith: React/Vite in `frontend/`, Flask in `backend/`, and SQLite as
the active database. The current migration goal is a production-shaped resume
project, not a microservice rewrite.

## Architecture

```text
frontend/ React + TypeScript + Vite
    -> /api JSON over the Vite dev proxy
backend/ Flask app factory + domain services + worker CLI
    -> SQLite database files under data/
tests/ backend, contract, integration, and worker coverage
```

SQLite remains intentional for the local/resume deployment. PostgreSQL and
Redis stay deferred until the app needs multiple public web/worker processes or
managed concurrent writes.

Legacy root/static dashboard assets and retired backend bridge modules have
been removed. The remaining compatibility API aliases stay temporarily because
the React frontend still uses some pre-v1 endpoints for portfolio lots, sell
simulation, research extras, and dashboard fallbacks.

## Fresh Setup

Create and activate a virtual environment from the repository root:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

If you already have the build tools installed in the venv and the environment
blocks PyPI during isolated builds, use the restricted-network fallback:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]" --no-build-isolation
```

Install optional heavyweight ML and legacy intelligence dependencies only when
working on those modules:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[ml]"
```

Install frontend dependencies:

```powershell
cd frontend
npm install
```

## Run Locally

Start Flask from the repository root:

```powershell
.\.venv\Scripts\python.exe app.py
```

Start Vite in a second terminal:

```powershell
cd frontend
npm run dev
```

Open `http://localhost:5173/`. Vite proxies `/api` requests to Flask at
`http://127.0.0.1:5000`. The Flask root is intentionally API-only.

Run the standalone scheduler only when testing background jobs:

```powershell
.\.venv\Scripts\python.exe -m backend.workers.scheduler_cli --once
```

## Production Packaging

The API production entry point is:

```powershell
gunicorn -c gunicorn.conf.py backend.wsgi:app
```

The backend Docker image runs the API as a non-root user, exposes
`/health/live`, and persists `/app/data`, `/app/logs`, `/app/cache`, and
`/app/models` as volumes. See `docs/DEPLOYMENT.md` for Docker, health checks,
worker process, backup/restore, logging, CSP, and graceful shutdown details.

## Environment

Useful local variables:

```env
APP_ENV=development
FLASK_SECRET_KEY=change-me-local-dev-secret
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
DISABLE_STARTUP_NETWORK=True
OPEN_BROWSER=False
STOCKSENSE_DB_PATH=data/nexus.db
STOCKSENSE_MARKET_DB_PATH=data/market_intelligence.db
STOCKSENSE_ADAPTIVE_DB_PATH=data/adaptive_thresholds.db
STOCKSENSE_AUDIT_LOG_PATH=data/prediction_audit.jsonl
```

For public demos, protect write routes:

```env
REQUIRE_MUTATION_TOKEN=True
DEMO_WRITE_TOKEN=replace_with_a_private_demo_token
```

Clients must then send `X-Demo-Token` or `Authorization: Bearer <token>`.

## Validation

Backend:

```powershell
.\.venv\Scripts\python.exe -m compileall -q app.py backend scripts
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest tests\integration\db -q
```

Frontend:

```powershell
cd frontend
npm run lint
npm run build
npm run test
npm run test:e2e
```

Tooling after installing development dependencies:

```powershell
.\.venv\Scripts\python.exe -m ruff check app.py backend tests scripts
.\.venv\Scripts\python.exe -m mypy app.py backend scripts
.\.venv\Scripts\pre-commit.exe run --all-files
```

The first type-check baseline is intentionally practical and excludes legacy
modules. Tighten it gradually as the migration continues.

## SQLite Maintenance

Validate or migrate the local schema:

```powershell
.\.venv\Scripts\python.exe scripts\sqlite_maintenance.py check
```

Create a backup:

```powershell
.\.venv\Scripts\python.exe scripts\sqlite_maintenance.py backup
```

Generate a dry-run cleanup report:

```powershell
.\.venv\Scripts\python.exe scripts\sqlite_maintenance.py cleanup-report
```

No cleanup command modifies `data/nexus.db` without an explicit confirmation
token and a backup path.

## Demo Data And Screenshots

Seed deterministic demo data:

```powershell
.\.venv\Scripts\python.exe scripts\seed_demo_data.py --db data\nexus.db
```

Phase 9 Playwright smoke tests generate workflow screenshots under
`.dev-runtime/screenshots/`.

## Dependency Files

- `pyproject.toml` is the source of Python runtime, development, and optional
  ML dependency metadata.
- `requirements.txt`, `requirements-dev.txt`, and `requirements-ml.txt` are
  compatibility entry points that install those pyproject groups.
- `requirements-lock.txt` captures the current virtualenv for reproducibility.
- `frontend/package-lock.json` locks the frontend dependency tree.

## Current Limitations

- SQLite is the active database; PostgreSQL is deferred.
- Redis is not required for the current single-process local/resume target.
- Some heavyweight ML and legacy intelligence modules remain optional.
- Some compatibility API aliases remain until the frontend can call `/api/v1`
  for every workflow.
- CI includes a non-blocking type-check and dependency-audit baseline while the
  migration is still retiring legacy surfaces.
