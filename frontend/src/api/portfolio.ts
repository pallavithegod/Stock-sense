import { apiClient } from './client'
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
  if (Array.isArray(checked)) return { data: checked } satisfies PortfolioCollection<T>
  if (checked && typeof checked === 'object') {
    const data = 'data' in checked && Array.isArray(checked.data) ? (checked.data as T[]) : []
    return {
      data,
      count: 'count' in checked && typeof checked.count === 'number' ? checked.count : data.length,
      total: 'total' in checked && typeof checked.total === 'number' ? checked.total : data.length,
    } satisfies PortfolioCollection<T>
  }
  return { data: [] } satisfies PortfolioCollection<T>
}

export async function getPortfolioState() {
  const state = await apiClient.get<PortfolioState>('/portfolio/state', {
    timeoutMs: 20000,
    unwrapData: false,
  })
  if (Array.isArray(state.positions) && state.positions.length > 0) {
    return state
  }

  const positions = await getPortfolio()
  return {
    ...state,
    success: state.success ?? true,
    positions,
    account_metrics: state.account_metrics ?? {},
  } satisfies PortfolioState
}

export async function getPortfolio() {
  const payload = await apiClient.get<PortfolioPosition[] | Record<string, unknown>>('/portfolio', {
    timeoutMs: 20000,
  })
  return extractCollection<PortfolioPosition>(payload).data
}

export async function createPortfolioPosition(payload: PortfolioMutationPayload) {
  const response = await apiClient.post<PortfolioEnvelope<{ exchange_symbol?: string }>>('/portfolio', payload, {
    timeoutMs: 20000,
  })
  return ensureOk(response)
}

export async function updatePortfolioPosition(symbol: string, payload: PortfolioMutationPayload) {
  const response = await apiClient.put<PortfolioEnvelope<unknown>>(`/portfolio/${encodeURIComponent(symbol)}`, payload, {
    timeoutMs: 20000,
  })
  return ensureOk(response)
}

export async function deletePortfolioPosition(symbol: string) {
  const response = await apiClient.delete<PortfolioEnvelope<unknown>>(`/portfolio/${encodeURIComponent(symbol)}`, {
    timeoutMs: 20000,
  })
  return ensureOk(response)
}

export async function getPortfolioLots(symbol?: string) {
  const query = symbol ? `?symbol=${encodeURIComponent(symbol)}&only_open=1` : '?only_open=1'
  const payload = await apiClient.get<PortfolioEnvelope<PortfolioLot[]> | Record<string, unknown>>(
    `/portfolio/lots${query}`,
    { timeoutMs: 20000 },
  )
  return extractCollection<PortfolioLot>(payload)
}

export async function getRealizedGains(symbol?: string) {
  const query = symbol ? `?symbol=${encodeURIComponent(symbol)}` : ''
  const payload = await apiClient.get<PortfolioEnvelope<RealizedGain[]> | Record<string, unknown>>(
    `/portfolio/realized-gains${query}`,
    { timeoutMs: 20000 },
  )
  return extractCollection<RealizedGain>(payload)
}

export async function getPortfolioTaxSummary() {
  const payload = await apiClient.get<PortfolioEnvelope<Record<string, unknown>>>(
    '/portfolio/tax-summary',
    { timeoutMs: 20000 },
  )
  return extractData<Record<string, unknown>>(payload)
}

export async function getPortfolioLotInsights(symbol?: string) {
  const query = symbol ? `?symbol=${encodeURIComponent(symbol)}` : ''
  const payload = await apiClient.get<PortfolioEnvelope<Record<string, unknown>>>(
    `/portfolio/lot-insights${query}`,
    { timeoutMs: 20000 },
  )
  return extractData<Record<string, unknown>>(payload)
}

export async function getPortfolioIntelligenceSuite() {
  const payload = await apiClient.get<PortfolioEnvelope<Record<string, unknown>>>(
    '/portfolio/intelligence-suite',
    { timeoutMs: 25000 },
  )
  return extractData<Record<string, unknown>>(payload)
}

export async function simulatePortfolioSell(payload: SellSimulationPayload) {
  const response = await apiClient.post<PortfolioEnvelope<Record<string, unknown>>>(
    '/portfolio/sell/simulate',
    payload,
    { timeoutMs: 20000 },
  )
  return extractData<Record<string, unknown>>(response)
}
