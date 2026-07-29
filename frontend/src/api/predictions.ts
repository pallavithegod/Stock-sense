import { apiClient } from './client'
import { getPortfolioState } from './portfolio'
import { getStocks } from './stocks'
import type { LivePrediction, PredictionRow } from '../types/prediction'

type PredictionsPayload = {
  data?: PredictionsPayload | PredictionRow[]
  rows?: PredictionRow[]
  predictions?: PredictionRow[]
  stocks?: PredictionRow[]
  opportunities?: PredictionRow[]
}

function extractPredictions(payload: PredictionsPayload | PredictionRow[]) {
  if (Array.isArray(payload)) return payload
  if (payload.data) return extractPredictions(payload.data)
  return payload.rows ?? payload.predictions ?? payload.stocks ?? payload.opportunities ?? []
}

export async function getPredictions() {
  const payload = await apiClient.get<PredictionsPayload | PredictionRow[]>('/predictions', {
    timeoutMs: 20000,
  })
  return extractPredictions(payload)
}

export async function getPredictionIntelligence() {
  const payload = await apiClient.get<PredictionsPayload>(
    '/predictions/intelligence?top_n=100',
    { timeoutMs: 25000 },
  )
  const rows = extractPredictions(payload)
  if (rows.length) return rows
  return getPredictionFallbackRows()
}

export function getLivePrediction(symbol: string) {
  return apiClient.get<LivePrediction>(`/predictions/live/${encodeURIComponent(symbol)}`, {
    timeoutMs: 25000,
  })
}

async function getPredictionFallbackRows(): Promise<PredictionRow[]> {
  try {
    const portfolio = await getPortfolioState()
    if (portfolio.positions.length) {
      return portfolio.positions.map((position) => ({
        symbol: String(position.symbol ?? 'UNKNOWN'),
        signal: 'WATCH',
        current_price: Number(position.current_price ?? position.avg_price) || undefined,
        confidence: undefined,
        risk: 'unavailable_without_prediction_pipeline',
        data_quality: 'portfolio_only',
        source_type: 'presentation_intelligence',
      }))
    }
  } catch {
    // Use the static market universe below if portfolio state is unavailable.
  }

  const stocks = await getStocks(12)
  return stocks.map((stock) => ({
    symbol: String(stock.symbol ?? 'UNKNOWN'),
    signal: 'WATCH',
    current_price: Number(stock.current_price ?? stock.price) || undefined,
    confidence: undefined,
    risk: 'unavailable_without_prediction_pipeline',
    data_quality: 'unavailable',
    source_type: 'presentation_intelligence',
  }))
}
