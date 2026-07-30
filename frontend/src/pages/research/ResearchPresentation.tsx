import { StatePanel } from '../../components/StatePanel'
import { cx, formatNumber, formatPercent } from '../../utils/format'
import type { ResearchInsight, ResearchReport } from '../../types/news'

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

function titleize(value: string) {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (match) => match.toUpperCase())
}

export function ReportCard({ report }: { report: ResearchReport }) {
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

export function InsightCard({ insight }: { insight: ResearchInsight }) {
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

export function KeyValuePanel({ data, limit = 6 }: { data: Record<string, unknown>; limit?: number }) {
  const entries = Object.entries(data)
    .filter(([, value]) => ['string', 'number', 'boolean'].includes(typeof value))
    .slice(0, limit)
  if (!entries.length) return <StatePanel title="No data" description="No readable fields are available yet." />
  return (
    <div className="space-y-2">
      {entries.map(([key, value]) => (
        <div className="flex justify-between gap-3 rounded-md bg-white/[0.04] px-3 py-2 text-sm" key={key}>
          <span className="text-slate-400">{titleize(key)}</span>
          <span className="text-right font-medium text-white">
            {typeof value === 'number' ? formatNumber(value) : String(value)}
          </span>
        </div>
      ))}
    </div>
  )
}

export function FuturesPanel({ data }: { data: Record<string, unknown> | null }) {
  const futures = asRecord(data?.futures)
  const worlds = asArray(futures.worlds ?? futures.scenarios ?? futures.paths)
  return (
    <div className="space-y-3">
      <KeyValuePanel data={futures} limit={5} />
      {worlds.length ? (
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <caption className="sr-only">Future scenario probabilities, expected returns, and targets</caption>
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
