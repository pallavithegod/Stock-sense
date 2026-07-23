import { APP_NAME } from '../config/env'
import type { ReactNode } from 'react'
import type { AppPage } from '../types/navigation'

const navItems: Array<{ id: AppPage; label: string }> = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'stocks', label: 'Stocks' },
  { id: 'portfolio', label: 'Portfolio' },
  { id: 'predictions', label: 'Predictions' },
  { id: 'news', label: 'News' },
  { id: 'research', label: 'Research' },
]

type AppShellProps = {
  activePage: AppPage
  children: ReactNode
  onPageChange: (page: AppPage) => void
}

export function AppShell({ activePage, children, onPageChange }: AppShellProps) {
  const currentPageLabel = navItems.find((item) => item.id === activePage)?.label ?? APP_NAME

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-white/10 bg-slate-950/95 px-5 py-6 lg:block">
        <div>
          <div className="text-lg font-semibold text-white">{APP_NAME}</div>
          <div className="mt-1 text-xs uppercase text-cyan-300">Market intelligence desk</div>
        </div>

        <nav className="mt-8 space-y-1">
          {navItems.map((item) => (
            <button
              className={`w-full rounded-md px-3 py-2 text-left text-sm ${
                activePage === item.id
                  ? 'bg-cyan-400/10 text-cyan-200'
                  : 'text-slate-400 hover:bg-white/[0.04] hover:text-white'
              }`}
              key={item.id}
              onClick={() => onPageChange(item.id)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </nav>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-10 border-b border-white/10 bg-slate-950/90 px-5 py-4 backdrop-blur">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="text-sm font-medium text-cyan-200">{APP_NAME}</div>
              <h1 className="text-xl font-semibold text-white">{currentPageLabel}</h1>
            </div>
          </div>
        </header>

        <main className="px-5 py-6">{children}</main>
      </div>
    </div>
  )
}
