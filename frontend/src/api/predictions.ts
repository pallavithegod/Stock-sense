import { apiClient } from './client'
import type { LivePrediction, PredictionRow } from '../types/prediction'

export function getPredictions() {
  return apiClient.get<PredictionRow[]>('/predictions', { timeoutMs: 20000 })
}

export function getPredictionIntelligence() {
  return apiClient.get<{ rows?: PredictionRow[]; predictions?: PredictionRow[] }>(
    '/predictions/intelligence?top_n=100',
    { timeoutMs: 25000 },
  )
}

export function getLivePrediction(symbol: string) {
  return apiClient.get<LivePrediction>(`/predictions/live/${encodeURIComponent(symbol)}`, {
    timeoutMs: 25000,
  })
}
