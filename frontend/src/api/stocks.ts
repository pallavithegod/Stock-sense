import { apiClient } from './client'
import { optionalArray } from '../schemas/runtime'
import type { RequestOptions } from '../types/api'
import type { StockSearchResult, StockSummary } from '../types/stock'

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

function compact(value: string | undefined) {
  return (value ?? '').toUpperCase().replace(/\.NS$|\.BO$/g, '').replace(/[^A-Z0-9]/g, '')
}

function searchRank(query: string, stock: StockSearchResult) {
  const q = compact(query)
  const symbol = compact(stock.symbol)
  const display = compact(stock.display)
  const name = compact(stock.name)

  if (!q) return 99
  if (symbol === q || display === q) return 0
  if (symbol.startsWith(q) || display.startsWith(q)) return 1
  if (name.startsWith(q)) return 2
  if (symbol.includes(q) || display.includes(q)) return 3
  if (name.includes(q)) return 4
  return 99
}

function normalizeSearchResults(query: string, results: StockSearchResult[], limit: number) {
  return results
    .filter((stock) => searchRank(query, stock) < 99)
    .sort((a, b) => {
      const rankDelta = searchRank(query, a) - searchRank(query, b)
      if (rankDelta !== 0) return rankDelta
      const aSymbol = compact(a.display || a.symbol)
      const bSymbol = compact(b.display || b.symbol)
      const lengthDelta = Math.abs(aSymbol.length - compact(query).length) - Math.abs(bSymbol.length - compact(query).length)
      if (lengthDelta !== 0) return lengthDelta
      return aSymbol.localeCompare(bSymbol)
    })
    .slice(0, limit)
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
