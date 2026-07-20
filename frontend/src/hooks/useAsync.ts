import { useEffect, useState } from 'react'
import type { DependencyList } from 'react'

type AsyncState<T> = {
  data: T | null
  error: string | null
  loading: boolean
}

export function useAsync<T>(factory: () => Promise<T>, deps: DependencyList) {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    error: null,
    loading: true,
  })

  useEffect(() => {
    let active = true

    factory()
      .then((data) => {
        if (active) setState({ data, error: null, loading: false })
      })
      .catch((error: unknown) => {
        if (active) {
          setState({
            data: null,
            error: error instanceof Error ? error.message : 'Request failed',
            loading: false,
          })
        }
      })

    return () => {
      active = false
    }
    // This hook intentionally accepts a caller-owned dependency list.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return state
}
