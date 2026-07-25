import { useEffect, useState } from 'react'
import type { DependencyList } from 'react'

type AsyncState<T> = {
  data: T | null
  error: string | null
  loading: boolean
}

type AsyncOptions = {
  retries?: number
  retryDelayMs?: number
}

export function useAsync<T>(
  factory: () => Promise<T>,
  deps: DependencyList,
  options: AsyncOptions = {},
) {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    error: null,
    loading: true,
  })

  useEffect(() => {
    let active = true
    let retryTimer: number | undefined
    const retries = Math.max(0, options.retries ?? 2)
    const retryDelayMs = Math.max(250, options.retryDelayMs ?? 1000)

    const run = (attempt: number) => {
      factory()
        .then((data) => {
          if (active) setState({ data, error: null, loading: false })
        })
        .catch((error: unknown) => {
          if (!active) return
          if (attempt < retries) {
            retryTimer = window.setTimeout(
              () => run(attempt + 1),
              retryDelayMs * (attempt + 1),
            )
            return
          }
          setState({
            data: null,
            error: error instanceof Error ? error.message : 'Request failed',
            loading: false,
          })
        })
    }

    setState((current) => ({ ...current, error: null, loading: true }))
    run(0)

    return () => {
      active = false
      if (retryTimer !== undefined) window.clearTimeout(retryTimer)
    }
    // This hook intentionally accepts a caller-owned dependency list.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return state
}
