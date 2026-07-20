import { API_BASE_URL } from '../config/env'
import type { ApiEnvelope, RequestOptions } from '../types/api'

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE'

async function request<T>(
  path: string,
  method: HttpMethod,
  body?: unknown,
  options: RequestOptions = {},
): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), options.timeoutMs ?? 15000)
  const signal = options.signal ?? controller.signal

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      signal,
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    })

    const payload = (await response.json().catch(() => null)) as ApiEnvelope<T> | T | null

    if (!response.ok) {
      const message =
        payload && typeof payload === 'object' && 'error' in payload && payload.error
          ? String(payload.error)
          : `Request failed with ${response.status}`
      throw new Error(message)
    }

    if (payload && typeof payload === 'object' && 'data' in payload) {
      return payload.data as T
    }

    return payload as T
  } finally {
    window.clearTimeout(timeout)
  }
}

export const apiClient = {
  get: <T>(path: string, options?: RequestOptions) => request<T>(path, 'GET', undefined, options),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, 'POST', body, options),
  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, 'PUT', body, options),
  delete: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, 'DELETE', undefined, options),
}
