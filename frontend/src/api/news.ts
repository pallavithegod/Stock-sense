import { apiClient } from './client'
import type { NewsPayload } from '../types/news'

export function getMarketNews() {
  return apiClient.get<NewsPayload>('/news/market', { timeoutMs: 20000 })
}

export function getNews() {
  return apiClient.get<NewsPayload>('/news', { timeoutMs: 20000 })
}

export function getSymbolNews(symbol: string) {
  return apiClient.get<NewsPayload>(`/news/symbol/${encodeURIComponent(symbol)}`, {
    timeoutMs: 20000,
  })
}
