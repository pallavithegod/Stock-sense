import { useState } from 'react'
import type { MouseEvent, ReactNode } from 'react'
import { appRoutes, labelForPage, pathForPage } from '../router/routes'
import type { AppPage } from '../types/navigation'
import { useAuth } from '../auth/useAuth'

type AppShellProps = {
  activePage: AppPage
  children: ReactNode
  onPageChange: (page: AppPage) => void
}

export function AppShell({ activePage, children, onPageChange }: AppShellProps) {
  const currentPageLabel = labelForPage(activePage)
  const { user, signOut } = useAuth()
  const [authActionError, setAuthActionError] = useState<string | null>(null)

  async function handleSignOut() {
    setAuthActionError(null)
    try {
      await signOut()
    } catch (error) {
      setAuthActionError(error instanceof Error ? error.message : 'Sign out failed.')
    }
  }

  function handleNavigate(event: MouseEvent<HTMLAnchorElement>, page: AppPage) {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return
    event.preventDefault()
    onPageChange(page)
  }

  return (
    <div className="stocksense-app">
      <header className="stocksense-header">
        <div className="stocksense-brand">
          <span className="stocksense-atom" aria-hidden="true" />
          <span className="stocksense-brand-text">StockSense</span>
          <span className="stocksense-live"><span /> LIVE NSE/BSE</span>
        </div>

        <nav aria-label="Primary" className="stocksense-top-nav">
          {appRoutes.map((item) => (
            <a
              aria-current={activePage === item.id ? 'page' : undefined}
              className={activePage === item.id ? 'active' : ''}
              href={pathForPage(item.id)}
              key={item.id}
              onClick={(event) => handleNavigate(event, item.id)}
            >
              {item.label}
            </a>
          ))}
        </nav>

        <div className="stocksense-header-tools">
          <label className="stocksense-search">
            <span aria-hidden="true">Q</span>
            <input placeholder="Search stocks, signals, portfolio" />
          </label>
          <button className="stocksense-icon-btn" type="button" aria-label="Theme palette">TM</button>
          {authActionError ? <span role="alert" className="text-xs text-rose-300">{authActionError}</span> : null}
          <button
            className="stocksense-avatar"
            type="button"
            aria-label={user ? 'Sign out' : 'Sign in'}
            onClick={() => {
              if (user) void handleSignOut()
              else onPageChange('portfolio')
            }}
            title={user?.email ?? 'Sign in'}
          >
            {user ? 'Out' : 'In'}
          </button>
        </div>
      </header>

      <div className="stocksense-main">
        <aside className="stocksense-sidebar">
          <div className="stocksense-sidebar-title">
            <span className="stocksense-atom small" aria-hidden="true" />
            <div>
              <strong>StockSense</strong>
              <span>Market intelligence desk</span>
            </div>
          </div>

          <div className="stocksense-side-card accent-yellow">
            <div className="side-card-head">
              <b>Dashboard</b>
              <span className="pill green">AUTO</span>
            </div>
            <div className="side-row"><span>Total Return</span><b id="portVal">--</b></div>
            <div className="side-row"><span>Model Accuracy</span><b className="cyan">Live</b></div>
          </div>

          <div className="stocksense-side-card mini-chart-card">
            <div className="side-card-head">
              <b>AI Index</b>
              <span className="green">+--</span>
            </div>
            <div className="mini-spark" aria-hidden="true">
              <span style={{ height: '28%' }} />
              <span style={{ height: '45%' }} />
              <span style={{ height: '36%' }} />
              <span style={{ height: '64%' }} />
              <span style={{ height: '52%' }} />
              <span style={{ height: '78%' }} />
              <span style={{ height: '68%' }} />
            </div>
            <div className="side-row"><span>Session</span><b>SYNC</b></div>
          </div>

          <div className="stocksense-side-section">
            <div className="side-card-head"><b>AI Performance</b><span>--</span></div>
            <div className="side-row"><span>Total Predictions</span><b>--</b></div>
            <div className="side-row"><span>Model Accuracy</span><b className="cyan">--</b></div>
            <div className="side-row"><span>Commodities Signal</span><b className="green">--</b></div>
          </div>

          <div className="stocksense-side-section">
            <div className="side-card-head"><b>Market Snapshot</b><span className="pill">NOW</span></div>
            <div className="side-row"><span>Momentum Score</span><b className="green">--</b></div>
            <div className="side-row"><span>Trend Divergence</span><b className="cyan">--</b></div>
            <div className="side-row"><span>AI Self-Learning</span><b className="pill cyan">Cycle --</b></div>
          </div>

          <div className="sync-card">
            <span>System Sync</span>
            <div><i /></div>
          </div>

          <nav aria-label="Primary" className="stocksense-mobile-nav">
            {appRoutes.map((item) => (
              <a
                aria-current={activePage === item.id ? 'page' : undefined}
                className={activePage === item.id ? 'active' : ''}
                href={pathForPage(item.id)}
                key={item.id}
                onClick={(event) => handleNavigate(event, item.id)}
              >
                {item.label}
              </a>
            ))}
          </nav>
        </aside>

        <section className="stocksense-workspace">
          <div className="stocksense-topbar">
            <div>
              <span className="topbar-kicker">StockSense Terminal</span>
              <h1>{currentPageLabel}</h1>
            </div>
          </div>
          <main className="stocksense-content">{children}</main>
        </section>
      </div>
    </div>
  )
}
