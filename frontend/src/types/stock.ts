export type StockSearchResult = {
  symbol: string
  display?: string
  name?: string
  sector?: string
  exchange?: string
}

export type StockSummary = {
  symbol: string
  name?: string
  current_price?: number
  change_percent?: number
  sector?: string
}
