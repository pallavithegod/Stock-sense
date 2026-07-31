import { mkdirSync } from 'node:fs'
import { expect, test } from '@playwright/test'
import type { Page, Route } from '@playwright/test'

type MockOptions = {
  failDashboardAfterFirst?: boolean
}

const stockRows = [
  { symbol: 'INFY.NS', display: 'INFY', name: 'Infosys Limited', exchange: 'NSE', current_price: 1500, change_percent: 1.2, sector: 'IT' },
  { symbol: 'TATAMOTORS.NS', display: 'TATAMOTORS', name: 'Tata Motors Limited', exchange: 'NSE', current_price: 920, change_percent: -0.4, sector: 'Auto' },
  { symbol: 'KOTAKBANK.NS', display: 'KOTAKBANK', name: 'Kotak Mahindra Bank', exchange: 'NSE', current_price: 1720, change_percent: 0.6, sector: 'Banking' },
]

test('dashboard loads and preserves stale data when refresh fails', async ({ page }) => {
  await mockApis(page, { failDashboardAfterFirst: true })

  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Market Dashboard' })).toBeVisible()
  const indicesTable = page.getByRole('table', { name: 'Market index prices and percentage change' })
  await expect(indicesTable.getByRole('cell', { name: 'NIFTY 50' })).toBeVisible()
  await expect(page.getByText('INFY')).toBeVisible()

  await page.getByRole('button', { name: 'Refresh dashboard' }).click()
  await expect(page.getByText('Showing the last successful snapshot.')).toBeVisible()
  await expect(indicesTable.getByRole('cell', { name: 'NIFTY 50' })).toBeVisible()
})

test('search finds exact symbols and NSE variants', async ({ page }) => {
  await mockApis(page)

  await page.goto('/stocks')
  const search = page.getByLabel('Search stocks')
  await search.fill('INFY')
  await expect(page.getByRole('button', { name: /INFY/ })).toBeVisible()

  await search.fill('TATA')
  await expect(page.getByRole('button', { name: /TATAMOTORS/ })).toBeVisible()

  await search.fill('KOTAK')
  await expect(page.getByRole('button', { name: /KOTAKBANK/ })).toBeVisible()
})

test('prediction rows render model fields and unavailable states', async ({ page }) => {
  await mockApis(page)

  await page.goto('/predictions')
  await expect(page.getByRole('heading', { name: 'Prediction Console' })).toBeVisible()
  await expect(page.getByRole('cell', { name: 'INFY' })).toBeVisible()
  await expect(page.getByRole('table').getByText('ml model')).toBeVisible()
  await expect(page.getByText('fixture_provider')).toBeVisible()
})

test('portfolio add, sell simulation, and delete confirmation use mocked APIs', async ({ page }) => {
  await mockApis(page)
  page.on('dialog', (dialog) => dialog.accept())

  await page.goto('/portfolio')
  await page.getByLabel('Symbol', { exact: true }).fill('TEST')
  await page.getByLabel('Quantity', { exact: true }).fill('2')
  await page.getByLabel('Average price').fill('100')
  await page.getByRole('button', { name: 'Add' }).click()

  await expect(page.getByText('TEST added.')).toBeVisible()
  const holdingsTable = page.locator('table', { hasText: 'Open portfolio positions' })
  await expect(holdingsTable.getByRole('cell', { name: 'TEST', exact: true })).toBeVisible()
  await expect(holdingsTable.getByRole('cell', { name: 'INFY', exact: true })).toBeVisible()

  await page.getByRole('button', { name: 'Edit TEST' }).focus()
  await page.keyboard.press('Enter')
  await page.getByLabel('Average price').fill('110')
  await page.getByRole('button', { name: 'Update' }).click()
  await expect(page.getByText('TEST updated.')).toBeVisible()

  await page.getByLabel('Sell symbol').fill('TEST')
  await page.getByLabel('Sell quantity').fill('1')
  await page.getByLabel('Sell price').fill('120')
  await page.getByRole('button', { name: 'Simulate FIFO/LIFO/HIFO' }).click()
  await expect(page.getByText('Recommended')).toBeVisible()
  await expect(page.getByRole('cell', { name: 'FIFO' })).toBeVisible()

  await page.getByRole('button', { name: 'Delete TEST' }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByText('TEST deleted.')).toBeVisible()
})

test('primary pages expose labels, captions, and responsive navigation', async ({ page, isMobile }) => {
  await mockApis(page)

  await page.goto('/portfolio')
  await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible()
  await expect(page.getByLabel('Symbol', { exact: true })).toBeVisible()
  await expect(page.locator('caption', { hasText: 'Open portfolio positions' })).toHaveCount(1)
  if (isMobile) {
    await expect(page.getByRole('navigation', { name: 'Primary' })).toBeVisible()
  }

  await page.goto('/news')
  await expect(page.getByLabel('Stock symbol')).toBeVisible()

  await page.goto('/research')
  await expect(page.getByLabel('Stock symbol')).toBeVisible()
})

test('captures main workflow screenshots', async ({ page }, testInfo) => {
  await mockApis(page)
  mkdirSync('../.dev-runtime/screenshots', { recursive: true })

  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Market Dashboard' })).toBeVisible()
  await page.screenshot({
    fullPage: true,
    path: `../.dev-runtime/screenshots/phase9-dashboard-${testInfo.project.name}.png`,
  })
})

async function mockApis(page: Page, options: MockOptions = {}) {
  const positions = [
    {
      symbol: 'INFY',
      quantity: 4,
      open_qty: 4,
      avg_price: 1400,
      current_price: 1500,
      current_value: 6000,
      pnl: 400,
      action: 'WATCH',
      confidence: 0.62,
    },
  ]
  let dashboardCalls = 0

  await page.route('**/*', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    if (!url.pathname.startsWith('/api/')) {
      await route.continue()
      return
    }
    const path = url.pathname.replace(/^\/api/, '')

    if (path.startsWith('/dashboard-data')) {
      dashboardCalls += 1
      if (options.failDashboardAfterFirst && dashboardCalls > 1) {
        await json(route, { error: 'fixture outage' }, 503)
        return
      }
      await json(route, dashboardPayload())
      return
    }

    if (path === '/stocks') {
      await json(route, { stocks: stockRows })
      return
    }

    if (path.startsWith('/search')) {
      await json(route, { results: stockRows })
      return
    }

    if (path.startsWith('/predictions/live/')) {
      await json(route, {
        data: {
          symbol: decodeURIComponent(path.split('/').pop() ?? 'INFY'),
          current_price: 1500,
          predictions: { '1m': { target_price: 1550, return_percent: 3.33 } },
          market_conditions: { momentum: 'positive', volatility_level: 'low' },
        },
      })
      return
    }

    if (path === '/predictions/intelligence') {
      await json(route, {
        rows: [
          {
            symbol: 'INFY',
            signal: 'BUY',
            current_price: 1500,
            target_price: 1650,
            confidence: 0.72,
            risk: 'LOW',
            source_type: 'ml_model',
            provider: 'fixture_provider',
            model_version: 'fixture-v1',
          },
        ],
      })
      return
    }

    if (path === '/predictions') {
      await json(route, { rows: [] })
      return
    }

    if (path === '/portfolio/state') {
      await json(route, portfolioState(positions))
      return
    }

    if (path === '/portfolio' && request.method() === 'GET') {
      await json(route, positions)
      return
    }

    if (path === '/portfolio' && request.method() === 'POST') {
      const body = request.postDataJSON() as { symbol?: string; quantity?: number; avg_price?: number }
      positions.push({
        symbol: String(body.symbol ?? 'TEST'),
        quantity: Number(body.quantity ?? 1),
        open_qty: Number(body.quantity ?? 1),
        avg_price: Number(body.avg_price ?? 100),
        current_price: 120,
        current_value: Number(body.quantity ?? 1) * 120,
        pnl: 20,
        action: 'WATCH',
        confidence: 0.5,
      })
      await json(route, { status: 'success', data: { exchange_symbol: body.symbol } })
      return
    }

    if (path.startsWith('/portfolio/') && request.method() === 'PUT') {
      const symbol = decodeURIComponent(path.split('/').pop() ?? '')
      const body = request.postDataJSON() as { quantity?: number; avg_price?: number }
      const position = positions.find((item) => item.symbol === symbol)
      if (position) {
        position.quantity = Number(body.quantity ?? position.quantity)
        position.open_qty = Number(body.quantity ?? position.open_qty)
        position.avg_price = Number(body.avg_price ?? position.avg_price)
        position.current_value = Number(position.open_qty ?? 0) * Number(position.current_price ?? 0)
        position.pnl = Number(position.current_value ?? 0) - Number(position.open_qty ?? 0) * Number(position.avg_price ?? 0)
      }
      await json(route, { status: 'success' })
      return
    }

    if (path.startsWith('/portfolio/') && request.method() === 'DELETE') {
      const symbol = decodeURIComponent(path.split('/').pop() ?? '')
      const index = positions.findIndex((position) => position.symbol === symbol)
      if (index >= 0) positions.splice(index, 1)
      await json(route, { status: 'success' })
      return
    }

    if (path === '/portfolio/lots') {
      await json(route, { data: [{ id: 1, symbol: 'INFY', open_qty: 4, buy_price: 1400, buy_date: '2026-01-01' }] })
      return
    }

    if (path === '/portfolio/realized-gains') {
      await json(route, { data: [] })
      return
    }

    if (path === '/portfolio/tax-summary') {
      await json(route, { status: 'success', data: { fy: '2026-27', transactions: 0, realized_total: 0 } })
      return
    }

    if (path === '/portfolio/lot-insights') {
      await json(route, { status: 'success', data: { fy_summary: { holding_period: 'long term' } } })
      return
    }

    if (path === '/portfolio/intelligence-suite') {
      await json(route, {
        status: 'success',
        data: {
          forecast: { current_value: 6000 },
          survival: { score: 91 },
          governance: { status: 'OK', alerts: [] },
        },
      })
      return
    }

    if (path === '/portfolio/sell/simulate') {
      await json(route, {
        status: 'success',
        data: {
          recommended_method: 'FIFO',
          sell_quantity: 1,
          sell_price: 120,
          scenarios: [{ method: 'FIFO', realized_gain: 20, realized_stcg: 20, realized_ltcg: 0, tax_impact_proxy: 3, matched_lots: [{}] }],
        },
      })
      return
    }

    if (path === '/news/market') {
      await json(route, { label: 'positive', articles: [{ title: 'Market breadth improves', source: 'Fixture' }] })
      return
    }

    if (path === '/alerts') {
      await json(route, { triggered_today: 0, active_alerts: 1, alerts: [{ symbol: 'INFY', condition: 'above', target_value: 1500, current_value: 1510 }] })
      return
    }

    if (path.startsWith('/news/symbol/')) {
      await json(route, { articles: [{ title: 'Symbol coverage', source: 'Fixture' }] })
      return
    }

    if (path === '/research') {
      await json(route, {
        researchreports: [{ title: 'Fixture research', confidence: 0.8, findings: ['Model stable'] }],
        aiinsights: [{ insight: 'Fixture insight', probability: 0.7, model_confidence: 0.8 }],
        model_performance: { directional_accuracy: 0.6 },
        live_stats: { total_symbols_analyzed: 3, total_predictions: 5, avg_confidence: 0.7, bullish_ratio: 0.66 },
      })
      return
    }

    if (path.startsWith('/emotional-state/')) {
      await json(route, { emotional_state: { fear_index: 40, greed_index: 60 } })
      return
    }

    if (path.startsWith('/futures-analysis/')) {
      await json(route, { futures: { worlds: [{ name: 'Base', probability: 0.6, expected_return: 4, target: 1600 }] } })
      return
    }

    await json(route, { error: `Unhandled fixture route ${path}` }, 404)
  })
}

function dashboardPayload() {
  return {
    source: 'fixture',
    live_indices: [{ name: 'NIFTY 50', symbol: '^NSEI', price: 22000, change_percent: 0.45 }],
    top_stocks: [{ symbol: 'INFY', current_price: 1500, change_percent: 1.2, signal: 'BUY', confidence: 0.72 }],
    alerts: [{ title: 'Provider healthy', detail: 'Fixture cache warmed' }],
    news: [{ title: 'Market breadth improves', source: 'Fixture' }],
    portfolio_value: 6000,
    active_positions: 1,
    directional_accuracy: 62,
    liquidity_score: 78,
    bull: 7,
    bear: 3,
  }
}

function portfolioState(positions: Array<Record<string, unknown>>) {
  const totalValue = positions.reduce((sum, position) => sum + Number(position.current_value ?? 0), 0)
  const totalPnl = positions.reduce((sum, position) => sum + Number(position.pnl ?? 0), 0)
  return {
    success: true,
    positions,
    account_metrics: {
      total_value: totalValue,
      total_pnl: totalPnl,
      total_cost: Math.max(totalValue - totalPnl, 1),
    },
  }
}

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    body: JSON.stringify(body),
    contentType: 'application/json',
    status,
  })
}
