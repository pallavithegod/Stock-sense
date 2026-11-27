import { apiClient } from './client'
import { optionalArray, recordOf } from '../schemas/runtime'
import type { RequestOptions } from '../types/api'
import type {
  PortfolioCollection,
  PortfolioEnvelope,
  PortfolioLot,
  PortfolioMutationPayload,
  PortfolioPosition,
  PortfolioState,
  RealizedGain,
  SellSimulationPayload,
} from '../types/portfolio'

function ensureOk<T>(payload: PortfolioEnvelope<T> | T) {
  if (
    payload &&
    typeof payload === 'object' &&
    'status' in payload &&
    payload.status === 'error'
  ) {
    throw new Error(String(payload.error || payload.message || 'Portfolio request failed'))
  }
  return payload
}

function extractData<T>(payload: PortfolioEnvelope<T> | T): T {
  const checked = ensureOk(payload)
  if (checked && typeof checked === 'object' && 'data' in checked && checked.data !== undefined) {
    return checked.data as T
  }
  return checked as T
}

function extractCollection<T>(payload: PortfolioEnvelope<T[]> | T[] | Record<string, unknown>) {
  const checked = ensureOk(payload)
  if (Array.isArray(checked)) return { data: optionalArray<T>(checked) } satisfies PortfolioCollection<T>
  if (checked && typeof checked === 'object') {
    const data = 'data' in checked && Array.isArray(checked.data) ? optionalArray<T>(checked.data) : []
    return {
      data,
      count: 'count' in checked && typeof checked.count === 'number' ? checked.count : data.length,
      total: 'total' in checked && typeof checked.total === 'number' ? checked.total : data.length,
    } satisfies PortfolioCollection<T>
  }
  return { data: [] } satisfies PortfolioCollection<T>
}

export async function getPortfolioState(options?: RequestOptions) {
  const state = await apiClient.get<PortfolioState>('/portfolio', {
    timeoutMs: 20000,
    ...options,
  })
  recordOf(state, 'portfolio state response')
  if (Array.isArray(state.positions) && state.positions.length > 0) {
    return state
  }

  const positions = await getPortfolio(options)
  return {
    ...state,
    success: state.success ?? true,
    positions,
    account_metrics: state.account_metrics ?? {},
  } satisfies PortfolioState
}

export async function getPortfolio(options?: RequestOptions) {
  const payload = await apiClient.get<PortfolioPosition[] | Record<string, unknown>>('/portfolio/positions', {
    timeoutMs: 20000,
    ...options,
  })
  const collection = extractCollection<PortfolioPosition>(payload)
  if (collection.data.length) return collection.data
  return 'positions' in payload && Array.isArray(payload.positions)
    ? optionalArray<PortfolioPosition>(payload.positions)
    : []
}

export async function createPortfolioPosition(payload: PortfolioMutationPayload, options?: RequestOptions) {
  const response = await apiClient.post<PortfolioEnvelope<{ exchange_symbol?: string }>>('/portfolio', payload, {
    timeoutMs: 20000,
    ...options,
  })
  return ensureOk(response)
}

export async function updatePortfolioPosition(symbol: string, payload: PortfolioMutationPayload, options?: RequestOptions) {
  const response = await apiClient.put<PortfolioEnvelope<unknown>>(`/portfolio/${encodeURIComponent(symbol)}`, payload, {
    timeoutMs: 20000,
    ...options,
  })
  return ensureOk(response)
}

export async function deletePortfolioPosition(symbol: string, options?: RequestOptions) {
  const response = await apiClient.delete<PortfolioEnvelope<unknown>>(`/portfolio/${encodeURIComponent(symbol)}`, {
    timeoutMs: 20000,
    ...options,
  })
  return ensureOk(response)
}

export async function getPortfolioLots(symbol?: string, options?: RequestOptions) {
  const query = symbol ? `?symbol=${encodeURIComponent(symbol)}&only_open=1` : '?only_open=1'
  const payload = await apiClient.get<PortfolioEnvelope<PortfolioLot[]> | Record<string, unknown>>(
    `/portfolio/lots${query}`,
    { timeoutMs: 20000, ...options },
  )
  return extractCollection<PortfolioLot>(payload)
}

export async function getRealizedGains(symbol?: string, options?: RequestOptions) {
  const query = symbol ? `?symbol=${encodeURIComponent(symbol)}` : ''
  const payload = await apiClient.get<PortfolioEnvelope<RealizedGain[]> | Record<string, unknown>>(
    `/portfolio/realized-gains${query}`,
    { timeoutMs: 20000, ...options },
  )
  return extractCollection<RealizedGain>(payload)
}

export async function getPortfolioTaxSummary(options?: RequestOptions) {
  const payload = await apiClient.get<PortfolioEnvelope<Record<string, unknown>>>(
    '/portfolio/tax-summary',
    { timeoutMs: 20000, ...options },
  )
  return extractData<Record<string, unknown>>(payload)
}

export async function getPortfolioLotInsights(symbol?: string, options?: RequestOptions) {
  const query = symbol ? `?symbol=${encodeURIComponent(symbol)}` : ''
  const payload = await apiClient.get<PortfolioEnvelope<Record<string, unknown>>>(
    `/portfolio/lot-insights${query}`,
    { timeoutMs: 20000, ...options },
  )
  return extractData<Record<string, unknown>>(payload)
}

export async function getPortfolioIntelligenceSuite(options?: RequestOptions) {
  const payload = await apiClient.get<PortfolioEnvelope<Record<string, unknown>>>(
    '/portfolio/intelligence-suite',
    { timeoutMs: 25000, ...options },
  )
  return extractData<Record<string, unknown>>(payload)
}

export async function simulatePortfolioSell(payload: SellSimulationPayload, options?: RequestOptions) {
  const response = await apiClient.post<PortfolioEnvelope<Record<string, unknown>>>(
    '/portfolio/sell/simulate',
    payload,
    { timeoutMs: 20000, ...options },
  )
  return extractData<Record<string, unknown>>(response)
}

export async function recordPortfolioSell(payload: SellSimulationPayload, options?: RequestOptions) {
  const response = await apiClient.post<PortfolioEnvelope<Record<string, unknown>>>(
    '/portfolio/sell',
    { ...payload, method: 'FIFO' },
    { timeoutMs: 20000, ...options },
  )
  return extractData<Record<string, unknown>>(response)
}
