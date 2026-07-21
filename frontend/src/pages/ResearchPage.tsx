import { useState } from 'react'
import { getEmotionalState, getFuturesAnalysis, getResearch } from '../api/news'
import { MetricCard } from '../components/MetricCard'
import { SectionHeader } from '../components/SectionHeader'
import { StatePanel } from '../components/StatePanel'
import { useAsync } from '../hooks/useAsync'
import { cx, formatNumber, formatPercent } from '../utils/format'
import type { ResearchInsight, ResearchReport } from '../types/news'

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function asArray(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? (value.filter((item) => item && typeof item === 'object') as Record<string, unknown>[]) : []
}

function impactTone(impact?: unknown) {
  const text = String(impact ?? '').toLowerCase()
  if (text.includes('high')) return 'border-rose-400/30 bg-rose-400/10 text-rose-100'
  if (text.includes('medium')) return 'border-amber-300/30 bg-amber-300/10 text-amber-100'
  return 'border-white/10 bg-slate-950/40 text-slate-200'
}

function ReportCard({ report }: { report: ResearchReport }) {
  const findings = Array.isArray(report.findings)
    ? report.findings
    : typeof report.findings === 'string'
      ? report.findings.split(/(?=[A-Z0-9]+%|Model|Analyzed|Real-time)/).filter(Boolean)
      : []
  return (
    <article className="rounded-lg border border-white/10 bg-slate-950/40 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-base font-semibold text-white">{report.title ?? 'Research report'}</h3>
        <span className="rounded-md bg-cyan-300/10 px-2 py-1 text-xs text-cyan-100">
          {formatPercent(Number(report.confidence) * 100)}
        </span>
      </div>
      {report.description ? <p className="mt-2 text-sm leading-6 text-slate-400">{report.description}</p> : null}
      {findings.length ? (
        <ul className="mt-3 space-y-2 text-sm text-slate-300">
          {findings.map((finding, index) => (
            <li className="rounded-md bg-white/[0.04] px-3 py-2" key={index}>
              {finding}
            </li>
          ))}
        </ul>
      ) : null}
    </article>
  )
}

function InsightCard({ insight }: { insight: ResearchInsight }) {
  return (
    <article className={cx('rounded-lg border p-4', impactTone(insight.impact))}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold">{insight.insight ?? 'AI insight'}</h3>
          <p className="mt-2 text-sm leading-6 opacity-80">{insight.description ?? 'No description available.'}</p>
        </div>
        <span className="rounded-md border border-white/10 px-2 py-1 text-xs">{insight.impact ?? 'INFO'}</span>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs opacity-80">
        <span>Probability {formatPercent(Number(insight.probability) * 100)}</span>
        <span>Confidence {formatNumber(insight.model_confidence)}</span>
        {insight.timeframe ? <span>{insight.timeframe}</span> : null}
      </div>
    </article>
  )
}

function KeyValuePanel({ data, limit = 6 }: { data: Record<string, unknown>; limit?: number }) {
  const entries = Object.entries(data)
    .filter(([, value]) => ['string', 'number', 'boolean'].includes(typeof value))
    .slice(0, limit)
  if (!entries.length) return <StatePanel title="No data" description="No readable fields are available yet." />
  return (
    <div className="space-y-2">
      {entries.map(([key, value]) => (
        <div className="flex justify-between gap-3 rounded-md bg-white/[0.04] px-3 py-2 text-sm" key={key}>
          <span className="text-slate-400">{key.replace(/_/g, ' ')}</span>
          <span className="text-right font-medium text-white">
            {typeof value === 'number' ? formatNumber(value) : String(value)}
          </span>
        </div>
      ))}
    </div>
  )
}

function FuturesPanel({ data }: { data: Record<string, unknown> | null }) {
  const futures = asRecord(data?.futures)
  const worlds = asArray(futures.worlds ?? futures.scenarios ?? futures.paths)
  return (
    <div className="space-y-3">
      <KeyValuePanel data={futures} limit={5} />
      {worlds.length ? (
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2">Scenario</th>
                <th className="px-3 py-2">Probability</th>
                <th className="px-3 py-2">Return</th>
                <th className="px-3 py-2">Target</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/10">
              {worlds.slice(0, 8).map((world, index) => (
                <tr key={index}>
                  <td className="px-3 py-3 font-medium text-white">
                    {String(world.name ?? world.scenario ?? `World ${index + 1}`)}
                  </td>
                  <td className="px-3 py-3 text-slate-300">{formatPercent(Number(world.probability) * 100)}</td>
                  <td className="px-3 py-3 text-slate-300">
                    {formatPercent(world.return_percent ?? world.expected_return)}
                  </td>
                  <td className="px-3 py-3 text-slate-300">{formatNumber(world.target ?? world.target_price)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  )
}

export function ResearchPage() {
  const [symbol, setSymbol] = useState('')
  const [submittedSymbol, setSubmittedSymbol] = useState('')
  const research = useAsync(() => getResearch(), [])
  const emotional = useAsync(
    () => (submittedSymbol ? getEmotionalState(submittedSymbol) : Promise.resolve(null)),
    [submittedSymbol],
  )
  const futures = useAsync(
    () => (submittedSymbol ? getFuturesAnalysis(submittedSymbol) : Promise.resolve(null)),
    [submittedSymbol],
  )

  const reports = research.data?.researchreports ?? []
  const insights = research.data?.aiinsights ?? []
  const performance = research.data?.model_performance ?? {}
  const liveStats = research.data?.live_stats ?? {}

  return (
    <div className="mx-auto max-w-7xl">
      <div className="mb-6">
        <div className="text-sm font-medium uppercase text-cyan-300">Research</div>
        <h1 className="mt-1 text-2xl font-semibold text-white">Research Cockpit</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
          Review AI research reports, model performance, market insights, and symbol-level emotional
          futures analysis from Flask.
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        <MetricCard
          metric={{
            label: 'Symbols analyzed',
            value: formatNumber(liveStats.total_symbols_analyzed),
          }}
        />
        <MetricCard
          metric={{
            label: 'Predictions',
            value: formatNumber(liveStats.total_predictions),
          }}
        />
        <MetricCard
          metric={{
            label: 'Avg confidence',
            value: formatNumber(liveStats.avg_confidence),
          }}
        />
        <MetricCard
          metric={{
            label: 'Bullish ratio',
            value: formatPercent(Number(liveStats.bullish_ratio) * 100),
          }}
        />
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <SectionHeader eyebrow="Reports" title="AI research" />
          <div className="mt-4 space-y-3">
            {research.loading ? (
              <StatePanel title="Loading research" description="Fetching research output from Flask." />
            ) : research.error ? (
              <StatePanel title="Research unavailable" description={research.error} />
            ) : reports.length ? (
              reports.map((report, index) => <ReportCard report={report} key={`${report.title}-${index}`} />)
            ) : (
              <StatePanel
                title="No reports yet"
                description={research.data?.message ?? 'Run predictions to populate research reports.'}
              />
            )}
          </div>
        </section>

        <aside className="space-y-4">
          <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
            <SectionHeader eyebrow="Performance" title="Model accuracy" />
            <div className="mt-4">
              <KeyValuePanel data={performance} />
            </div>
          </section>

          <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
            <SectionHeader eyebrow="Symbol" title="Emotional futures" />
            <form
              className="mt-4 flex gap-2"
              onSubmit={(event) => {
                event.preventDefault()
                setSubmittedSymbol(symbol.trim().toUpperCase())
              }}
            >
              <input
                className="h-10 min-w-0 flex-1 rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-white outline-none focus:border-cyan-300/50"
                onChange={(event) => setSymbol(event.target.value)}
                placeholder="RELIANCE, INFY..."
                value={symbol}
              />
              <button className="rounded-md bg-cyan-300 px-3 text-sm font-medium text-slate-950" type="submit">
                Load
              </button>
            </form>
          </section>
        </aside>
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-3">
        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5 xl:col-span-2">
          <SectionHeader eyebrow="Insights" title="AI insight stream" />
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {insights.length ? (
              insights.map((insight, index) => <InsightCard insight={insight} key={`${insight.insight}-${index}`} />)
            ) : (
              <StatePanel title="No insights yet" description="Insights appear after prediction history is available." />
            )}
          </div>
        </section>

        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <SectionHeader eyebrow="Stats" title="Live system" />
          <div className="mt-4">
            <KeyValuePanel data={liveStats} />
          </div>
        </section>
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-2">
        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <SectionHeader eyebrow="Emotion" title={submittedSymbol ? `${submittedSymbol} state` : 'Symbol state'} />
          <div className="mt-4">
            {!submittedSymbol ? (
              <StatePanel title="No symbol selected" description="Enter a symbol to load emotional state." />
            ) : emotional.loading ? (
              <StatePanel title="Loading emotion" description={`Analyzing ${submittedSymbol}.`} />
            ) : emotional.error ? (
              <StatePanel title="Emotion unavailable" description={emotional.error} />
            ) : (
              <KeyValuePanel data={asRecord(asRecord(emotional.data).emotional_state)} limit={10} />
            )}
          </div>
        </section>

        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <SectionHeader eyebrow="Futures" title={submittedSymbol ? `${submittedSymbol} worlds` : 'Future worlds'} />
          <div className="mt-4">
            {!submittedSymbol ? (
              <StatePanel title="No symbol selected" description="Enter a symbol to generate future scenarios." />
            ) : futures.loading ? (
              <StatePanel title="Loading futures" description={`Generating worlds for ${submittedSymbol}.`} />
            ) : futures.error ? (
              <StatePanel title="Futures unavailable" description={futures.error} />
            ) : (
              <FuturesPanel data={futures.data} />
            )}
          </div>
        </section>
      </div>
    </div>
  )
}
