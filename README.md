# Stock Sense Nexus

Local/demo stock intelligence dashboard with a Flask backend, a React/Vite frontend, and SQLite as the active database for now.

## Current Local Stack

- Frontend: React, TypeScript, Tailwind CSS, Vite
- Backend: Python, Flask
- Database: SQLite at `data/nexus.db`
- Future deferred database plan: PostgreSQL migration later

## Run Locally

Start the backend from the project root:

```powershell
python app.py
```

Start the frontend in another terminal:

```powershell
cd frontend
npm run dev
```

Open:

```text
http://localhost:5173/
```

During development, Vite proxies browser requests from `/api` to the Flask
backend at `http://127.0.0.1:5000`. The Flask root is API-only and intentionally
returns a small JSON status document; use the Vite URL for the dashboard.

If `vite.config.ts` changes while Vite is running, restart `npm run dev` once so
the proxy configuration is reloaded.

## SQLite Demo Mode

SQLite is the intentional local/demo database for this phase. The primary database file is:

```text
data/nexus.db
```

Runtime database files are ignored by git, including `data/*.db`, SQLite WAL/SHM files, and generated exports/backups. This keeps personal portfolio data, local prediction history, and demo state out of GitHub.

The database schema is initialized automatically when the backend imports `database.py`. Startup now also validates the required SQLite tables and columns so broken local DB state fails early.

## SQLite Maintenance

Validate the local schema:

```powershell
python scripts/sqlite_maintenance.py check
```

Create a timestamped DB backup:

```powershell
python scripts/sqlite_maintenance.py backup
```

Export all SQLite tables to JSON:

```powershell
python scripts/sqlite_maintenance.py export
```

Backup files go to `data/backups/` and JSON exports go to `data/exports/` by default.

## Demo Security

Local CORS is restricted to Flask and Vite localhost origins by default. For public demos, protect portfolio and feedback mutation routes with:

```env
REQUIRE_MUTATION_TOKEN=True
DEMO_WRITE_TOKEN=replace_with_a_private_demo_token
```

Clients must then send the token as `X-Demo-Token` or `Authorization: Bearer <token>`. Keep this disabled for normal local development unless you are testing public-demo behavior.

## Phase 7 Manual Validation

1. Run `python app.py`.
2. In the frontend, add/edit/delete portfolio data.
3. Stop and restart the backend.
4. Confirm portfolio data persists.
5. Run `python scripts/sqlite_maintenance.py check`.
6. Confirm database files are not staged:

```powershell
git status --short data
```

## Deferred PostgreSQL Plan

PostgreSQL is not active yet. The later migration should introduce SQLAlchemy models, Alembic migrations, a `DATABASE_URL`, and a controlled SQLite-to-PostgreSQL data migration.
