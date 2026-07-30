import { apiClient } from './client'
import { recordOf } from '../schemas/runtime'
import type { DashboardData } from '../types/dashboard'
import type { RequestOptions } from '../types/api'

async function getRawDashboard(path: string, options: RequestOptions = {}) {
  const payload = await apiClient.get<DashboardData>(path, {
    timeoutMs: 20000,
    unwrapData: false,
    ...options,
  })
  recordOf(payload, 'dashboard response')
  return payload
}

export function getLiveDashboard(options?: RequestOptions) {
  return getRawDashboard('/dashboard-data/live', options)
}

export function getDashboard(options?: RequestOptions) {
  return getRawDashboard('/dashboard-data', options)
}

export function getSystemStatus(options?: RequestOptions) {
  return apiClient.get<Record<string, unknown>>('/system/status', options)
}

export async function getDashboardSnapshot(options?: RequestOptions) {
  try {
    return await getLiveDashboard(options)
  } catch {
    return getDashboard(options)
  }
}
