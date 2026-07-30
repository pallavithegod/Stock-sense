import { expect, test } from 'vitest'
import { arrayOf, recordOf } from '../../src/schemas/runtime'
import { formatDate, formatNumber, formatPercent } from '../../src/utils/format'
import { normalizeDashboard } from '../../src/utils/dashboardAdapter'
import { normalizeLivePrediction, normalizePredictionRow } from '../../src/utils/predictionAdapter'
import { normalizeSearchResults, searchRank } from '../../src/utils/stockSearch'

test.describe('format helpers', () => {
  test('formats Indian numbers, dates, and unavailable values consistently', () => {
    expect(formatNumber(1234567.891)).toBe('12,34,567.89')
    expect(formatNumber('not-a-number')).toBe('--')
    expect(formatPercent(4.2)).toBe('+4.20%')
    expect(formatPercent(-1.234)).toBe('-1.23%')
    expect(formatDate('2026-01-15T10:00:00Z')).toBe('15 Jan 2026')
    expect(formatDate('bad-date')).toBe('--')
  })
})

test.describe('runtime validation helpers', () => {
  test('reject invalid object and array responses with useful messages', () => {
    expect(() => recordOf(null, 'portfolio response')).toThrow('portfolio response was not a JSON object.')
    expect(() => arrayOf({ rows: [] }, undefined, 'stock response')).toThrow('stock response was not an array.')
  })
})

test.describe('stock search ranking', () => {
  const rows = [
    { symbol: 'TATAMOTORS.NS', display: 'TATAMOTORS', name: 'Tata Motors Limited' },
    { symbol: 'INFY.NS', display: 'INFY', name: 'Infosys Limited' },
    { symbol: 'KOTAKBANK.NS', display: 'KOTAKBANK', name: 'Kotak Mahindra Bank' },
    { symbol: 'ABC.NS', display: 'ABC', name: 'Logistics Infy' },
  ]

  test('prioritizes exact and prefix symbol matches over company-name contains', () => {
    expect(searchRank('INFY', rows[1])).toBe(0)
    expect(searchRank('INFY', rows[3])).toBe(4)
    expect(normalizeSearchResults('TATA', rows, 10).map((row) => row.display)).toEqual(['TATAMOTORS'])
    expect(normalizeSearchResults('KOTAK', rows, 10).map((row) => row.display)).toEqual(['KOTAKBANK'])
  })

  test('returns an empty result set for no-match queries', () => {
    expect(normalizeSearchResults('ZZZZ', rows, 10)).toEqual([])
  })
})

test.describe('prediction adapters', () => {
  test('normalizes explicit prediction rows and derives missing return', () => {
    const row = normalizePredictionRow({
      symbol: 'INFY',
      signal: 'BUY',
      current_price: 1000,
      target_price: 1125,
      confidence: 0.71,
      source_type: 'ml_model',
      provider: 'fixture',
      model_version: 'v1',
      idempotency_key: 'INFY-6m',
    })

    expect(row).toMatchObject({
      symbol: 'INFY',
      signal: 'BUY',
      confidence: 0.71,
      expectedReturn: 12.5,
      sourceType: 'ml_model',
      provider: 'fixture',
      modelVersion: 'v1',
      fingerprint: 'INFY-6m',
    })
  })

  test('normalizes nested live prediction horizons', () => {
    const view = normalizeLivePrediction({
      data: {
        symbol: 'TCS',
        current_price: 3500,
        predictions: {
          '1m': { target_price: 3600, return_percent: 2.86 },
          '6m': { target_price: 3900, return_percent: 11.43 },
        },
        market_conditions: { momentum: 'positive', volatility_level: 'low' },
      },
    })

    expect(view?.symbol).toBe('TCS')
    expect(view?.horizons).toHaveLength(2)
    expect(view?.horizons[1]).toEqual({ label: '6m', target: 3900, returnPercent: 11.43 })
  })

  test('preserves zero values and marks unavailable values explicitly', () => {
    const row = normalizePredictionRow({
      symbol: 'ZERO',
      current_price: 0,
      confidence: 0,
      target_price: null,
      data_quality: 'unavailable',
      source_type: 'presentation_intelligence',
    })

    expect(row.price).toBe(0)
    expect(row.confidence).toBe(0)
    expect(row.expectedReturn).toBeUndefined()
    expect(row.dataQuality).toBe('unavailable')
    expect(row.sourceType).toBe('presentation_intelligence')
  })
})

test.describe('dashboard adapter', () => {
  test('uses portfolio positions as signal fallback and preserves provenance', () => {
    const dashboard = normalizeDashboard({
      source: 'fixture',
      PORTFOLIO_STATE: {
        positions: [
          { symbol: 'INFY', current_price: 1500, change_percent: 1.2, action: 'WATCH', confidence: 0.5 },
        ],
      },
      live_indices: [{ name: 'NIFTY 50', symbol: '^NSEI', price: 22000, change_percent: 0.4 }],
    })

    expect(dashboard.source).toBe('fixture')
    expect(dashboard.indices[0].name).toBe('NIFTY 50')
    expect(dashboard.signals[0]).toMatchObject({ symbol: 'INFY', signal: 'WATCH', price: 1500 })
    expect(dashboard.metrics[0].detail).toBe('1 active positions')
  })
})
