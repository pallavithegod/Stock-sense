import { useState } from 'react'
import { getDashboardSnapshot } from '../api/dashboard'
import { MetricCard } from '../components/MetricCard'
import { SectionHeader } from '../components/SectionHeader'
import { StatePanel } from '../components/StatePanel'
import { useAsync } from '../hooks/useAsync'
import { normalizeDashboard } from '../utils/dashboardAdapter'
import { cx, formatNumber, formatPercent } from '../utils/format'

function toneForChange(value?: number) {
  if (value === undefined) return 'text-slate-400'
  return value >= 0 ? 'text-emerald-300' : 'text-rose-300'
}

export function DashboardPage() {
  const [refreshKey, setRefreshKey] = useState(0)
  const { data, error, loading } = useAsync(() => getDashboardSnapshot(), [refreshKey])
  const dashboard = normalizeDashboard(data)

  return (
    <div className="mx-auto max-w-7xl">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="text-sm font-medium uppercase text-cyan-300">Live command center</div>
          <h1 className="mt-1 text-2xl font-semibold text-white">Market Dashboard</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
            React now consumes the existing Flask dashboard APIs. This page intentionally keeps
            business logic in the backend and focuses on a cleaner presentation layer.
          </p>
        </div>
        <button
          className="h-10 rounded-md border border-cyan-300/30 bg-cyan-300/10 px-4 text-sm font-medium text-cyan-100 hover:bg-cyan-300/15"
          onClick={() => setRefreshKey((value) => value + 1)}
          type="button"
        >
          Refresh
        </button>
      </div>

      {error ? (
        <div className="mb-5 rounded-lg border border-amber-300/30 bg-amber-300/10 p-4 text-sm text-amber-100">
          Flask API is not reachable yet: {error}. Run `python app.py` in the project root, then
          refresh this page.
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {dashboard.metrics.map((metric) => (
          <MetricCard key={metric.label} metric={metric} />
        ))}
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1.35fr_0.9fr]">
        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <SectionHeader
            action={
              <div className="rounded-md bg-white/[0.04] px-2 py-1 text-xs text-slate-400">
                {loading ? 'Syncing' : dashboard.source ?? 'Flask API'}
              </div>
            }
            eyebrow="Market"
            title="Indices"
          />

          <div className="mt-4 overflow-hidden rounded-lg border border-white/10">
            <table className="w-full table-fixed text-left text-sm">
              <thead className="bg-white/[0.04] text-xs uppercase text-slate-400">
                <tr>
                  <th className="px-3 py-3">Index</th>
                  <th className="px-3 py-3 text-right">Price</th>
                  <th className="px-3 py-3 text-right">Change</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10">
                {dashboard.indices.length ? (
                  dashboard.indices.map((index) => (
                    <tr key={`${index.name}-${index.symbol ?? ''}`}>
                      <td className="px-3 py-3">
                        <div className="font-medium text-white">{index.name}</div>
                        <div className="text-xs text-slate-500">{index.symbol}</div>
                      </td>
                      <td className="px-3 py-3 text-right text-slate-200">
                        {formatNumber(index.price)}
                      </td>
                      <td className={cx('px-3 py-3 text-right', toneForChange(index.changePercent))}>
                        {formatPercent(index.changePercent)}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td className="px-3 py-8 text-center text-slate-400" colSpan={3}>
                      {loading ? 'Loading index data...' : 'No index data available yet.'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <SectionHeader eyebrow="Signals" title="Top Opportunities" />
          <div className="mt-4 space-y-3">
            {dashboard.signals.length ? (
              dashboard.signals.map((signal) => (
                <div
                  className="rounded-md border border-white/10 bg-slate-950/50 p-3"
                  key={`${signal.symbol}-${signal.signal ?? ''}`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="font-medium text-white">{signal.symbol}</div>
                    <div className="rounded bg-cyan-300/10 px-2 py-1 text-xs text-cyan-200">
                      {signal.signal ?? 'WATCH'}
                    </div>
                  </div>
                  <div className="mt-3 flex items-center justify-between text-sm text-slate-400">
                    <span>{formatNumber(signal.price)}</span>
                    <span>{formatPercent(signal.changePercent)}</span>
                    <span>{formatNumber(signal.confidence)} conf</span>
                  </div>
                </div>
              ))
            ) : (
              <StatePanel
                description={loading ? 'Signals are loading from Flask.' : 'No signals are available yet.'}
                title="No opportunities"
              />
            )}
          </div>
        </section>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <SectionHeader eyebrow="Risk" title="Alerts" />
          <div className="mt-4 space-y-3">
            {dashboard.alerts.length ? (
              dashboard.alerts.map((alert) => (
                <div className="rounded-md border border-white/10 p-3" key={alert.title}>
                  <div className="text-sm font-medium text-white">{alert.title}</div>
                  <div className="mt-1 text-sm text-slate-400">{alert.detail ?? alert.symbol}</div>
                </div>
              ))
            ) : (
              <StatePanel description="No active alerts in the dashboard payload." title="Clear" />
            )}
          </div>
        </section>

        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <SectionHeader eyebrow="News" title="Market Feed" />
          <div className="mt-4 space-y-3">
            {dashboard.news.length ? (
              dashboard.news.map((item) => (
                <div className="rounded-md border border-white/10 p-3" key={item.title}>
                  <div className="text-sm font-medium text-white">{item.title}</div>
                  <div className="mt-1 text-sm text-slate-400">{item.detail}</div>
                </div>
              ))
            ) : (
              <StatePanel description="News will appear here once the Flask feed responds." title="No feed" />
            )}
          </div>
        </section>
      </div>

      <section className="mt-6 rounded-lg border border-white/10 bg-white/[0.04] p-5">
        <SectionHeader eyebrow="Debug" title="Dashboard API payload" />
        <pre className="mt-4 max-h-96 overflow-auto rounded-md bg-slate-950 p-4 text-xs leading-6 text-slate-300">
          {loading ? 'Loading...' : JSON.stringify(dashboard.raw, null, 2)}
        </pre>
      </section>
    </div>
  )
}
