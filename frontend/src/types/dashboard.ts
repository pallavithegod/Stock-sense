export type DashboardMetric = {
  label: string
  value: string | number
  detail?: string
  tone?: 'neutral' | 'positive' | 'negative' | 'warning'
}

export type DashboardData = {
  portfolioValue?: number
  marketStatus?: string
  activePositions?: number
  predictions?: unknown[]
  [key: string]: unknown
}

export type MarketIndex = {
  name: string
  symbol?: string
  price?: number
  change?: number
  changePercent?: number
}

export type DashboardSignal = {
  symbol: string
  price?: number
  changePercent?: number
  signal?: string
  confidence?: number
}

export type DashboardAlert = {
  title: string
  detail?: string
  severity?: string
  symbol?: string
}

export type NormalizedDashboard = {
  metrics: DashboardMetric[]
  indices: MarketIndex[]
  signals: DashboardSignal[]
  alerts: DashboardAlert[]
  news: DashboardAlert[]
  lastUpdate?: string
  source?: string
  raw: Record<string, unknown>
}
