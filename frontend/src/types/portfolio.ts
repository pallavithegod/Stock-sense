export type PortfolioPosition = {
  symbol: string
  quantity?: number
  qty?: number
  open_qty?: number
  avg_price?: number
  price?: number
  current_price?: number
  current_value?: number
  value?: number
  pnl?: number
  unrealized_pnl?: number
  pnl_percent?: number
  action?: string
  confidence?: number
  sector?: string
  [key: string]: unknown
}

export type PortfolioState = {
  success?: boolean
  positions: PortfolioPosition[]
  account_metrics?: Record<string, unknown>
  stale?: boolean
}

export type PortfolioLot = {
  id?: number
  lot_id?: number
  symbol?: string
  quantity?: number
  qty?: number
  open_qty?: number
  buy_price?: number
  avg_price?: number
  purchase_price?: number
  buy_date?: string
  purchase_date?: string
  added_date?: string
  status?: string
  [key: string]: unknown
}

export type RealizedGain = {
  symbol?: string
  quantity?: number
  sell_price?: number
  buy_price?: number
  realized_gain?: number
  realized_stcg?: number
  realized_ltcg?: number
  gain_type?: string
  sell_date?: string
  [key: string]: unknown
}

export type PortfolioMutationPayload = {
  symbol: string
  quantity: number
  avg_price: number
  purchase_date?: string
}

export type SellSimulationPayload = {
  symbol: string
  quantity: number
  sell_price: number
  sell_date?: string
  fees?: number
  methods?: string[]
}

export type PortfolioCollection<T> = {
  data: T[]
  count?: number
  total?: number
}

export type PortfolioEnvelope<T> = {
  status?: string
  success?: boolean
  data?: T
  error?: string
  message?: string
}
