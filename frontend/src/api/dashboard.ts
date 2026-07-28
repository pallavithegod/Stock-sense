import { apiClient } from './client'
import type { DashboardData } from '../types/dashboard'

async function getRawDashboard(path: string, timeoutMs = 20000) {
  return apiClient.get<DashboardData>(path, { timeoutMs, unwrapData: false })
}

export function getLiveDashboard() {
  return getRawDashboard('/dashboard-data/live')
}

export function getDashboard() {
  return getRawDashboard('/dashboard-data')
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
