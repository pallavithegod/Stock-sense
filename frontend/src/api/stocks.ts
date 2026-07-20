import { apiClient } from './client'
import type { StockSearchResult, StockSummary } from '../types/stock'

export function searchStocks(query: string, limit = 20) {
  return apiClient.get<StockSearchResult[]>(
    `/search/comprehensive?q=${encodeURIComponent(query)}&limit=${limit}`,
  )
}

export function getStocks(limit = 20) {
  return apiClient.get<StockSummary[]>(`/stocks?limit=${limit}`, { timeoutMs: 20000 })
}

export function getStock(symbol: string) {
  return apiClient.get<StockSummary>(`/stock/${encodeURIComponent(symbol)}`, { timeoutMs: 20000 })
}
