# StockSense Frontend

React/Vite frontend for the StockSense dashboard. The Flask backend remains the
API server; Vite serves the browser app and proxies `/api` to Flask in local
development.

## Setup

```powershell
cd frontend
npm install
```

## Run

Start Flask from the repository root:

```powershell
.\.venv\Scripts\python.exe app.py
```

Start the frontend:

```powershell
npm run dev
```

Open `http://localhost:5173/`. The Flask root at port 5000 is API-only.

## Scripts

```powershell
npm run lint
npm run build
npm run test
npm run test:e2e
```

- `npm run test` uses Vitest and React Testing Library for fast unit/component
  tests.
- `npm run test:e2e` uses Playwright for browser workflow smoke tests and
  screenshots.

## Structure

```text
src/
  api/          typed endpoint modules
  app/          application-level wiring when needed
  components/   reusable UI primitives
  layouts/      app shell and navigation
  pages/        feature pages and presentation slices
  query/        lightweight query/cache layer
  router/       URL routing helpers
  schemas/      runtime response validation
  utils/        formatters and adapters
tests/
  unit/         Vitest/RTL tests
  e2e/          Playwright tests with deterministic mocked APIs
```

Keep Playwright for true browser checks only; use Vitest/RTL for fast component
and adapter coverage.
