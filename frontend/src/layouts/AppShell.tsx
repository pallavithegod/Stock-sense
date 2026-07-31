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
    <div className="nexus-app">
      <header className="nexus-header">
        <div className="nexus-brand">
          <span className="nexus-atom" aria-hidden="true" />
          <span className="nexus-brand-text">NEXUS AI <b>QUANTUM</b></span>
          <span className="nexus-live"><span /> LIVE NSE/BSE</span>
        </div>

        <nav aria-label="Primary" className="nexus-top-nav">
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

        <div className="nexus-header-tools">
          <label className="nexus-search">
            <span aria-hidden="true">Q</span>
            <input placeholder="Search stocks, signals, portfolio" />
          </label>
          <button className="nexus-icon-btn" type="button" aria-label="Theme palette">TM</button>
          <button className="nexus-avatar" type="button" aria-label="User profile">AI</button>
        </div>
      </header>

      <div className="nexus-main">
        <aside className="nexus-sidebar">
          <div className="nexus-sidebar-title">
            <span className="nexus-atom small" aria-hidden="true" />
            <div>
              <strong>NEXUS AI</strong>
              <span>Market intelligence desk</span>
            </div>
          </div>

          <div className="nexus-side-card accent-yellow">
            <div className="side-card-head">
              <b>Dashboard</b>
              <span className="pill green">AUTO</span>
            </div>
            <div className="side-row"><span>Total Return</span><b id="portVal">--</b></div>
            <div className="side-row"><span>Model Accuracy</span><b className="cyan">Live</b></div>
          </div>

          <div className="nexus-side-card mini-chart-card">
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

          <div className="nexus-side-section">
            <div className="side-card-head"><b>AI Performance</b><span>--</span></div>
            <div className="side-row"><span>Total Predictions</span><b>--</b></div>
            <div className="side-row"><span>Model Accuracy</span><b className="cyan">--</b></div>
            <div className="side-row"><span>Commodities Signal</span><b className="green">--</b></div>
          </div>

          <div className="nexus-side-section">
            <div className="side-card-head"><b>Market Snapshot</b><span className="pill">NOW</span></div>
            <div className="side-row"><span>Momentum Score</span><b className="green">--</b></div>
            <div className="side-row"><span>Trend Divergence</span><b className="cyan">--</b></div>
            <div className="side-row"><span>AI Self-Learning</span><b className="pill cyan">Cycle --</b></div>
          </div>

          <div className="sync-card">
            <span>System Sync</span>
            <div><i /></div>
          </div>

          <div className="nexus-mobile-nav">
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
          </div>
        </aside>

        <section className="nexus-workspace">
          <div className="nexus-topbar">
            <div>
              <span className="topbar-kicker">NEXUS TERMINAL</span>
              <h1>{currentPageLabel}</h1>
            </div>
            <div className="topbar-right">
              <span className="topbar-chip">127.0.0.1:5000</span>
              <span className="topbar-chip teal">API LINK</span>
            </div>
          </div>
          <main className="nexus-content">{children}</main>
        </section>
      </div>
    </div>
  )
}
