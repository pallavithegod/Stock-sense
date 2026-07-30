import type { FormEvent } from 'react'
import { IconButton } from '../../components/IconButton'
import { MetricCard } from '../../components/MetricCard'
import { SectionHeader } from '../../components/SectionHeader'
import { StatePanel } from '../../components/StatePanel'
import { cx, formatNumber, formatPercent } from '../../utils/format'
import {
  IntelligencePanel,
  KeyValueList,
  SellSimulationResult,
  TaxSummaryPanel,
} from './PortfolioPresentation'
import {
  asRecord,
  gainValue,
  lotDate,
  lotId,
  lotPrice,
  lotQuantity,
  positionAverage,
  positionPnl,
  positionPnlPercent,
  positionQuantity,
  positionValue,
  titleize,
} from './portfolioView'
import type {
  FieldErrors,
  PositionForm,
  SellForm,
} from './portfolioView'
import type {
  PortfolioCollection,
  PortfolioLot,
  PortfolioPosition,
  RealizedGain,
} from '../../types/portfolio'

type QueryLike<T> = {
  data?: T
  error: string | null
  loading: boolean
}

export function PortfolioSummary({
  pnlPercent,
  positions,
  totalPnl,
  totalValue,
}: {
  pnlPercent?: number
  positions: PortfolioPosition[]
  totalPnl: number
  totalValue: number
}) {
  return (
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
  )
}

export function HoldingsTable({
  onDelete,
  onEdit,
  onSelect,
  portfolio,
  positions,
  saving,
  selectedSymbol,
}: {
  onDelete: (symbol: string) => void
  onEdit: (position: PortfolioPosition) => void
  onSelect: (position: PortfolioPosition) => void
  portfolio: QueryLike<unknown>
  positions: PortfolioPosition[]
  saving: boolean
  selectedSymbol: string
}) {
  return (
    <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
      <SectionHeader eyebrow="Holdings" title="Open positions" />
      {portfolio.loading ? (
        <StatePanel title="Loading portfolio" description="Reading holdings." />
      ) : portfolio.error ? (
        <StatePanel title="Portfolio unavailable" description={portfolio.error} />
      ) : positions.length ? (
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <caption className="sr-only">Open portfolio positions with quantity, price, value, signal, and actions</caption>
            <thead className="text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2">Symbol</th>
                <th className="px-3 py-2">Qty</th>
                <th className="px-3 py-2">Avg</th>
                <th className="px-3 py-2">Price</th>
                <th className="px-3 py-2">Value</th>
                <th className="px-3 py-2">P&L</th>
                <th className="px-3 py-2">Signal</th>
                <th className="px-3 py-2">Actions</th>
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
                    onClick={() => onSelect(position)}
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
                        <IconButton
                          className="h-8 min-w-8 px-2 text-xs"
                          label={`Edit ${position.symbol}`}
                          onClick={(event) => {
                            event.stopPropagation()
                            onEdit(position)
                          }}
                        >
                          Edit
                        </IconButton>
                        <IconButton
                          className="h-8 min-w-8 px-2 text-xs"
                          disabled={saving}
                          label={`Delete ${position.symbol}`}
                          onClick={(event) => {
                            event.stopPropagation()
                            onDelete(position.symbol)
                          }}
                          tone="danger"
                        >
                          Delete
                        </IconButton>
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
  )
}

export function PositionFormPanel({
  editingSymbol,
  errors,
  form,
  onCancel,
  onChange,
  onSubmit,
  saving,
}: {
  editingSymbol: string | null
  errors: FieldErrors<keyof PositionForm>
  form: PositionForm
  onCancel: () => void
  onChange: (form: PositionForm) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  saving: boolean
}) {
  return (
    <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
      <SectionHeader eyebrow={editingSymbol ? 'Edit' : 'Add'} title="Position" />
      <form className="mt-4 space-y-3" onSubmit={onSubmit}>
        <label className="sr-only" htmlFor="position-symbol">Symbol</label>
        <input
          id="position-symbol"
          aria-describedby={errors.symbol ? 'position-symbol-error' : undefined}
          aria-invalid={Boolean(errors.symbol)}
          className="h-10 w-full rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-white outline-none focus:border-cyan-300/50"
          disabled={Boolean(editingSymbol)}
          onChange={(event) => onChange({ ...form, symbol: event.target.value })}
          placeholder="Symbol, e.g. INFY"
          required
          value={form.symbol}
        />
        {errors.symbol ? <div className="text-xs text-rose-200" id="position-symbol-error">{errors.symbol}</div> : null}
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="sr-only" htmlFor="position-quantity">Quantity</label>
            <input
              id="position-quantity"
              aria-describedby={errors.quantity ? 'position-quantity-error' : undefined}
              aria-invalid={Boolean(errors.quantity)}
              className="h-10 w-full rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-white outline-none focus:border-cyan-300/50"
              min="0"
              onChange={(event) => onChange({ ...form, quantity: event.target.value })}
              placeholder="Quantity"
              required
              step="any"
              type="number"
              value={form.quantity}
            />
            {errors.quantity ? <div className="mt-1 text-xs text-rose-200" id="position-quantity-error">{errors.quantity}</div> : null}
          </div>
          <div>
            <label className="sr-only" htmlFor="position-avg-price">Average price</label>
            <input
              id="position-avg-price"
              aria-describedby={errors.avgPrice ? 'position-avg-price-error' : undefined}
              aria-invalid={Boolean(errors.avgPrice)}
              className="h-10 w-full rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-white outline-none focus:border-cyan-300/50"
              min="0"
              onChange={(event) => onChange({ ...form, avgPrice: event.target.value })}
              placeholder="Average price"
              required
              step="any"
              type="number"
              value={form.avgPrice}
            />
            {errors.avgPrice ? <div className="mt-1 text-xs text-rose-200" id="position-avg-price-error">{errors.avgPrice}</div> : null}
          </div>
        </div>
        <label className="sr-only" htmlFor="position-purchase-date">Purchase date</label>
        <input
          id="position-purchase-date"
          className="h-10 w-full rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-white outline-none focus:border-cyan-300/50"
          onChange={(event) => onChange({ ...form, purchaseDate: event.target.value })}
          type="date"
          value={form.purchaseDate}
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
            <button className="rounded-md border border-white/10 px-3 py-2 text-sm text-slate-300" onClick={onCancel} type="button">
              Cancel
            </button>
          ) : null}
        </div>
      </form>
    </section>
  )
}

export function LotsTable({
  lots,
  selectedSymbol,
}: {
  lots: QueryLike<PortfolioCollection<PortfolioLot>>
  selectedSymbol: string
}) {
  return (
    <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
      <SectionHeader eyebrow="Lots" title={selectedSymbol ? `${selectedSymbol} open lots` : 'Open lots'} />
      <div className="mt-4 overflow-x-auto">
        {lots.loading ? (
          <StatePanel title="Loading lots" description="Reading open tax lots." />
        ) : lots.data?.data.length ? (
          <table className="min-w-full text-left text-sm">
            <caption className="sr-only">Open tax lots filtered by selected symbol</caption>
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
  )
}

export function SellSimulator({
  errors,
  form,
  onChange,
  onSubmit,
  result,
  saving,
}: {
  errors: FieldErrors<keyof SellForm>
  form: SellForm
  onChange: (form: SellForm) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  result: Record<string, unknown> | null
  saving: boolean
}) {
  return (
    <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
      <SectionHeader eyebrow="Sell" title="Simulation" />
      <form className="mt-4 grid gap-3 sm:grid-cols-2" onSubmit={onSubmit}>
        <label className="sr-only" htmlFor="sell-symbol">Sell symbol</label>
        <input
          id="sell-symbol"
          aria-describedby={errors.symbol ? 'sell-symbol-error' : undefined}
          aria-invalid={Boolean(errors.symbol)}
          className="h-10 rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-white outline-none focus:border-cyan-300/50"
          onChange={(event) => onChange({ ...form, symbol: event.target.value })}
          placeholder="Symbol"
          required
          value={form.symbol}
        />
        <label className="sr-only" htmlFor="sell-quantity">Sell quantity</label>
        <input
          id="sell-quantity"
          aria-describedby={errors.quantity ? 'sell-quantity-error' : undefined}
          aria-invalid={Boolean(errors.quantity)}
          className="h-10 rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-white outline-none focus:border-cyan-300/50"
          min="0"
          onChange={(event) => onChange({ ...form, quantity: event.target.value })}
          placeholder="Quantity"
          required
          step="any"
          type="number"
          value={form.quantity}
        />
        <label className="sr-only" htmlFor="sell-price">Sell price</label>
        <input
          id="sell-price"
          aria-describedby={errors.sellPrice ? 'sell-price-error' : undefined}
          aria-invalid={Boolean(errors.sellPrice)}
          className="h-10 rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-white outline-none focus:border-cyan-300/50"
          min="0"
          onChange={(event) => onChange({ ...form, sellPrice: event.target.value })}
          placeholder="Sell price"
          required
          step="any"
          type="number"
          value={form.sellPrice}
        />
        <label className="sr-only" htmlFor="sell-fees">Fees</label>
        <input
          id="sell-fees"
          className="h-10 rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-white outline-none focus:border-cyan-300/50"
          min="0"
          onChange={(event) => onChange({ ...form, fees: event.target.value })}
          placeholder="Fees"
          step="any"
          type="number"
          value={form.fees}
        />
        <label className="sr-only" htmlFor="sell-date">Sell date</label>
        <input
          id="sell-date"
          className="h-10 rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-white outline-none focus:border-cyan-300/50"
          onChange={(event) => onChange({ ...form, sellDate: event.target.value })}
          type="date"
          value={form.sellDate}
        />
        <button
          className="h-10 rounded-md bg-cyan-300 px-3 text-sm font-medium text-slate-950 disabled:opacity-50"
          disabled={saving}
          type="submit"
        >
          Simulate FIFO/LIFO/HIFO
        </button>
        {errors.symbol ? <div className="text-xs text-rose-200" id="sell-symbol-error">{errors.symbol}</div> : null}
        {errors.quantity ? <div className="text-xs text-rose-200" id="sell-quantity-error">{errors.quantity}</div> : null}
        {errors.sellPrice ? <div className="text-xs text-rose-200" id="sell-price-error">{errors.sellPrice}</div> : null}
      </form>
      {result ? <SellSimulationResult result={result} /> : null}
    </section>
  )
}

export function GainsTaxIntelligencePanel({
  insights,
  intelligence,
  metricEntries,
  realized,
  selectedSymbol,
  taxSummary,
}: {
  insights: QueryLike<Record<string, unknown>>
  intelligence: QueryLike<Record<string, unknown>>
  metricEntries: [string, unknown][]
  realized: QueryLike<PortfolioCollection<RealizedGain>>
  selectedSymbol: string
  taxSummary: QueryLike<Record<string, unknown>>
}) {
  return (
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
        <TaxSummaryPanel data={taxSummary.data ?? null} />
      </section>

      <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
        <SectionHeader eyebrow="Intelligence" title="Snapshot" />
        <div className="mt-4 space-y-3">
          {metricEntries.map(([key, value]) => (
            <div className="flex justify-between rounded-md bg-white/[0.04] px-3 py-2 text-sm" key={key}>
              <span className="text-slate-400">{titleize(key)}</span>
              <span className="font-medium text-white">{formatNumber(value)}</span>
            </div>
          ))}
          {selectedSymbol && insights.data ? (
            <div>
              <div className="mb-2 text-xs uppercase text-slate-500">{selectedSymbol} lot insight</div>
              <KeyValueList data={asRecord(insights.data.fy_summary)} limit={4} />
            </div>
          ) : null}
          <IntelligencePanel data={intelligence.data ?? null} />
        </div>
      </section>
    </div>
  )
}
