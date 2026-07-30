import type { AppPage } from '../types/navigation'

export type AppRoute = {
  id: AppPage
  label: string
  path: string
}

export const appRoutes: AppRoute[] = [
  { id: 'dashboard', label: 'Dashboard', path: '/' },
  { id: 'stocks', label: 'Stocks', path: '/stocks' },
  { id: 'portfolio', label: 'Portfolio', path: '/portfolio' },
  { id: 'predictions', label: 'Predictions', path: '/predictions' },
  { id: 'news', label: 'News', path: '/news' },
  { id: 'research', label: 'Research', path: '/research' },
]

const routeByPath = new Map(appRoutes.map((route) => [route.path, route]))
const routeByPage = new Map(appRoutes.map((route) => [route.id, route]))

export function pageFromPath(pathname: string): AppPage {
  return routeByPath.get(normalizePath(pathname))?.id ?? 'dashboard'
}

export function pathForPage(page: AppPage): string {
  return routeByPage.get(page)?.path ?? '/'
}

export function labelForPage(page: AppPage): string {
  return routeByPage.get(page)?.label ?? 'Dashboard'
}

function normalizePath(pathname: string) {
  const normalized = pathname.replace(/\/+$/g, '')
  return normalized || '/'
}
