import { apiClient } from './client'
import { optionalArray } from '../schemas/runtime'
import type { RequestOptions } from '../types/api'
import type { StockSearchResult, StockSummary } from '../types/stock'
import { normalizeSearchResults } from '../utils/stockSearch'

type SearchPayload = {
  results?: StockSearchResult[]
  data?: StockSearchResult[]
  stocks?: StockSearchResult[]
}

type StocksPayload = {
  data?: StockSummary[]
  stocks?: StockSummary[]
  results?: StockSummary[]
}

function extractArray<T>(payload: T[] | Record<string, unknown> | null | undefined, keys: string[]) {
  if (Array.isArray(payload)) return optionalArray<T>(payload)
  if (!payload || typeof payload !== 'object') return []
  for (const key of keys) {
    const value = payload[key]
    if (Array.isArray(value)) return optionalArray<T>(value)
  }
  return []
}

export async function searchStocks(query: string, limit = 20, options?: RequestOptions) {
  const params = `q=${encodeURIComponent(query)}&limit=${limit}`
  const primary = await apiClient.get<SearchPayload | StockSearchResult[]>(
    `/search/comprehensive?${params}`,
    options,
  )
  const primaryResults = extractArray<StockSearchResult>(primary, ['results', 'data', 'stocks'])
  const normalizedPrimary = normalizeSearchResults(query, primaryResults, limit)
  if (normalizedPrimary.length) return normalizedPrimary

  const fallback = await apiClient.get<SearchPayload | StockSearchResult[]>(`/search?${params}`, options)
  return normalizeSearchResults(
    query,
    extractArray<StockSearchResult>(fallback, ['results', 'data', 'stocks']),
    limit,
  )
}

export async function getStocks(limit = 20, options?: RequestOptions) {
  const payload = await apiClient.get<StocksPayload | StockSummary[]>(`/stocks?limit=${limit}`, {
    timeoutMs: 20000,
    ...options,
  })
  return extractArray<StockSummary>(payload, ['stocks', 'data', 'results'])
}

export function getStock(symbol: string, options?: RequestOptions) {
  return apiClient.get<StockSummary>(`/stock/${encodeURIComponent(symbol)}`, { timeoutMs: 20000, ...options })
}
