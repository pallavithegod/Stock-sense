import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  invalidateQueries,
  readQueryCache,
  serializeQueryKey,
  subscribeQuery,
  writeQueryCache,
} from './queryClient'
import type { QueryKey } from './queryClient'

type QueryConfig<T> = {
  enabled?: boolean
  key: QueryKey
  queryFn: (signal: AbortSignal) => Promise<T>
  retry?: number
  retryDelayMs?: number
  staleMs?: number
}

type QueryState<T> = {
  data?: T
  error: string | null
  isStale: boolean
  loading: boolean
  refreshing: boolean
}

export function useQuery<T>({
  enabled = true,
  key,
  queryFn,
  retry = 1,
  retryDelayMs = 500,
  staleMs = 30_000,
}: QueryConfig<T>) {
  const keyString = serializeQueryKey(key)
  const [refreshIndex, setRefreshIndex] = useState(0)
  const [cacheSignal, setCacheSignal] = useState(0)
  const [state, setState] = useState<QueryState<T>>(() => {
    const cached = readQueryCache<T>(key)
    return {
      data: cached?.data,
      error: cached?.error ?? null,
      isStale: cached ? Date.now() - cached.updatedAt > staleMs : false,
      loading: enabled && !cached?.data,
      refreshing: false,
    }
  })

  useEffect(() => subscribeQuery(keyString, () => setCacheSignal((value) => value + 1)), [keyString])

  useEffect(() => {
    const controller = new AbortController()
    let active = true
    const startTimer = window.setTimeout(() => {
      if (!active) return
      if (!enabled) {
        setState((current) => ({ ...current, loading: false, refreshing: false }))
        return
      }

      const cached = readQueryCache<T>(keyString)
      const hasFreshCache = cached?.data !== undefined && Date.now() - cached.updatedAt <= staleMs
      if (hasFreshCache && refreshIndex === 0) {
        setState({
          data: cached.data,
          error: cached.error ?? null,
          isStale: false,
          loading: false,
          refreshing: false,
        })
        return
      }

        setState((current) => {
          const existingData = cached?.data ?? current.data
          return {
            data: existingData,
            error: null,
            isStale: Boolean(existingData),
            loading: !existingData,
            refreshing: Boolean(existingData),
          }
        })

      fetchWithRetry(() => queryFn(controller.signal), retry, retryDelayMs)
        .then((data) => {
          if (!active) return
          writeQueryCache<T>(keyString, { data, updatedAt: Date.now() })
          setState({ data, error: null, isStale: false, loading: false, refreshing: false })
        })
        .catch((error: unknown) => {
          if (!active || controller.signal.aborted) return
          const message = error instanceof Error ? error.message : 'Request failed.'
          setState((current) => {
            const staleData = readQueryCache<T>(keyString)?.data ?? current.data
            writeQueryCache<T>(keyString, {
              data: staleData,
              error: message,
              updatedAt: staleData === undefined ? 0 : Date.now() - staleMs - 1,
            })
            return {
              data: staleData,
              error: message,
              isStale: staleData !== undefined,
              loading: false,
              refreshing: false,
            }
          })
        })
    }, 0)

    return () => {
      active = false
      window.clearTimeout(startTimer)
      controller.abort()
    }
  }, [cacheSignal, enabled, keyString, queryFn, refreshIndex, retry, retryDelayMs, staleMs])

  const refetch = useCallback(() => setRefreshIndex((value) => value + 1), [])

  return useMemo(
    () => ({
      ...state,
      refetch,
    }),
    [refetch, state],
  )
}

export function useMutation<TPayload, TResult>({
  mutationFn,
  onSuccess,
}: {
  mutationFn: (payload: TPayload, signal: AbortSignal) => Promise<TResult>
  onSuccess?: (result: TResult) => void
}) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const mutate = useCallback(
    async (payload: TPayload) => {
      const controller = new AbortController()
      setLoading(true)
      setError(null)
      try {
        const result = await mutationFn(payload, controller.signal)
        onSuccess?.(result)
        return result
      } catch (caught) {
        const message = caught instanceof Error ? caught.message : 'Request failed.'
        setError(message)
        throw caught
      } finally {
        setLoading(false)
      }
    },
    [mutationFn, onSuccess],
  )

  return { error, loading, mutate }
}

export { invalidateQueries }

async function fetchWithRetry<T>(
  queryFn: () => Promise<T>,
  retry: number,
  retryDelayMs: number,
): Promise<T> {
  let attempt = 0
  let lastError: unknown
  while (attempt <= retry) {
    try {
      return await queryFn()
    } catch (error) {
      lastError = error
      if (attempt >= retry) break
      await sleep(retryDelayMs * (attempt + 1))
      attempt += 1
    }
  }
  throw lastError
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}
