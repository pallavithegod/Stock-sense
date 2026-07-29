export type PredictionRow = {
  symbol: string
  horizon?: string
  as_of?: string
  signal?: string
  action?: string
  direction?: string
  confidence?: number
  confidence_score?: number
  current_price?: number
  price?: number
  target_price?: number
  expected_return?: number
  target_6m?: number
  target_1y?: number
  predicted_return?: number
  return_percent?: number
  risk?: string
  risk_level?: string
  allocation_pct?: number
  ai_size?: number
  edge_score?: number
  data_quality?: string
  source_type?: string
  provider?: string
  model_version?: string | null
  feature_version?: string | null
  is_synthetic?: boolean
  is_demo?: boolean
  fingerprint?: string
  idempotency_key?: string
  source?: string
  prediction?: {
    confidence?: number
    current_price?: number
    expected_return?: number
    predicted_return?: number
    return_percent?: number
    risk?: string
    risk_level?: string
    target_price?: number
    target_6m?: number
    target_1y?: number
    predictions?: Record<string, unknown>
  }
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
