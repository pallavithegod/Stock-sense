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
