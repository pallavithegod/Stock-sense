export type PortfolioPosition = {
  symbol: string
  quantity?: number
  open_qty?: number
  avg_price?: number
  current_price?: number
  current_value?: number
  pnl?: number
  pnl_percent?: number
  action?: string
  confidence?: number
}

export type PortfolioState = {
  success?: boolean
  positions: PortfolioPosition[]
  account_metrics?: Record<string, unknown>
}
