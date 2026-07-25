import { useState } from 'react'
import type { FormEvent } from 'react'
import {
  createPortfolioPosition,
  deletePortfolioPosition,
  getPortfolioIntelligenceSuite,
  getPortfolioLotInsights,
  getPortfolioLots,
  getPortfolioState,
  getPortfolioTaxSummary,
  getRealizedGains,
  simulatePortfolioSell,
  updatePortfolioPosition,
} from '../api/portfolio'
import { MetricCard } from '../components/MetricCard'
import { SectionHeader } from '../components/SectionHeader'
import { StatePanel } from '../components/StatePanel'
import { useAsync } from '../hooks/useAsync'
import { cx, formatNumber, formatPercent } from '../utils/format'
import type {
  PortfolioLot,
  PortfolioMutationPayload,
  PortfolioPosition,
  RealizedGain,
  SellSimulationPayload,
} from '../types/portfolio'

type PositionForm = {
  symbol: string
  quantity: string
  avgPrice: string
  purchaseDate: string
}

type SellForm = {
  symbol: string
  quantity: string
  sellPrice: string
  fees: string
  sellDate: string
}

const emptyPositionForm: PositionForm = {
  symbol: '',
  quantity: '',
  avgPrice: '',
  purchaseDate: '',
}

const emptySellForm: SellForm = {
  symbol: '',
  quantity: '',
  sellPrice: '',
  fees: '0',
  sellDate: '',
}

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

function positionQuantity(position: PortfolioPosition) {
  return firstNumber(position, ['open_qty', 'quantity', 'qty'])
}

function positionAverage(position: PortfolioPosition) {
  return firstNumber(position, ['avg_price', 'price', 'buy_price'])
}

function positionValue(position: PortfolioPosition) {
  return firstNumber(position, ['current_value', 'value'])
}

function positionPnl(position: PortfolioPosition) {
  return firstNumber(position, ['pnl', 'unrealized_pnl', 'unrealized_total'])
}

function positionPnlPercent(position: PortfolioPosition) {
  const explicit = firstNumber(position, ['pnl_percent', 'unrealized_pnl_percent'])
  if (explicit !== undefined) return explicit

  const pnl = positionPnl(position)
  const quantity = positionQuantity(position)
  const average = positionAverage(position)
  const cost = quantity !== undefined && average !== undefined ? quantity * average : undefined
  return pnl !== undefined && cost ? (pnl / cost) * 100 : undefined
}

function lotId(lot: PortfolioLot) {
  return lot.id ?? lot.lot_id ?? `${lot.symbol ?? 'LOT'}-${lot.buy_date ?? lot.purchase_date ?? ''}`
}

function lotQuantity(lot: PortfolioLot) {
  return firstNumber(lot, ['open_qty', 'quantity', 'qty'])
}

function lotPrice(lot: PortfolioLot) {
  return firstNumber(lot, ['buy_price', 'avg_price', 'purchase_price'])
}

function lotDate(lot: PortfolioLot) {
  return String(lot.buy_date ?? lot.purchase_date ?? lot.added_date ?? '--')
}

function gainValue(gain: RealizedGain) {
  return firstNumber(gain, ['realized_gain', 'gain', 'pnl'])
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function asArray(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.filter((item) => item && typeof item === 'object') as Record<string, unknown>[] : []
}

function titleize(value: string) {
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (match) => match.toUpperCase())
}

function payloadFromForm(form: PositionForm): PortfolioMutationPayload {
  return {
    symbol: form.symbol.trim().toUpperCase(),
    quantity: Number(form.quantity),
    avg_price: Number(form.avgPrice),
    purchase_date: form.purchaseDate || undefined,
  }
}

function sellPayloadFromForm(form: SellForm): SellSimulationPayload {
  return {
    symbol: form.symbol.trim().toUpperCase(),
    quantity: Number(form.quantity),
    sell_price: Number(form.sellPrice),
    sell_date: form.sellDate || undefined,
    fees: Number(form.fees || 0),
    methods: ['FIFO', 'LIFO', 'HIFO'],
  }
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

function KeyValueList({ data, limit = 6 }: { data: Record<string, unknown> | null | undefined; limit?: number }) {
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

function SellSimulationResult({ result }: { result: Record<string, unknown> }) {
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

function TaxSummaryPanel({ data }: { data: Record<string, unknown> | null }) {
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

function IntelligencePanel({ data }: { data: Record<string, unknown> | null }) {
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

export function PortfolioPage() {
  const [refreshKey, setRefreshKey] = useState(0)
  const [selectedSymbol, setSelectedSymbol] = useState('')
  const [editingSymbol, setEditingSymbol] = useState<string | null>(null)
  const [positionForm, setPositionForm] = useState<PositionForm>(emptyPositionForm)
  const [sellForm, setSellForm] = useState<SellForm>(emptySellForm)
  const [mutationError, setMutationError] = useState<string | null>(null)
  const [mutationMessage, setMutationMessage] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [sellResult, setSellResult] = useState<Record<string, unknown> | null>(null)

  const portfolio = useAsync(() => getPortfolioState(), [refreshKey])
  const lots = useAsync(() => getPortfolioLots(selectedSymbol || undefined), [refreshKey, selectedSymbol])
  const realized = useAsync(() => getRealizedGains(selectedSymbol || undefined), [refreshKey, selectedSymbol])
  const taxSummary = useAsync(() => getPortfolioTaxSummary(), [refreshKey])
  const insights = useAsync(() => getPortfolioLotInsights(selectedSymbol || undefined), [
    refreshKey,
    selectedSymbol,
  ])
  const intelligence = useAsync(() => getPortfolioIntelligenceSuite(), [refreshKey])

  const positions = portfolio.data?.positions ?? []
  const metrics = portfolio.data?.account_metrics ?? {}
  const totalValue =
    firstNumber(metrics, ['total_value', 'portfolio_value', 'current_value']) ??
    positions.reduce((sum, position) => sum + (positionValue(position) ?? 0), 0)
  const totalPnl =
    firstNumber(metrics, ['total_pnl', 'unrealized_pnl', 'pnl']) ??
    positions.reduce((sum, position) => sum + (positionPnl(position) ?? 0), 0)
  const totalCost =
    firstNumber(metrics, ['total_cost', 'invested_value', 'total_invested']) ??
    positions.reduce(
      (sum, position) => sum + (positionAverage(position) ?? 0) * (positionQuantity(position) ?? 0),
      0,
    )
  const pnlPercent = totalCost ? (totalPnl / totalCost) * 100 : undefined

  const metricEntries = Object.entries(metrics)
    .filter(([, value]) => Number.isFinite(Number(value)))
    .slice(0, 4)

  async function submitPosition(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setMutationError(null)
    setMutationMessage(null)
    try {
      const payload = payloadFromForm(positionForm)
      if (!payload.symbol || payload.quantity <= 0 || payload.avg_price <= 0) {
        throw new Error('Enter symbol, quantity, and average price.')
      }
      if (editingSymbol) {
        await updatePortfolioPosition(editingSymbol, payload)
        setMutationMessage(`${editingSymbol} updated.`)
      } else {
        await createPortfolioPosition(payload)
        setMutationMessage(`${payload.symbol} added.`)
      }
      setEditingSymbol(null)
      setPositionForm(emptyPositionForm)
      setRefreshKey((key) => key + 1)
    } catch (error) {
      setMutationError(error instanceof Error ? error.message : 'Portfolio save failed.')
    } finally {
      setSaving(false)
    }
  }

  async function removePosition(symbol: string) {
    setSaving(true)
    setMutationError(null)
    setMutationMessage(null)
    try {
      await deletePortfolioPosition(symbol)
      setMutationMessage(`${symbol} deleted.`)
      if (selectedSymbol === symbol) setSelectedSymbol('')
      setRefreshKey((key) => key + 1)
    } catch (error) {
      setMutationError(error instanceof Error ? error.message : 'Delete failed.')
    } finally {
      setSaving(false)
    }
  }

  async function submitSellSimulation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setMutationError(null)
    setSellResult(null)
    try {
      const payload = sellPayloadFromForm(sellForm)
      if (!payload.symbol || payload.quantity <= 0 || payload.sell_price <= 0) {
        throw new Error('Enter symbol, sell quantity, and sell price.')
      }
      setSellResult(await simulatePortfolioSell(payload))
    } catch (error) {
      setMutationError(error instanceof Error ? error.message : 'Sell simulation failed.')
    } finally {
      setSaving(false)
    }
  }

  function startEdit(position: PortfolioPosition) {
    const symbol = String(position.symbol || '').toUpperCase()
    setEditingSymbol(symbol)
    setPositionForm({
      symbol,
      quantity: String(positionQuantity(position) ?? ''),
      avgPrice: String(positionAverage(position) ?? ''),
      purchaseDate: String(position.purchase_date ?? position.added_date ?? '').slice(0, 10),
    })
  }

  function syncSellPosition(position: PortfolioPosition) {
    const symbol = String(position.symbol || '').toUpperCase()
    setSelectedSymbol(symbol)
    setSellForm((current) => ({
      ...current,
      symbol,
      quantity: current.quantity || String(positionQuantity(position) ?? ''),
      sellPrice: current.sellPrice || String(position.current_price ?? positionAverage(position) ?? ''),
    }))
  }

  return (
    <div className="mx-auto max-w-7xl">
      <div className="mb-6 flex items-end justify-between gap-3">
        <div>
          <div className="text-sm font-medium uppercase text-cyan-300">Portfolio</div>
          <h1 className="mt-1 text-2xl font-semibold text-white">Portfolio Desk</h1>
        </div>
        <button
          className="h-10 rounded-md border border-cyan-300/30 bg-cyan-300/10 px-4 text-sm font-medium text-cyan-100 hover:bg-cyan-300/15"
          disabled={portfolio.loading}
          onClick={() => setRefreshKey((key) => key + 1)}
          type="button"
        >
          {portfolio.loading ? 'Syncing' : 'Refresh'}
        </button>
      </div>

      {mutationError ? (
        <div className="mb-4 rounded-md border border-rose-400/30 bg-rose-400/10 p-3 text-sm text-rose-200">
          {mutationError}
        </div>
      ) : null}
      {mutationMessage ? (
        <div className="mb-4 rounded-md border border-emerald-400/30 bg-emerald-400/10 p-3 text-sm text-emerald-200">
          {mutationMessage}
        </div>
      ) : null}

      <div className="grid gap-3 md:grid-cols-4">
        <MetricCard metric={{ label: 'Positions', value: positions.length }} />
        <MetricCard metric={{ label: 'Current value', value: formatNumber(totalValue) }} />
        <MetricCard
          metric={{
            label: 'Unrealized P&L',
            value: formatNumber(totalPnl),
            tone: (totalPnl ?? 0) >= 0 ? 'positive' : 'negative',
          }}
        />
        <MetricCard
          metric={{
            label: 'P&L %',
            value: formatPercent(pnlPercent),
            tone: (pnlPercent ?? 0) >= 0 ? 'positive' : 'negative',
          }}
        />
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-[1.5fr_0.9fr]">
        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <SectionHeader eyebrow="Holdings" title="Open positions" />
          {portfolio.loading ? (
            <StatePanel title="Loading portfolio" description="Reading holdings." />
          ) : portfolio.error ? (
            <StatePanel title="Portfolio unavailable" description={portfolio.error} />
          ) : positions.length ? (
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-3 py-2">Symbol</th>
                    <th className="px-3 py-2">Qty</th>
                    <th className="px-3 py-2">Avg</th>
                    <th className="px-3 py-2">Price</th>
                    <th className="px-3 py-2">Value</th>
                    <th className="px-3 py-2">P&L</th>
                    <th className="px-3 py-2">Signal</th>
                    <th className="px-3 py-2"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/10">
                  {positions.map((position) => {
                    const pnl = positionPnl(position)
                    return (
                      <tr
                        className={cx(
                          'cursor-pointer hover:bg-white/[0.03]',
                          selectedSymbol === position.symbol && 'bg-cyan-300/10',
                        )}
                        key={position.symbol}
                        onClick={() => syncSellPosition(position)}
                      >
                        <td className="px-3 py-3 font-medium text-white">{position.symbol}</td>
                        <td className="px-3 py-3 text-slate-300">{formatNumber(positionQuantity(position))}</td>
                        <td className="px-3 py-3 text-slate-300">{formatNumber(positionAverage(position))}</td>
                        <td className="px-3 py-3 text-slate-300">{formatNumber(position.current_price)}</td>
                        <td className="px-3 py-3 text-slate-300">{formatNumber(positionValue(position))}</td>
                        <td className={cx('px-3 py-3', (pnl ?? 0) >= 0 ? 'text-emerald-300' : 'text-rose-300')}>
                          {formatNumber(pnl)}
                          <div className="text-xs">{formatPercent(positionPnlPercent(position))}</div>
                        </td>
                        <td className="px-3 py-3 text-slate-300">
                          {position.action ?? '--'}
                          {position.confidence !== undefined ? (
                            <div className="text-xs text-slate-500">{formatNumber(position.confidence)} confidence</div>
                          ) : null}
                        </td>
                        <td className="px-3 py-3">
                          <div className="flex gap-2">
                            <button
                              className="rounded-md border border-white/10 px-2 py-1 text-xs text-slate-200 hover:border-cyan-300/40"
                              onClick={(event) => {
                                event.stopPropagation()
                                startEdit(position)
                              }}
                              type="button"
                            >
                              Edit
                            </button>
                            <button
                              className="rounded-md border border-rose-400/30 px-2 py-1 text-xs text-rose-200 hover:bg-rose-400/10"
                              disabled={saving}
                              onClick={(event) => {
                                event.stopPropagation()
                                void removePosition(position.symbol)
                              }}
                              type="button"
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <StatePanel
              title="No holdings yet"
              description="Add a demo position to validate the SQLite portfolio flow."
            />
          )}
        </section>

        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <SectionHeader eyebrow={editingSymbol ? 'Edit' : 'Add'} title="Position" />
          <form className="mt-4 space-y-3" onSubmit={(event) => void submitPosition(event)}>
            <input
              className="h-10 w-full rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-white outline-none focus:border-cyan-300/50"
              disabled={Boolean(editingSymbol)}
              onChange={(event) => setPositionForm((form) => ({ ...form, symbol: event.target.value }))}
              placeholder="Symbol, e.g. INFY"
              value={positionForm.symbol}
            />
            <div className="grid gap-3 sm:grid-cols-2">
              <input
                className="h-10 rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-white outline-none focus:border-cyan-300/50"
                min="0"
                onChange={(event) => setPositionForm((form) => ({ ...form, quantity: event.target.value }))}
                placeholder="Quantity"
                step="any"
                type="number"
                value={positionForm.quantity}
              />
              <input
                className="h-10 rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-white outline-none focus:border-cyan-300/50"
                min="0"
                onChange={(event) => setPositionForm((form) => ({ ...form, avgPrice: event.target.value }))}
                placeholder="Average price"
                step="any"
                type="number"
                value={positionForm.avgPrice}
              />
            </div>
            <input
              className="h-10 w-full rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-white outline-none focus:border-cyan-300/50"
              onChange={(event) => setPositionForm((form) => ({ ...form, purchaseDate: event.target.value }))}
              type="date"
              value={positionForm.purchaseDate}
            />
            <div className="flex gap-2">
              <button
                className="rounded-md bg-cyan-300 px-3 py-2 text-sm font-medium text-slate-950 disabled:opacity-50"
                disabled={saving}
                type="submit"
              >
                {editingSymbol ? 'Update' : 'Add'}
              </button>
              {editingSymbol ? (
                <button
                  className="rounded-md border border-white/10 px-3 py-2 text-sm text-slate-300"
                  onClick={() => {
                    setEditingSymbol(null)
                    setPositionForm(emptyPositionForm)
                  }}
                  type="button"
                >
                  Cancel
                </button>
              ) : null}
            </div>
          </form>
        </section>
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-2">
        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <SectionHeader eyebrow="Lots" title={selectedSymbol ? `${selectedSymbol} open lots` : 'Open lots'} />
          <div className="mt-4 overflow-x-auto">
            {lots.loading ? (
              <StatePanel title="Loading lots" description="Reading open tax lots." />
            ) : lots.data?.data.length ? (
              <table className="min-w-full text-left text-sm">
                <thead className="text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-3 py-2">Lot</th>
                    <th className="px-3 py-2">Symbol</th>
                    <th className="px-3 py-2">Qty</th>
                    <th className="px-3 py-2">Buy price</th>
                    <th className="px-3 py-2">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/10">
                  {lots.data.data.slice(0, 10).map((lot) => (
                    <tr key={String(lotId(lot))}>
                      <td className="px-3 py-3 text-slate-400">{String(lotId(lot))}</td>
                      <td className="px-3 py-3 font-medium text-white">{lot.symbol ?? '--'}</td>
                      <td className="px-3 py-3 text-slate-300">{formatNumber(lotQuantity(lot))}</td>
                      <td className="px-3 py-3 text-slate-300">{formatNumber(lotPrice(lot))}</td>
                      <td className="px-3 py-3 text-slate-300">{lotDate(lot)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <StatePanel title="No lots" description="No open lots are available for the current filter." />
            )}
          </div>
        </section>

        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <SectionHeader eyebrow="Sell" title="Simulation" />
          <form className="mt-4 grid gap-3 sm:grid-cols-2" onSubmit={(event) => void submitSellSimulation(event)}>
            <input
              className="h-10 rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-white outline-none focus:border-cyan-300/50"
              onChange={(event) => setSellForm((form) => ({ ...form, symbol: event.target.value }))}
              placeholder="Symbol"
              value={sellForm.symbol}
            />
            <input
              className="h-10 rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-white outline-none focus:border-cyan-300/50"
              min="0"
              onChange={(event) => setSellForm((form) => ({ ...form, quantity: event.target.value }))}
              placeholder="Quantity"
              step="any"
              type="number"
              value={sellForm.quantity}
            />
            <input
              className="h-10 rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-white outline-none focus:border-cyan-300/50"
              min="0"
              onChange={(event) => setSellForm((form) => ({ ...form, sellPrice: event.target.value }))}
              placeholder="Sell price"
              step="any"
              type="number"
              value={sellForm.sellPrice}
            />
            <input
              className="h-10 rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-white outline-none focus:border-cyan-300/50"
              min="0"
              onChange={(event) => setSellForm((form) => ({ ...form, fees: event.target.value }))}
              placeholder="Fees"
              step="any"
              type="number"
              value={sellForm.fees}
            />
            <input
              className="h-10 rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-white outline-none focus:border-cyan-300/50"
              onChange={(event) => setSellForm((form) => ({ ...form, sellDate: event.target.value }))}
              type="date"
              value={sellForm.sellDate}
            />
            <button
              className="h-10 rounded-md bg-cyan-300 px-3 text-sm font-medium text-slate-950 disabled:opacity-50"
              disabled={saving}
              type="submit"
            >
              Simulate FIFO/LIFO/HIFO
            </button>
          </form>
          {sellResult ? (
            <SellSimulationResult result={sellResult} />
          ) : null}
        </section>
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-3">
        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <SectionHeader eyebrow="Realized" title="Gains ledger" />
          <div className="mt-4 space-y-2">
            {realized.data?.data.length ? (
              realized.data.data.slice(0, 5).map((gain, index) => (
                <div className="rounded-md border border-white/10 bg-slate-950/40 p-3" key={`${gain.symbol}-${index}`}>
                  <div className="flex justify-between gap-3">
                    <div className="font-medium text-white">{gain.symbol ?? '--'}</div>
                    <div className={cx((gainValue(gain) ?? 0) >= 0 ? 'text-emerald-300' : 'text-rose-300')}>
                      {formatNumber(gainValue(gain))}
                    </div>
                  </div>
                  <div className="mt-1 text-xs text-slate-500">
                    {gain.sell_date ?? '--'} | STCG {formatNumber(gain.realized_stcg)} | LTCG{' '}
                    {formatNumber(gain.realized_ltcg)}
                  </div>
                </div>
              ))
            ) : (
              <StatePanel title="No realized gains" description="Sell history will appear here." />
            )}
          </div>
        </section>

        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <SectionHeader eyebrow="Tax" title="Summary" />
          <TaxSummaryPanel data={taxSummary.data} />
        </section>

        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <SectionHeader eyebrow="Intelligence" title="Snapshot" />
          <div className="mt-4 space-y-3">
            {metricEntries.map(([key, value]) => (
              <div className="flex justify-between rounded-md bg-white/[0.04] px-3 py-2 text-sm" key={key}>
                <span className="text-slate-400">{key}</span>
                <span className="font-medium text-white">{formatNumber(value)}</span>
              </div>
            ))}
            {selectedSymbol && insights.data ? (
              <div>
                <div className="mb-2 text-xs uppercase text-slate-500">{selectedSymbol} lot insight</div>
                <KeyValueList data={asRecord(insights.data.fy_summary)} limit={4} />
              </div>
            ) : null}
            <IntelligencePanel data={intelligence.data} />
          </div>
        </section>
      </div>
    </div>
  )
}
