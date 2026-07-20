export type PredictionRow = {
  symbol: string
  signal?: string
  confidence?: number
  current_price?: number
  target_price?: number
  predicted_return?: number
  risk?: string
}

export type LivePrediction = {
  symbol: string
  current_price?: number
  predictions?: Record<string, unknown>
  confidence?: number
}
