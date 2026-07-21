import { useMemo, useState } from 'react'
import { getPredictionIntelligence, getPredictions } from '../api/predictions'
import { SectionHeader } from '../components/SectionHeader'
import { StatePanel } from '../components/StatePanel'
import { useAsync } from '../hooks/useAsync'
import { normalizePredictionRow } from '../utils/predictionAdapter'
import { cx, formatNumber, formatPercent } from '../utils/format'

function signalClass(signal: string) {
  const normalized = signal.toUpperCase()
  if (normalized.includes('BUY')) return 'bg-emerald-400/10 text-emerald-200'
  if (normalized.includes('SELL')) return 'bg-rose-400/10 text-rose-200'
  return 'bg-cyan-300/10 text-cyan-200'
}

export function PredictionsPage() {
  const [refreshKey, setRefreshKey] = useState(0)
  const primary = useAsync(() => getPredictionIntelligence(), [refreshKey])
  const fallback = useAsync(() => (primary.error ? getPredictions() : Promise.resolve([])), [primary.error])

  const rows = useMemo(() => {
    const source = primary.data?.length ? primary.data : fallback.data ?? []
    return source.map(normalizePredictionRow)
  }, [fallback.data, primary.data])

  const avgConfidence =
    rows.length > 0
      ? rows.reduce((sum, row) => sum + Number(row.confidence ?? 0), 0) / rows.length
      : undefined

  return (
    <div className="mx-auto max-w-7xl">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="text-sm font-medium uppercase text-cyan-300">Signals</div>
          <h1 className="mt-1 text-2xl font-semibold text-white">Prediction Console</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
            A typed React view over the current Flask prediction intelligence endpoints.
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

      <div className="mb-5 grid gap-4 sm:grid-cols-3">
        <div className="rounded-lg border border-white/10 bg-white/[0.04] p-4">
          <div className="text-xs uppercase text-slate-500">Tracked signals</div>
          <div className="mt-2 text-2xl font-semibold text-white">{formatNumber(rows.length)}</div>
        </div>
        <div className="rounded-lg border border-white/10 bg-white/[0.04] p-4">
          <div className="text-xs uppercase text-slate-500">Avg confidence</div>
          <div className="mt-2 text-2xl font-semibold text-white">{formatNumber(avgConfidence)}</div>
        </div>
        <div className="rounded-lg border border-white/10 bg-white/[0.04] p-4">
          <div className="text-xs uppercase text-slate-500">Source</div>
          <div className="mt-2 text-2xl font-semibold text-white">
            {primary.error ? 'Fallback' : 'Intelligence'}
          </div>
        </div>
      </div>

      <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
        <SectionHeader eyebrow="Table" title="Live prediction rows" />

        {primary.loading ? (
          <div className="mt-5">
            <StatePanel description="Loading prediction intelligence from Flask." title="Syncing" />
          </div>
        ) : rows.length ? (
          <div className="mt-5 overflow-hidden rounded-lg border border-white/10">
            <table className="w-full min-w-[820px] text-left text-sm">
              <thead className="bg-white/[0.04] text-xs uppercase text-slate-400">
                <tr>
                  <th className="px-3 py-3">Symbol</th>
                  <th className="px-3 py-3">Signal</th>
                  <th className="px-3 py-3 text-right">Price</th>
                  <th className="px-3 py-3 text-right">Target</th>
                  <th className="px-3 py-3 text-right">Return</th>
                  <th className="px-3 py-3 text-right">Confidence</th>
                  <th className="px-3 py-3 text-right">AI Size</th>
                  <th className="px-3 py-3">Risk</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10">
                {rows.map((row) => (
                  <tr key={`${row.symbol}-${row.signal}-${row.target ?? ''}`}>
                    <td className="px-3 py-3 font-medium text-white">{row.symbol}</td>
                    <td className="px-3 py-3">
                      <span className={cx('rounded px-2 py-1 text-xs', signalClass(row.signal))}>
                        {row.signal}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-right text-slate-300">{formatNumber(row.price)}</td>
                    <td className="px-3 py-3 text-right text-slate-300">{formatNumber(row.target)}</td>
                    <td className="px-3 py-3 text-right text-slate-300">
                      {formatPercent(row.expectedReturn)}
                    </td>
                    <td className="px-3 py-3 text-right text-slate-300">
                      {formatNumber(row.confidence)}
                    </td>
                    <td className="px-3 py-3 text-right text-slate-300">
                      {formatNumber(row.allocation)}
                    </td>
                    <td className="px-3 py-3 text-slate-300">{row.risk ?? '--'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="mt-5">
            <StatePanel
              description={primary.error ?? 'No prediction rows are available yet. Start Flask and let the prediction engine warm up.'}
              title="No predictions"
            />
          </div>
        )}
      </section>
    </div>
  )
}
