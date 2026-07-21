export type StockSearchResult = {
  symbol: string
  display?: string
  name?: string
  sector?: string
  exchange?: string
  price?: number
  current_price?: number
  change_percent?: number
  change_value?: number
}

export type StockSummary = {
  symbol: string
  name?: string
  current_price?: number
  price?: number
  change_percent?: number
  sector?: string
  signal?: string
  confidence?: number
}
