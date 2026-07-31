import { useCallback } from 'react'
import { getDashboardSnapshot } from '../api/dashboard'
import { IconButton } from '../components/IconButton'
import { MetricCard } from '../components/MetricCard'
import { SectionHeader } from '../components/SectionHeader'
import { StatePanel } from '../components/StatePanel'
import { useQuery } from '../query/useQuery'
import { normalizeDashboard } from '../utils/dashboardAdapter'
import { cx, formatNumber, formatPercent } from '../utils/format'

function toneForChange(value?: number) {
  if (value === undefined) return 'muted'
  return value >= 0 ? 'positive' : 'negative'
}

function displayChange(value?: number) {
  return value === undefined ? '--' : formatPercent(value)
}

export function DashboardPage() {
  const loadDashboard = useCallback((signal: AbortSignal) => getDashboardSnapshot({ signal }), [])
  const { data, error, isStale, loading, refetch, refreshing } = useQuery({
    key: ['dashboard', 'snapshot'],
    queryFn: loadDashboard,
    retry: 1,
    staleMs: 30_000,
  })
  const dashboard = normalizeDashboard(data)
  const featuredIndex = dashboard.indices[0]
  const secondaryIndex = dashboard.indices[1]
  const source = dashboard.source ?? (loading || refreshing ? 'Syncing' : 'Live')

  return (
    <div className="stocksense-dashboard-page">
      <div className="dashboard-command-row">
        <section className="command-panel command-panel-hero">
          <div className="command-grid-bg" aria-hidden="true" />
          <div className="panel-overline">Live command center</div>
          <div className="hero-command-content">
            <div>
              <h2>Market Dashboard</h2>
              <p>Real-time portfolio intelligence, index flow, model signals, alerts, and news compressed into a professional trading desk.</p>
            </div>
            <IconButton disabled={refreshing} label="Refresh dashboard" onClick={refetch} tone="primary">
              {refreshing ? 'Syncing' : 'Refresh'}
            </IconButton>
          </div>
          <div className="command-status-strip">
            <div>
              <span>API Source</span>
              <b>{source}</b>
            </div>
            <div>
              <span>Primary Index</span>
              <b>{featuredIndex?.name ?? '--'}</b>
            </div>
            <div>
              <span>Last Update</span>
              <b>{dashboard.lastUpdate ?? '--'}</b>
            </div>
          </div>
        </section>

        <section className="command-panel market-pulse-panel">
          <SectionHeader eyebrow="NSE/BSE" title="Market pulse" />
          <div className="pulse-score">
            <span>{featuredIndex ? formatNumber(featuredIndex.price) : '--'}</span>
            <b className={toneForChange(featuredIndex?.changePercent)}>
              {displayChange(featuredIndex?.changePercent)}
            </b>
          </div>
          <div className="pulse-rail" aria-hidden="true">
            <span style={{ width: featuredIndex && (featuredIndex.changePercent ?? 0) >= 0 ? '72%' : '38%' }} />
          </div>
          <div className="pulse-secondary">
            <span>{secondaryIndex?.name ?? 'Second index'}</span>
            <b className={toneForChange(secondaryIndex?.changePercent)}>
              {displayChange(secondaryIndex?.changePercent)}
            </b>
          </div>
        </section>
      </div>

      {error ? (
        <div className="stocksense-alert-panel">
          Market data is not reachable yet: {error}.{' '}
          {isStale ? 'Showing the last successful snapshot.' : 'Start the backend, then refresh this page.'}
        </div>
      ) : null}

      <div className="stocksense-metrics-grid">
        {dashboard.metrics.map((metric) => (
          <MetricCard key={metric.label} metric={metric} />
        ))}
      </div>

      <div className="dashboard-grid-main">
        <section className="command-panel market-board-panel">
          <SectionHeader
            action={<div className="data-badge">{loading || refreshing ? 'SYNCING' : source.toUpperCase()}</div>}
            eyebrow="Market"
            title="Indices board"
          />

          <div className="index-tile-grid">
            {dashboard.indices.length ? (
              dashboard.indices.slice(0, 4).map((index) => (
                <div className="index-tile" key={`${index.name}-${index.symbol ?? ''}`}>
                  <div>
                    <strong>{index.name}</strong>
                    <span>{index.symbol ?? 'INDEX'}</span>
                  </div>
                  <b>{formatNumber(index.price)}</b>
                  <em className={toneForChange(index.changePercent)}>{displayChange(index.changePercent)}</em>
                </div>
              ))
            ) : (
              <StatePanel description={loading || refreshing ? 'Loading index data.' : 'No index data available yet.'} title="No indices" />
            )}
          </div>

          <div className="stocksense-table-wrap">
            <table>
              <caption className="sr-only">Market index prices and percentage change</caption>
              <thead>
                <tr>
                  <th>Index</th>
                  <th>Price</th>
                  <th>Change</th>
                </tr>
              </thead>
              <tbody>
                {dashboard.indices.length ? (
                  dashboard.indices.map((index) => (
                    <tr key={`${index.name}-${index.symbol ?? ''}`}>
                      <td>
                        <div className="table-primary">{index.name}</div>
                        <div className="table-secondary">{index.symbol}</div>
                      </td>
                      <td className="numeric">{formatNumber(index.price)}</td>
                      <td className={cx('numeric', toneForChange(index.changePercent))}>
                        {displayChange(index.changePercent)}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td className="empty-cell" colSpan={3}>
                      {loading || refreshing ? 'Loading index data...' : 'No index data available yet.'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="command-panel signal-radar-panel">
          <SectionHeader eyebrow="Signals" title="AI opportunity radar" />
          <div className="radar-stage" aria-hidden="true">
            <div className="radar-ring ring-one" />
            <div className="radar-ring ring-two" />
            <div className="radar-sweep" />
            {dashboard.signals.slice(0, 5).map((signal, index) => (
              <span
                className="radar-dot"
                key={`${signal.symbol}-${index}`}
                style={{
                  left: `${22 + index * 13}%`,
                  top: `${30 + (index % 3) * 15}%`,
                }}
              />
            ))}
          </div>

          <div className="opportunity-list">
            {dashboard.signals.length ? (
              dashboard.signals.slice(0, 6).map((signal) => (
                <div className="opportunity-row" key={`${signal.symbol}-${signal.signal ?? ''}`}>
                  <div>
                    <strong>{signal.symbol}</strong>
                    <span>{signal.signal ?? 'WATCH'}</span>
                  </div>
                  <div>
                    <b>{formatNumber(signal.price)}</b>
                    <em className={toneForChange(signal.changePercent)}>{displayChange(signal.changePercent)}</em>
                  </div>
                  <small>{formatNumber(signal.confidence)} conf</small>
                </div>
              ))
            ) : (
              <StatePanel description={loading ? 'Signals are loading.' : 'No signals are available yet.'} title="No opportunities" />
            )}
          </div>
        </section>
      </div>

      <div className="dashboard-grid-secondary">
        <section className="command-panel ai-allocation-panel">
          <SectionHeader eyebrow="AI" title="Allocation intelligence" />
          <div className="allocation-body">
            <div className="allocation-donut" aria-label="AI allocation mix">
              <span>AI</span>
            </div>
            <div className="allocation-legend">
              <div><i className="legend-green" />Core holdings <b>54%</b></div>
              <div><i className="legend-cyan" />Momentum <b>28%</b></div>
              <div><i className="legend-yellow" />Cash buffer <b>18%</b></div>
            </div>
          </div>
        </section>

        <section className="command-panel">
          <SectionHeader eyebrow="Risk" title="Alerts" />
          <div className="stack-list">
            {dashboard.alerts.length ? (
              dashboard.alerts.map((alert) => (
                <div className="stack-item" key={alert.title}>
                  <div className="stack-item-title">{alert.title}</div>
                  <p>{alert.detail ?? alert.symbol}</p>
                </div>
              ))
            ) : (
              <StatePanel description="No active alerts right now." title="Clear" />
            )}
          </div>
        </section>

        <section className="command-panel">
          <SectionHeader eyebrow="News" title="Market feed" />
          <div className="stack-list">
            {dashboard.news.length ? (
              dashboard.news.map((item) => (
                <div className="stack-item" key={item.title}>
                  <div className="stack-item-title">{item.title}</div>
                  <p>{item.detail}</p>
                </div>
              ))
            ) : (
              <StatePanel description="News will appear here once the feed responds." title="No feed" />
            )}
          </div>
        </section>
      </div>
    </div>
  )
}
