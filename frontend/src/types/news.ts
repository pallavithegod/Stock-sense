export type NewsArticle = {
  title: string
  description?: string
  url?: string
  link?: string
  source?: string
  publisher?: string
  sentiment?: string
  sentiment_score?: number
  confidence?: number
  source_reliability?: number
  sector?: string
  why_it_matters?: string
  relevance_type?: string
  published_at?: string
  published?: string
  normalized_time?: string
  providerPublishTime?: string
  [key: string]: unknown
}

export type NewsPayload = {
  articles?: NewsArticle[]
  sentiment?: Record<string, unknown>
  sectorwise?: Record<string, unknown>
  heatmap?: unknown[]
  label?: string
  sentiment_score?: number
  confidence?: number
  timestamp?: string
  [key: string]: unknown
}

export type AlertItem = {
  symbol?: string
  condition?: string
  target_value?: number
  current_value?: number
  triggered?: boolean
  message?: string
  [key: string]: unknown
}

export type AlertsPayload = {
  active_alerts?: number
  triggered_today?: number
  alerts?: AlertItem[]
  [key: string]: unknown
}

export type ResearchReport = {
  title?: string
  description?: string
  confidence?: number
  findings?: string[] | string
  timestamp?: string
  [key: string]: unknown
}

export type ResearchInsight = {
  insight?: string
  description?: string
  probability?: number
  impact?: string
  timeframe?: string
  model_confidence?: number
  based_on?: string
  [key: string]: unknown
}

export type ResearchPayload = {
  researchreports?: ResearchReport[]
  aiinsights?: ResearchInsight[]
  model_performance?: Record<string, unknown>
  live_stats?: Record<string, unknown>
  message?: string
  [key: string]: unknown
}
