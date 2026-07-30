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
  let timedOut = false
  const timeout = window.setTimeout(() => {
    timedOut = true
    controller.abort()
  }, options.timeoutMs ?? 15000)
  const abortFromCaller = () => controller.abort()
  options.signal?.addEventListener('abort', abortFromCaller, { once: true })

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      signal: controller.signal,
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

    if (options.unwrapData !== false && payload && typeof payload === 'object' && 'data' in payload) {
      return payload.data as T
    }

    return payload as T
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error(timedOut ? 'Request timed out. The Flask API took too long to respond.' : 'Request canceled.', {
        cause: error,
      })
    }
    throw error
  } finally {
    options.signal?.removeEventListener('abort', abortFromCaller)
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
