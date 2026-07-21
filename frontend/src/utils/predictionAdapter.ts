import type { LivePrediction, PredictionRow } from '../types/prediction'

type AnyRecord = Record<string, unknown>

function toNumber(value: unknown): number | undefined {
  const num = Number(value)
  return Number.isFinite(num) ? num : undefined
}

function toText(value: unknown): string | undefined {
  if (value === undefined || value === null || value === '') return undefined
  return String(value)
}

function isRecord(value: unknown): value is AnyRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export type PredictionViewRow = {
  symbol: string
  signal: string
  confidence?: number
  price?: number
  target?: number
  expectedReturn?: number
  risk?: string
  allocation?: number
  edge?: number
}

export function normalizePredictionRow(row: PredictionRow): PredictionViewRow {
  return {
    symbol: toText(row.symbol) ?? 'UNKNOWN',
    signal: toText(row.signal ?? row.action ?? row.direction) ?? 'WATCH',
    confidence: toNumber(row.confidence ?? row.confidence_score),
    price: toNumber(row.current_price ?? row.price),
    target: toNumber(row.target_price ?? row.target_6m ?? row.target_1y),
    expectedReturn: toNumber(row.predicted_return ?? row.return_percent),
    risk: toText(row.risk ?? row.risk_level),
    allocation: toNumber(row.allocation_pct ?? row.ai_size),
    edge: toNumber(row.edge_score),
  }
}

export type LivePredictionView = {
  symbol: string
  price?: number
  horizons: Array<{ label: string; target?: number; returnPercent?: number }>
  momentum?: string
  volatility?: string
}

export function normalizeLivePrediction(payload: LivePrediction | null): LivePredictionView | null {
  if (!payload) return null
  const data: AnyRecord = isRecord(payload.data) ? payload.data : (payload as unknown as AnyRecord)
  const predictions = isRecord(data.predictions) ? data.predictions : {}

  const horizons = Object.entries(predictions).map(([label, value]) => {
    const item = isRecord(value) ? value : {}
    return {
      label,
      target: toNumber(item.target_price),
      returnPercent: toNumber(item.return_percent),
    }
  })

  const market = isRecord(data.market_conditions) ? data.market_conditions : {}

  return {
    symbol: toText(data.symbol ?? payload.symbol) ?? 'UNKNOWN',
    price: toNumber(data.current_price ?? payload.current_price),
    horizons,
    momentum: toText(market.momentum),
    volatility: toText(market.volatility_level),
  }
}
