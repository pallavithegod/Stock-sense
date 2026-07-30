import { APP_NAME } from '../config/env'
import type { MouseEvent, ReactNode } from 'react'
import { appRoutes, labelForPage, pathForPage } from '../router/routes'
import type { AppPage } from '../types/navigation'

type AppShellProps = {
  activePage: AppPage
  children: ReactNode
  onPageChange: (page: AppPage) => void
}

export function AppShell({ activePage, children, onPageChange }: AppShellProps) {
  const currentPageLabel = labelForPage(activePage)

  function handleNavigate(event: MouseEvent<HTMLAnchorElement>, page: AppPage) {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return
    event.preventDefault()
    onPageChange(page)
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-white/10 bg-slate-950/95 px-5 py-6 lg:block">
        <div>
          <div className="text-lg font-semibold text-white">{APP_NAME}</div>
          <div className="mt-1 text-xs uppercase text-cyan-300">Market intelligence desk</div>
        </div>

        <nav className="mt-8 space-y-1">
          {appRoutes.map((item) => (
            <a
              aria-current={activePage === item.id ? 'page' : undefined}
              className={`block w-full rounded-md px-3 py-2 text-left text-sm ${
                activePage === item.id
                  ? 'bg-cyan-400/10 text-cyan-200'
                  : 'text-slate-400 hover:bg-white/[0.04] hover:text-white'
              }`}
              href={pathForPage(item.id)}
              key={item.id}
              onClick={(event) => handleNavigate(event, item.id)}
            >
              {item.label}
            </a>
          ))}
        </nav>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-10 border-b border-white/10 bg-slate-950/90 px-5 py-4 backdrop-blur">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="text-sm font-medium text-cyan-200">{APP_NAME}</div>
              <h1 className="text-xl font-semibold text-white">{currentPageLabel}</h1>
            </div>
          </div>
          <nav aria-label="Primary" className="mt-4 flex gap-2 overflow-x-auto pb-1 lg:hidden">
            {appRoutes.map((item) => (
              <a
                aria-current={activePage === item.id ? 'page' : undefined}
                className={`shrink-0 rounded-md border px-3 py-2 text-sm ${
                  activePage === item.id
                    ? 'border-cyan-300/40 bg-cyan-400/10 text-cyan-100'
                    : 'border-white/10 text-slate-300'
                }`}
                href={pathForPage(item.id)}
                key={item.id}
                onClick={(event) => handleNavigate(event, item.id)}
              >
                {item.label}
              </a>
            ))}
          </nav>
        </header>

        <main className="px-5 py-6">{children}</main>
        <footer className="border-t border-white/10 px-5 py-4 text-xs leading-5 text-slate-500">
          StockSense is a demo research tool. Signals, forecasts, and portfolio metrics are not financial advice.
        </footer>
      </div>
    </div>
  )
}
