import { apiClient } from './client'
import type { AlertsPayload, NewsPayload, ResearchPayload } from '../types/news'

function asNewsPayload(payload: NewsPayload | null | undefined): NewsPayload {
  return payload ?? { articles: [] }
}

export async function getMarketNews() {
  return asNewsPayload(await apiClient.get<NewsPayload>('/news/market', { timeoutMs: 20000, unwrapData: false }))
}

export async function getNews() {
  return asNewsPayload(await apiClient.get<NewsPayload>('/news', { timeoutMs: 20000, unwrapData: false }))
}

export function getSymbolNews(symbol: string) {
  return apiClient.get<NewsPayload>(`/news/symbol/${encodeURIComponent(symbol)}`, {
    timeoutMs: 20000,
    unwrapData: false,
  })
}

export function getAlerts() {
  return apiClient.get<AlertsPayload>('/alerts', { timeoutMs: 20000, unwrapData: false })
}

export function getResearch() {
  return apiClient.get<ResearchPayload>('/research', { timeoutMs: 20000, unwrapData: false })
}

export function getEmotionalState(symbol: string) {
  return apiClient.get<Record<string, unknown>>(`/emotional-state/${encodeURIComponent(symbol)}`, {
    timeoutMs: 25000,
  })
}

export function getFuturesAnalysis(symbol: string) {
  return apiClient.get<Record<string, unknown>>(`/futures-analysis/${encodeURIComponent(symbol)}`, {
    timeoutMs: 25000,
  })
}
