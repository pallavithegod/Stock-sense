import { APP_NAME, API_BASE_URL } from '../config/env'
import type { ReactNode } from 'react'

const navItems = ['Dashboard', 'Stocks', 'Portfolio', 'Predictions', 'News', 'Research']

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-white/10 bg-slate-950/95 px-5 py-6 lg:block">
        <div>
          <div className="text-lg font-semibold text-white">{APP_NAME}</div>
          <div className="mt-1 text-xs uppercase text-cyan-300">Market intelligence desk</div>
        </div>

        <nav className="mt-8 space-y-1">
          {navItems.map((item, index) => (
            <button
              className={`w-full rounded-md px-3 py-2 text-left text-sm ${
                index === 0
                  ? 'bg-cyan-400/10 text-cyan-200'
                  : 'text-slate-400 hover:bg-white/[0.04] hover:text-white'
              }`}
              key={item}
              type="button"
            >
              {item}
            </button>
          ))}
        </nav>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-10 border-b border-white/10 bg-slate-950/90 px-5 py-4 backdrop-blur">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="text-sm font-medium text-cyan-200">Frontend migration phase 1</div>
              <h1 className="text-xl font-semibold text-white">Dashboard Shell</h1>
            </div>
            <div className="rounded-md border border-white/10 bg-white/[0.04] px-3 py-2 text-xs text-slate-400">
              API: <span className="text-slate-200">{API_BASE_URL}</span>
            </div>
          </div>
        </header>

        <main className="px-5 py-6">{children}</main>
      </div>
    </div>
  )
}
