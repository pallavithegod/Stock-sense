import { formatNumber, formatPercent } from './format'
import type { StockSearchResult, StockSummary } from '../types/stock'

export function stockDisplayName(stock: StockSearchResult | StockSummary) {
  return stock.name || stock.symbol
}

export function stockDisplaySymbol(stock: StockSearchResult | StockSummary) {
  return ('display' in stock && stock.display) || stock.symbol
}

export function stockPrice(stock: StockSearchResult | StockSummary) {
  return stock.current_price ?? stock.price
}

export function stockChange(stock: StockSearchResult | StockSummary) {
  return stock.change_percent
}

export function stockMetaLine(stock: StockSearchResult | StockSummary) {
  const parts = [
    'exchange' in stock ? stock.exchange : undefined,
    stock.sector,
    stockPrice(stock) !== undefined ? `Price ${formatNumber(stockPrice(stock))}` : undefined,
    stockChange(stock) !== undefined ? formatPercent(stockChange(stock)) : undefined,
  ].filter(Boolean)

  return parts.join(' | ')
}
