import { apiClient } from './client'
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
  return extractPredictions(payload)
}

export function getLivePrediction(symbol: string) {
  return apiClient.get<LivePrediction>(`/predictions/live/${encodeURIComponent(symbol)}`, {
    timeoutMs: 25000,
  })
}
