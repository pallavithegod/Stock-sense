import { apiClient } from './client'
import type { DashboardData } from '../types/dashboard'

export function getLiveDashboard() {
  return apiClient.get<DashboardData>('/dashboard-data/live', { timeoutMs: 20000 })
}

export function getDashboard() {
  return apiClient.get<DashboardData>('/dashboard-data', { timeoutMs: 20000 })
}

export function getSystemStatus() {
  return apiClient.get<Record<string, unknown>>('/system/status')
}

export async function getDashboardSnapshot() {
  try {
    return await getLiveDashboard()
  } catch {
    return getDashboard()
  }
}
