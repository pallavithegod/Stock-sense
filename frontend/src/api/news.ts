import { apiClient } from './client'
import { recordOf } from '../schemas/runtime'
import type { RequestOptions } from '../types/api'
import type { AlertsPayload, NewsPayload, ResearchPayload } from '../types/news'

function asNewsPayload(payload: NewsPayload | null | undefined): NewsPayload {
  return payload ?? { articles: [] }
}

export async function getMarketNews(options?: RequestOptions) {
  const payload = asNewsPayload(await apiClient.get<NewsPayload>('/news/market', { timeoutMs: 20000, ...options }))
  recordOf(payload, 'market news response')
  return payload
}

export async function getNews(options?: RequestOptions) {
  const payload = asNewsPayload(await apiClient.get<NewsPayload>('/news', { timeoutMs: 20000, ...options }))
  recordOf(payload, 'news response')
  return payload
}

export function getSymbolNews(symbol: string, options?: RequestOptions) {
  return apiClient.get<NewsPayload>(`/news/symbol/${encodeURIComponent(symbol)}`, {
    timeoutMs: 20000,
    ...options,
  })
}

export function getAlerts(options?: RequestOptions) {
  return apiClient.get<AlertsPayload>('/alerts', { timeoutMs: 20000, ...options })
}

export async function getResearch(options?: RequestOptions) {
  const payload = await apiClient.get<ResearchPayload & {
    research_reports?: ResearchPayload['researchreports']
    ai_insights?: ResearchPayload['aiinsights']
  }>('/research', { timeoutMs: 20000, ...options })
  return {
    ...payload,
    researchreports: payload.researchreports ?? payload.research_reports ?? [],
    aiinsights: payload.aiinsights ?? payload.ai_insights ?? [],
  } satisfies ResearchPayload
}

export function getEmotionalState(symbol: string, options?: RequestOptions) {
  return apiClient.get<Record<string, unknown>>(`/emotional-state/${encodeURIComponent(symbol)}`, {
    timeoutMs: 25000,
    ...options,
  })
}

export function getFuturesAnalysis(symbol: string, options?: RequestOptions) {
  return apiClient.get<Record<string, unknown>>(`/futures-analysis/${encodeURIComponent(symbol)}`, {
    timeoutMs: 25000,
    ...options,
  })
}
