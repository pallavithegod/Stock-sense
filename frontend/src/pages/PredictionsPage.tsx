import { useCallback, useMemo } from 'react'
import { getPredictionIntelligence, getPredictions } from '../api/predictions'
import { IconButton } from '../components/IconButton'
import { SectionHeader } from '../components/SectionHeader'
import { StatePanel } from '../components/StatePanel'
import { useQuery } from '../query/useQuery'
import { normalizePredictionRow } from '../utils/predictionAdapter'
import { cx, formatNumber, formatPercent } from '../utils/format'

function signalClass(signal: string) {
  const normalized = signal.toUpperCase()
  if (normalized.includes('BUY')) return 'bg-emerald-400/10 text-emerald-200'
  if (normalized.includes('SELL')) return 'bg-rose-400/10 text-rose-200'
  return 'bg-cyan-300/10 text-cyan-200'
}

export function PredictionsPage() {
  const loadPrimary = useCallback((signal: AbortSignal) => getPredictionIntelligence({ signal }), [])
  const loadFallback = useCallback((signal: AbortSignal) => getPredictions({ signal }), [])
  const primary = useQuery({
    key: ['predictions', 'intelligence'],
    queryFn: loadPrimary,
    retry: 1,
    staleMs: 30_000,
  })
  const fallback = useQuery({
    enabled: Boolean(primary.error),
    key: ['predictions', 'fallback'],
    queryFn: loadFallback,
    retry: 1,
    staleMs: 30_000,
  })

  const rows = useMemo(() => {
    const source = primary.data?.length ? primary.data : fallback.data ?? []
    return source.map(normalizePredictionRow)
  }, [fallback.data, primary.data])

  const confidenceRows = rows.filter((row) => row.confidence !== undefined)
  const avgConfidence =
    confidenceRows.length > 0
      ? confidenceRows.reduce((sum, row) => sum + Number(row.confidence), 0) / confidenceRows.length
      : undefined
  const hasFallbackRows = rows.some((row) => row.dataQuality !== undefined && row.dataQuality !== 'live')
  const sourceLabel = rows.find((row) => row.sourceType)?.sourceType ?? (primary.error ? 'fallback' : 'unavailable')

  return (
    <div className="mx-auto max-w-7xl">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="text-sm font-medium uppercase text-cyan-300">Signals</div>
          <h1 className="mt-1 text-2xl font-semibold text-white">Prediction Console</h1>
        </div>
        <IconButton
          disabled={primary.refreshing}
          label="Refresh predictions"
          onClick={primary.refetch}
          tone="primary"
        >
          {primary.refreshing ? 'Syncing' : 'Refresh'}
        </IconButton>
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
            {sourceLabel.replaceAll('_', ' ')}
          </div>
        </div>
      </div>

      <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
        <SectionHeader eyebrow="Table" title="Live prediction rows" />

        {primary.loading ? (
          <div className="mt-5">
            <StatePanel description="Loading prediction intelligence." title="Syncing" />
          </div>
        ) : rows.length ? (
          <div className="mt-5 overflow-hidden rounded-lg border border-white/10">
            <table className="w-full min-w-[980px] text-left text-sm">
              <caption className="sr-only">Prediction rows with signal, price, target, return, confidence, risk, and source</caption>
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
                  <th className="px-3 py-3">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10">
                {rows.map((row) => (
                  <tr key={row.fingerprint ?? `${row.symbol}-${row.signal}-${row.target ?? ''}`}>
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
                    <td className="px-3 py-3 text-xs text-slate-400">
                      <div>{(row.sourceType ?? 'unavailable').replaceAll('_', ' ')}</div>
                      {row.provider ? <div className="text-slate-500">{row.provider}</div> : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {hasFallbackRows ? (
              <div className="border-t border-white/10 bg-amber-300/10 px-3 py-2 text-xs text-amber-100">
                Prediction pipeline data is unavailable. WATCH rows are based on saved portfolio or market-universe
                entries, not model predictions.
              </div>
            ) : null}
          </div>
        ) : (
          <div className="mt-5">
            <StatePanel
              description={primary.error ?? 'No prediction rows are available yet. Let the prediction engine warm up.'}
              title="No predictions"
            />
          </div>
        )}
      </section>
    </div>
  )
}
