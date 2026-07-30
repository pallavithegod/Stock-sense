import { useCallback, useState } from 'react'
import { getEmotionalState, getFuturesAnalysis, getResearch } from '../api/news'
import { MetricCard } from '../components/MetricCard'
import { SectionHeader } from '../components/SectionHeader'
import { StatePanel } from '../components/StatePanel'
import { useQuery } from '../query/useQuery'
import { formatNumber, formatPercent } from '../utils/format'
import { FuturesPanel, InsightCard, KeyValuePanel, ReportCard } from './research/ResearchPresentation'
import { asRecord } from './research/researchView'

export function ResearchPage() {
  const [symbol, setSymbol] = useState('')
  const [submittedSymbol, setSubmittedSymbol] = useState('')
  const loadResearch = useCallback((signal: AbortSignal) => getResearch({ signal }), [])
  const loadEmotional = useCallback(
    (signal: AbortSignal) => getEmotionalState(submittedSymbol, { signal }),
    [submittedSymbol],
  )
  const loadFutures = useCallback(
    (signal: AbortSignal) => getFuturesAnalysis(submittedSymbol, { signal }),
    [submittedSymbol],
  )
  const research = useQuery({
    key: ['research', 'overview'],
    queryFn: loadResearch,
    retry: 1,
    staleMs: 60_000,
  })
  const emotional = useQuery({
    enabled: Boolean(submittedSymbol),
    key: ['research', 'emotional', submittedSymbol],
    queryFn: loadEmotional,
    retry: 1,
    staleMs: 60_000,
  })
  const futures = useQuery({
    enabled: Boolean(submittedSymbol),
    key: ['research', 'futures', submittedSymbol],
    queryFn: loadFutures,
    retry: 1,
    staleMs: 60_000,
  })

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
          futures analysis.
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
              <StatePanel title="Loading research" description="Fetching research output." />
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
              <label className="sr-only" htmlFor="research-symbol">
                Stock symbol
              </label>
              <input
                id="research-symbol"
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
              <FuturesPanel data={futures.data ?? null} />
            )}
          </div>
        </section>
      </div>
    </div>
  )
}
