export type PredictionRow = {
  symbol: string
  signal?: string
  action?: string
  direction?: string
  confidence?: number
  confidence_score?: number
  current_price?: number
  price?: number
  target_price?: number
  target_6m?: number
  target_1y?: number
  predicted_return?: number
  return_percent?: number
  risk?: string
  risk_level?: string
  allocation_pct?: number
  ai_size?: number
  edge_score?: number
}

export type LivePrediction = {
  symbol: string
  current_price?: number
  data?: {
    symbol?: string
    current_price?: number
    predictions?: Record<string, unknown>
    confidences?: Record<string, unknown>
    market_conditions?: Record<string, unknown>
  }
  predictions?: Record<string, unknown>
  confidence?: number
}
