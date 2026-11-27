import { apiClient } from './client'
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
  return extractPredictions(payload)
}

export function getLivePrediction(symbol: string, options?: RequestOptions) {
  return apiClient.get<LivePrediction>(`/predictions/live/${encodeURIComponent(symbol)}`, {
    timeoutMs: 25000,
    ...options,
  })
}
