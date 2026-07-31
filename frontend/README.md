# StockSense Frontend

The StockSense frontend is a React and Vite trading workspace for market
dashboards, stock search, portfolios, predictions, news, and research. It uses
typed API modules, a lightweight query layer, accessible form/table patterns,
and browser smoke tests for core workflows.

## Setup

```powershell
cd frontend
npm install
```

## Development

Start the Flask API from the repository root:

```powershell
.\.venv\Scripts\python.exe app.py
```

Start Vite from `frontend/`:

```powershell
npm run dev
```

Open:

```text
http://localhost:5173/
```

The Vite dev server proxies `/api` requests to the Flask API on
`http://127.0.0.1:5000`.

## Scripts

```powershell
npm run lint
npm run build
npm run test
npm run test:e2e
```

- `npm run lint` checks TypeScript and React code quality.
- `npm run build` creates the production frontend bundle.
- `npm run test` runs Vitest and React Testing Library.
- `npm run test:e2e` runs Playwright browser smoke tests.

## Structure

```text
src/
  api/          endpoint modules and HTTP access
  components/   shared UI primitives
  layouts/      StockSense application shell
  pages/        feature pages and presentation sections
  query/        request cache, retries, cancellation, invalidation
  router/       URL routing helpers
  schemas/      runtime response validation
  utils/        formatters and data adapters

tests/
  unit/         component and utility tests
  e2e/          Playwright workflow checks with mocked APIs
```

Use Vitest for fast component and adapter coverage. Use Playwright for browser
behavior that depends on layout, routing, screenshots, or real user flows.
