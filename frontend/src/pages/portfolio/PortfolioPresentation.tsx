import { StatePanel } from '../../components/StatePanel'
import { cx, formatNumber, formatPercent } from '../../utils/format'

function toNumber(value: unknown) {
  const num = Number(value)
  return Number.isFinite(num) ? num : undefined
}

function firstNumber(record: Record<string, unknown> | undefined, keys: string[]) {
  for (const key of keys) {
    const value = toNumber(record?.[key])
    if (value !== undefined) return value
  }
  return undefined
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function asArray(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? (value.filter((item) => item && typeof item === 'object') as Record<string, unknown>[]) : []
}

function titleize(value: string) {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (match) => match.toUpperCase())
}

function MiniStat({ label, value, tone }: { label: string; value: unknown; tone?: 'good' | 'bad' | 'warn' }) {
  const toneClass =
    tone === 'good'
      ? 'text-emerald-300'
      : tone === 'bad'
        ? 'text-rose-300'
        : tone === 'warn'
          ? 'text-amber-200'
          : 'text-white'
  return (
    <div className="rounded-md bg-white/[0.04] p-3">
      <div className="text-xs uppercase text-slate-500">{label}</div>
      <div className={cx('mt-2 text-lg font-semibold', toneClass)}>{String(value ?? '--')}</div>
    </div>
  )
}

export function KeyValueList({ data, limit = 6 }: { data: Record<string, unknown> | null | undefined; limit?: number }) {
  const entries = Object.entries(data ?? {})
    .filter(([, value]) => ['string', 'number', 'boolean'].includes(typeof value))
    .slice(0, limit)
  if (!entries.length) {
    return <StatePanel title="No data" description="No readable fields are available yet." />
  }
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

export function SellSimulationResult({ result }: { result: Record<string, unknown> }) {
  const scenarios = asArray(result.scenarios)
  return (
    <div className="mt-4">
      <div className="mb-3 grid gap-3 sm:grid-cols-3">
        <MiniStat label="Recommended" value={result.recommended_method ?? '--'} tone="good" />
        <MiniStat label="Sell quantity" value={formatNumber(result.sell_quantity)} />
        <MiniStat label="Sell price" value={formatNumber(result.sell_price)} />
      </div>
      {scenarios.length ? (
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <caption className="sr-only">Sell simulation scenarios and estimated gain or tax impact</caption>
            <thead className="text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2">Method</th>
                <th className="px-3 py-2">Gain</th>
                <th className="px-3 py-2">STCG</th>
                <th className="px-3 py-2">LTCG</th>
                <th className="px-3 py-2">Tax proxy</th>
                <th className="px-3 py-2">Lots</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/10">
              {scenarios.map((scenario) => {
                const gain = firstNumber(scenario, ['realized_gain'])
                return (
                  <tr key={String(scenario.method)}>
                    <td className="px-3 py-3 font-medium text-white">{String(scenario.method ?? '--')}</td>
                    <td className={cx('px-3 py-3', (gain ?? 0) >= 0 ? 'text-emerald-300' : 'text-rose-300')}>
                      {formatNumber(gain)}
                    </td>
                    <td className="px-3 py-3 text-slate-300">{formatNumber(scenario.realized_stcg)}</td>
                    <td className="px-3 py-3 text-slate-300">{formatNumber(scenario.realized_ltcg)}</td>
                    <td className="px-3 py-3 text-slate-300">{formatNumber(scenario.tax_impact_proxy)}</td>
                    <td className="px-3 py-3 text-slate-300">{asArray(scenario.matched_lots).length}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <StatePanel title="No scenarios" description="The backend could not produce sell scenarios." />
      )}
    </div>
  )
}

export function TaxSummaryPanel({ data }: { data: Record<string, unknown> | null }) {
  return (
    <div className="mt-4 space-y-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <MiniStat label="Financial year" value={data?.fy ?? '--'} />
        <MiniStat label="Transactions" value={formatNumber(data?.transactions)} />
        <MiniStat label="Realized total" value={formatNumber(data?.realized_total)} />
        <MiniStat label="STCG realized" value={formatNumber(data?.stcg_realized)} />
        <MiniStat label="LTCG realized" value={formatNumber(data?.ltcg_realized)} />
        <MiniStat label="From" value={String(data?.from ?? '--').slice(0, 10)} />
      </div>
    </div>
  )
}

export function IntelligencePanel({ data }: { data: Record<string, unknown> | null }) {
  const forecast = asRecord(data?.forecast)
  const horizons = asRecord(forecast.horizons)
  const horizonEntries = Object.entries(horizons).slice(0, 3)
  const governance = asRecord(data?.governance)
  const survival = asRecord(data?.survival)
  const alerts = asArray(governance.alerts)
  const scorecard = asArray(data?.scorecard)

  return (
    <div className="mt-4 space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <MiniStat label="Current value" value={formatNumber(forecast.current_value)} />
        <MiniStat label="Survival score" value={formatNumber(survival.score)} tone="good" />
        <MiniStat
          label="Governance"
          value={governance.status ?? '--'}
          tone={governance.status === 'GUARD' ? 'warn' : 'good'}
        />
      </div>
      {horizonEntries.length ? (
        <div className="space-y-2">
          <div className="text-xs uppercase text-slate-500">Forecast horizons</div>
          {horizonEntries.map(([label, raw]) => {
            const horizon = asRecord(raw)
            return (
              <div className="rounded-md bg-white/[0.04] p-3" key={label}>
                <div className="flex justify-between gap-3">
                  <span className="font-medium text-white">{label}</span>
                  <span className="text-slate-300">{formatNumber(horizon.expected_value)}</span>
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  P05 {formatNumber(horizon.p05_value)} | P95 {formatNumber(horizon.p95_value)} | DD10{' '}
                  {formatPercent(Number(horizon.drawdown_prob_10) * 100)}
                </div>
              </div>
            )
          })}
        </div>
      ) : null}
      {alerts.length ? (
        <div className="space-y-2">
          <div className="text-xs uppercase text-slate-500">Governance alerts</div>
          {alerts.slice(0, 3).map((alert, index) => (
            <div className="rounded-md border border-amber-300/20 bg-amber-300/10 p-3 text-sm" key={index}>
              <div className="font-medium text-amber-100">{String(alert.severity ?? 'Alert')}</div>
              <div className="mt-1 text-amber-100/80">{String(alert.message ?? '--')}</div>
            </div>
          ))}
        </div>
      ) : null}
      {scorecard.length ? (
        <div className="grid gap-2">
          {scorecard.slice(0, 3).map((row, index) => (
            <div className="flex justify-between rounded-md bg-white/[0.04] px-3 py-2 text-sm" key={index}>
              <span className="text-slate-300">{String(row.module ?? '--')}</span>
              <span className="font-medium text-emerald-300">{String(row.status ?? '--')}</span>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  )
}
