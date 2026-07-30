import { apiClient } from './client'
import { getPortfolioState } from './portfolio'
import { getStocks } from './stocks'
import { optionalArray } from '../schemas/runtime'
import type { RequestOptions } from '../types/api'
import type { LivePrediction, PredictionRow } from '../types/prediction'

type PredictionsPayload = {
  data?: PredictionsPayload | PredictionRow[]
  rows?: PredictionRow[]
  predictions?: PredictionRow[]
  stocks?: PredictionRow[]
  opportunities?: PredictionRow[]
}

function extractPredictions(payload: PredictionsPayload | PredictionRow[]) {
  if (Array.isArray(payload)) return optionalArray<PredictionRow>(payload)
  if (payload.data) return extractPredictions(payload.data)
  return optionalArray<PredictionRow>(payload.rows ?? payload.predictions ?? payload.stocks ?? payload.opportunities)
}

export async function getPredictions(options?: RequestOptions) {
  const payload = await apiClient.get<PredictionsPayload | PredictionRow[]>('/predictions', {
    timeoutMs: 20000,
    ...options,
  })
  return extractPredictions(payload)
}

export async function getPredictionIntelligence(options?: RequestOptions) {
  const payload = await apiClient.get<PredictionsPayload>(
    '/predictions/intelligence?top_n=100',
    { timeoutMs: 25000, ...options },
  )
  const rows = extractPredictions(payload)
  if (rows.length) return rows
  return getPredictionFallbackRows(options)
}

export function getLivePrediction(symbol: string, options?: RequestOptions) {
  return apiClient.get<LivePrediction>(`/predictions/live/${encodeURIComponent(symbol)}`, {
    timeoutMs: 25000,
    ...options,
  })
}

async function getPredictionFallbackRows(options?: RequestOptions): Promise<PredictionRow[]> {
  try {
    const portfolio = await getPortfolioState(options)
    if (portfolio.positions.length) {
      return portfolio.positions.map((position) => ({
        symbol: String(position.symbol ?? 'UNKNOWN'),
        signal: 'WATCH',
        current_price: Number(position.current_price ?? position.avg_price) || undefined,
        confidence: undefined,
        risk: 'unavailable_without_prediction_pipeline',
        data_quality: 'portfolio_only',
        source_type: 'presentation_intelligence',
        provider: 'frontend_portfolio_fallback',
        model_version: null,
        is_synthetic: false,
        is_demo: false,
      }))
    }
  } catch {
    // Use the static market universe below if portfolio state is unavailable.
  }

  const stocks = await getStocks(12, options)
  return stocks.map((stock) => ({
    symbol: String(stock.symbol ?? 'UNKNOWN'),
    signal: 'WATCH',
    current_price: Number(stock.current_price ?? stock.price) || undefined,
    confidence: undefined,
    risk: 'unavailable_without_prediction_pipeline',
    data_quality: 'unavailable',
    source_type: 'presentation_intelligence',
    provider: 'frontend_market_universe_fallback',
    model_version: null,
    is_synthetic: false,
    is_demo: false,
  }))
}
