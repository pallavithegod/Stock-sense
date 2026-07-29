import type { LivePrediction, PredictionRow } from '../types/prediction'

type AnyRecord = Record<string, unknown>
const DISPLAY_HORIZON = '6m'

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

function isPresent(value: unknown) {
  if (value === undefined || value === null) return false
  if (typeof value === 'string') return value.trim() !== ''
  if (Array.isArray(value)) return value.length > 0
  return true
}

function firstValue(...values: unknown[]) {
  return values.find(isPresent)
}

function horizonValue(row: AnyRecord, ...keys: string[]) {
  const predictions = isRecord(row.predictions) ? row.predictions : {}
  for (const horizon of [DISPLAY_HORIZON, '1y', '3m', '15d', '1d']) {
    const item = predictions[horizon]
    if (!isRecord(item)) continue
    for (const key of keys) {
      if (isPresent(item[key])) return item[key]
    }
  }
  return undefined
}

function positiveNumber(...values: unknown[]) {
  let fallback: number | undefined
  for (const value of values) {
    const numeric = toNumber(value)
    if (numeric === undefined) continue
    fallback = numeric
    if (numeric > 0) return numeric
  }
  return fallback
}

export type PredictionViewRow = {
  symbol: string
  horizon?: string
  signal: string
  confidence?: number
  price?: number
  target?: number
  expectedReturn?: number
  risk?: string
  allocation?: number
  edge?: number
  dataQuality?: string
  sourceType?: string
  provider?: string
  modelVersion?: string
  synthetic?: boolean
  demo?: boolean
  fingerprint?: string
}

export function normalizePredictionRow(row: PredictionRow): PredictionViewRow {
  const record = row as AnyRecord
  const prediction = isRecord(record.prediction) ? record.prediction : {}
  const price = toNumber(firstValue(
    row.current_price,
    row.price,
    record.actual_price,
    record.currentPrice,
    prediction.current_price,
  ))
  const target = toNumber(firstValue(
    row.target_6m,
    prediction.target_6m,
    horizonValue(record, 'target_price', 'target'),
    horizonValue(prediction, 'target_price', 'target'),
    row.target_price,
    prediction.target_price,
    record.target,
    row.target_1y,
    prediction.target_1y,
  ))
  const explicitReturn = toNumber(firstValue(
    horizonValue(record, 'return_percent', 'return_pct', 'expected_return'),
    horizonValue(prediction, 'return_percent', 'return_pct', 'expected_return'),
    record.expected_return,
    record.expectedReturn,
    prediction.expected_return,
    row.predicted_return,
    prediction.predicted_return,
    row.return_percent,
    record.return_pct,
  ))
  const derivedReturn =
    explicitReturn !== undefined
      ? explicitReturn
      : price !== undefined && target !== undefined && price !== 0
        ? ((target - price) / price) * 100
        : undefined
  const risk = toText(firstValue(
    row.risk,
    row.risk_level,
    record.riskLevel,
    prediction.risk_level,
    prediction.risk,
    record.no_trade_reason,
    `${String(record.models_used ?? '')} ${String(prediction.models_used ?? '')}`.includes('FAILED') ? 'DEGRADED' : undefined,
    'LOW',
  ))

  return {
    symbol: toText(row.symbol) ?? 'UNKNOWN',
    horizon: toText(row.horizon),
    signal: toText(row.signal ?? row.action ?? row.direction) ?? 'WATCH',
    confidence: positiveNumber(row.confidence, row.confidence_score, prediction.confidence, record.probability, record.certainty),
    price,
    target,
    expectedReturn: derivedReturn,
    risk,
    allocation: toNumber(firstValue(
      row.allocation_pct,
      row.ai_size,
      record.weight_pct,
      record.recommended_position_size,
      record.kelly_fraction,
      record.allocation,
    )),
    edge: toNumber(firstValue(row.edge_score, record.edge)),
    dataQuality: toText(firstValue(row.data_quality, record.dataQuality)),
    sourceType: toText(firstValue(row.source_type, record.sourceType, row.source)),
    provider: toText(row.provider),
    modelVersion: toText(row.model_version),
    synthetic: row.is_synthetic === true,
    demo: row.is_demo === true,
    fingerprint: toText(row.fingerprint ?? row.idempotency_key),
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
