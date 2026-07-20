import { apiClient } from './client'
import type { PortfolioPosition, PortfolioState } from '../types/portfolio'

export function getPortfolioState() {
  return apiClient.get<PortfolioState>('/portfolio/state', { timeoutMs: 20000 })
}

export function getPortfolio() {
  return apiClient.get<PortfolioPosition[]>('/portfolio', { timeoutMs: 20000 })
}
