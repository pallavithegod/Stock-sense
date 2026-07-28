# StockSense Project Audit

Audit date: 2026-07-25

Scope: repository at `New3_Working_V5_Copy`, including the Flask backend, legacy root UI, React/Vite frontend, data/runtime folders, scripts, and tests.

## Executive Summary

StockSense currently works as a local/demo Flask + React + SQLite application, but it is not production-ready. The project contains a newer modular backend and frontend layered on top of a large legacy monolith. The biggest structural issue is that many extracted modules still depend on `app.py` globals, so the codebase looks modular without actually being decoupled.

Verified baseline:

- Frontend build passes: `npm run build`.
- Backend tests pass in the project virtualenv: `.venv\Scripts\python.exe -m pytest -q` -> 27 passed.
- Frontend lint fails: `frontend/src/hooks/useAsync.ts` violates `react-hooks/set-state-in-effect`.
- System Python cannot run tests because `pytest` is not installed outside the virtualenv.

## Critical Findings

1. Real secrets exist in `.env`.
   The local `.env` contains live-looking API tokens for Alpha Vantage, News API, Finnhub, Hugging Face, and a Flask secret. `.gitignore` excludes `.env`, and `git ls-files` does not show it tracked, but the working copy itself is unsafe to zip, share, or back up casually. Rotate those keys if this folder has been shared.

2. Unsafe `eval` exists in the learning pipeline.
   `continuous_learning.py` parses stored `models_used` with `eval(models)`. Since that field comes from database content, this is code execution risk. Use `json.loads` with schema fallback instead.

3. Production readiness is blocked by architecture.
   `app.py` is about 5,220 lines, `app.js` about 9,547 lines, `style.css` about 4,020 lines, and `intelligence_core.py` about 2,760 lines. The backend route modules call `configure_*_runtime(globals())`, which copies legacy globals into modules. That makes testing, refactoring, concurrency safety, and production deployment fragile.

4. Synthetic/fallback prediction behavior can mislead users.
   The legacy AI layer can generate synthetic OHLCV data when market data fails. Some newer endpoints filter `is_synthetic`, but fallback values still appear in dashboard/system payloads. A stock/crypto prediction product must clearly separate live, delayed, cached, fallback, and synthetic data.

5. Financial claims are overconfident.
   `/api/system/status` reports static-looking values such as `"uptime": "99.9%"` and fallback prediction accuracy `"87.5%"`. These are not production metrics and should not be presented as real reliability/accuracy.

## Architecture Findings

The repo has three overlapping generations:

- Legacy root app: `app.py`, `app.js`, `index.html`, `style.css`, `chart.js`, `nexus-ai.*`, `research_ui.*`.
- Partially extracted backend: `backend/routes/*`, `backend/services/*`, `backend/legacy/quantum_ai.py`.
- New frontend: `frontend/src/*` with Vite, React, TypeScript, and Tailwind.

This creates duplicated APIs and UI logic:

- Root legacy UI files still exist and are served only when `ENABLE_LEGACY_UI=True`.
- `dashboard/nexus-ai.*` duplicates `nexus-ai.*` with different hashes.
- `research_ui.css` and `static/research/research_ui.css` are identical, while the JS versions differ.
- `database.py` and `app.py` both contain prediction table logic.
- `backend/routes/market_routes.py` includes route handlers plus large analysis helpers and unreachable/nested legacy fragments.

Recommended target architecture:

- `app.py`: application factory, config, extension setup, blueprint registration only.
- `backend/routes`: request/response only.
- `backend/services`: business logic only, injected dependencies, no Flask globals.
- `backend/ml`: prediction engines, model evaluation, calibration, feature generation.
- `backend/data`: market data providers and source-quality metadata.
- `frontend`: only active UI.
- `legacy/`: quarantined legacy code that is not imported during normal startup.

## Directory Review

`.agents`, `.vscode`

- Local tooling/editor state. Should stay ignored unless intentional project settings are needed.

`backend`

- Good direction: routes and services have started to separate concerns.
- Bad pattern: runtime globals are copied into modules via `configure_*_runtime(globals())`.
- Route modules still contain business logic and broad exception handling.
- `backend/legacy/quantum_ai.py` is active legacy code, not just archived code.

`cache`

- Runtime cache. Must stay untracked. It contains yfinance cache artifacts.

`dashboard`

- Legacy dashboard shell/assets. Different from root `nexus-ai.*`, so there are multiple UI truths.

`data`

- Contains large local SQLite files, WAL/SHM files, JSON cache, and audit files.
- `data/nexus.db` is about 127 MB; `data/nexus_demo.db` is about 124 MB.
- Good: `.gitignore` excludes runtime DB files.
- Production concern: SQLite is acceptable for local demo, not for multi-user production prediction/portfolio workflows.

`frontend`

- Healthier than the legacy UI. TypeScript build passes.
- Lint currently fails in `src/hooks/useAsync.ts`.
- API client has timeouts and JSON handling, but no auth token wiring for protected mutation mode.

`logs`

- `logs/nexus_ai.log` is about 158 MB. Logging lacks rotation. This will grow indefinitely.

`models`

- Runtime/model artifact folder. Should stay ignored. Needs a model registry/versioning policy before production.

`scripts`

- Many encoding cleanup scripts suggest historical corruption. Keep only reusable maintenance scripts; move one-off cleanup scripts to `scripts/archive` or remove after a clean git tag.

`static`

- Contains legacy research UI assets. Some duplicate root files.

`tests`

- Useful smoke/security coverage exists.
- Missing: portfolio lot accounting edge cases, prediction calibration, synthetic/fallback filtering, route contract coverage, database migration tests, frontend tests.

`utils`

- Small helpers for encoding, fuzzy matching, stock loading. Reasonable, but should remain dependency-light.

## File-Level Highlights

`app.py`

- Too large and owns too many responsibilities: config, app setup, routes, background loops, cache, data fetching, prediction logic, portfolio intelligence, dashboard payloads, and UI serving.
- Imports and globals are repeated.
- Many broad `except Exception` blocks hide failures.
- Starts background services only in `__main__`, which is good for tests, but production worker behavior needs a clear model.
- Uses a plain `FileHandler` for logs without rotation.

`backend/services/security.py`

- Positive: CORS defaults are restricted, production placeholder secrets are rejected, mutation guard exists, request-size guard exists, rate limiting exists.
- Gaps: no real user authentication/authorization, in-memory rate limiting only, no CSRF strategy for browser mutations, no HSTS, no central audit log for protected mutations.

`database.py`

- Positive: parameterized SQL is mostly used.
- Gaps: global `_initialized` can skip initialization for a second DB path in the same process; schema migration is manual; SQLite has no production migration framework; some legacy prediction schema helpers conflict with current schema intent.

`continuous_learning.py`

- Critical: replace `eval(models)` with `json.loads`.
- Learning is based on very thin realized outcome data and lacks train/test separation, backtesting protocol, leakage controls, and calibration.

`backend/legacy/quantum_ai.py`

- Large active legacy module.
- Generates synthetic data fallback and sets `df.attrs["is_synthetic"] = True`.
- Should be quarantined behind an explicit provider interface and forbidden from silently feeding trading recommendations.

`backend/routes/market_routes.py`

- Too large for a route module.
- Contains search, stock details, analysis, charts, dynamic lookup, and legacy fragments.
- Several failures are silently swallowed, making debugging difficult.

`backend/routes/predictions.py`

- Contains route handlers plus prediction synthesis logic.
- Good: some endpoints reject synthetic data.
- Concern: long-horizon predictions are mostly heuristic transformations of current signal, volatility, and momentum.

`backend/routes/portfolio.py`

- Good validation layer is used for mutations.
- Lacks authentication by default unless demo mutation token is enabled.
- Financial/tax calculations need dedicated tests before being trusted.

`backend/services/prediction_presenter.py`

- Good pure presenter module.
- Concern: fills missing fields with defaults like `UNKNOWN`, `WATCH`, `LOW`, and `DEGRADED`; UI must distinguish missing data from real model output.

`backend/services/startup_checks.py`

- Good lightweight diagnostics.
- Concern: reports only whether environment keys exist, not whether services are usable or rate-limited.

`secure_api_config.py`

- Claims "Zero Hardcoded Credentials" but can return `api_key` inside service config dictionaries. Make sure no endpoint serializes that object.
- References missing `security_utils`, so it falls back to basic environment lookup.

`requirements.txt`

- Dependencies are mostly unpinned and duplicated (`torch`, `transformers` appear twice).
- No lockfile for Python production reproducibility.

`frontend/src/api/client.ts`

- Good timeout and error handling.
- Does not inject demo write token/auth headers when `REQUIRE_MUTATION_TOKEN=True`.

`frontend/src/hooks/useAsync.ts`

- Lint error from synchronous `setState` inside effect.

`README.md`

- Useful local setup instructions.
- Should add production disclaimer, secret rotation guidance, and the fact that this is not investment advice.

## Security Checklist

Immediate:

- Rotate all API tokens found in `.env`.
- Keep `.env` local only; never send this repo folder as a zip with `.env`, `data`, `logs`, `cache`, or `models`.
- Replace `eval` in `continuous_learning.py`.
- Add log rotation.
- Ensure no endpoint returns API keys from `secure_api_config.py`.

Before public demo:

- Set `REQUIRE_MUTATION_TOKEN=True`.
- Use a strong `DEMO_WRITE_TOKEN`.
- Use a strong `FLASK_SECRET_KEY`.
- Set `APP_ENV=production`.
- Restrict CORS to the real frontend origin.
- Disable legacy UI unless deliberately needed.
- Put the app behind TLS and a real reverse proxy.

Before production:

- Add real authentication and authorization.
- Replace in-memory rate limiting with Redis or gateway-level rate limiting.
- Add audit logging for portfolio/prediction mutation events.
- Add dependency vulnerability scanning.
- Add dependency pinning/lockfiles.

## ML and Prediction Risks

Current prediction logic is mostly heuristic and technical-indicator driven. It is not yet a credible production ML forecasting system.

Main gaps:

- No reproducible training pipeline.
- No feature store or feature versioning.
- No train/validation/test split policy.
- No walk-forward backtesting.
- No leakage checks.
- No confidence calibration.
- No benchmark comparison against naive baselines.
- No model registry/versioning.
- No monitoring for prediction drift versus realized outcomes.
- No clear crypto-specific data provider or 24/7 market calendar handling.
- No risk disclaimer or suitability controls.

Minimum credible path:

1. Define prediction horizons and target labels precisely.
2. Store every prediction with model version, feature timestamp, data source, and market close timestamp.
3. Backtest with walk-forward validation.
4. Compare against naive baselines.
5. Calibrate confidence using historical outcomes.
6. Mark all outputs as educational, not financial advice.

## Production Readiness Gaps

- No WSGI production config documented beyond listing `gunicorn`.
- No Dockerfile or deployment manifests.
- No centralized config schema.
- No Alembic/SQLAlchemy migration workflow.
- No log rotation or structured logging.
- No background worker management.
- No health/readiness split.
- No observability beyond local logs/status JSON.
- No CI workflow.
- No frontend test suite.
- No load testing.
- No service-level timeout/retry policy per market data provider.

## Recommended Cleanup Roadmap

Phase 1: Security and trust

- Rotate keys and clean local secret handling.
- Replace `eval`.
- Add log rotation.
- Add a hard `data_quality` field to every market/prediction response.
- Remove fake production metrics from status endpoints.

Phase 2: Stabilize current app

- Fix frontend lint.
- Pin Python dependencies.
- Add CI for backend tests, frontend lint, and frontend build.
- Add route contract tests for every active `/api/*` endpoint.
- Add portfolio ledger tests.

Phase 3: Decompose monolith

- Convert `app.py` into an app factory.
- Stop using `configure_*_runtime(globals())`.
- Move market data, prediction, portfolio, and dashboard logic behind explicit services.
- Quarantine legacy UI/assets under `legacy/`.

Phase 4: ML credibility

- Build a reproducible prediction evaluation pipeline.
- Add walk-forward backtests.
- Store model versions and feature snapshots.
- Calibrate confidence and remove unverified accuracy claims.

Phase 5: Production

- Move from SQLite to PostgreSQL for multi-user production.
- Add auth, authorization, audit logs, and external rate limiting.
- Add deployment automation and observability.

