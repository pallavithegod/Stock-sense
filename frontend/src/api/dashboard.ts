import { apiClient } from './client'
import { API_BASE_URL } from '../config/env'
import type { DashboardData } from '../types/dashboard'

async function getRawDashboard(path: string, timeoutMs = 20000) {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
      },
      signal: controller.signal,
    })
    const payload = await response.json().catch(() => null)
    if (!response.ok) {
      const message =
        payload && typeof payload === 'object' && 'error' in payload
          ? String(payload.error)
          : `Request failed with ${response.status}`
      throw new Error(message)
    }
    return payload as DashboardData
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('Request timed out. The Flask API took too long to respond.', {
        cause: error,
      })
    }
    throw error
  } finally {
    window.clearTimeout(timeout)
  }
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
