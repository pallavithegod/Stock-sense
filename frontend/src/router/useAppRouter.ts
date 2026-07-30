import { useCallback, useEffect, useState } from 'react'
import type { AppPage } from '../types/navigation'
import { pageFromPath, pathForPage } from './routes'

function currentPage() {
  return pageFromPath(window.location.pathname)
}

export function useAppRouter() {
  const [activePage, setActivePage] = useState<AppPage>(() => currentPage())

  useEffect(() => {
    const onPopState = () => setActivePage(currentPage())
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  const navigate = useCallback((page: AppPage) => {
    const path = pathForPage(page)
    if (window.location.pathname !== path) {
      window.history.pushState(null, '', path)
    }
    setActivePage(page)
  }, [])

  return { activePage, navigate }
}
