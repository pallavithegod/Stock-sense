import { useState } from 'react'
import type { FormEvent } from 'react'
import {
  createPortfolioPosition,
  deletePortfolioPosition,
  simulatePortfolioSell,
  updatePortfolioPosition,
} from '../api/portfolio'
import { IconButton } from '../components/IconButton'
import { invalidateQueries } from '../query/useQuery'
import {
  GainsTaxIntelligencePanel,
  HoldingsTable,
  LotsTable,
  PortfolioSummary,
  PositionFormPanel,
  SellSimulator,
} from './portfolio/PortfolioSections'
import {
  emptyPositionForm,
  emptySellForm,
  firstNumber,
  payloadFromForm,
  positionAverage,
  positionPnl,
  positionQuantity,
  positionValue,
  sellPayloadFromForm,
} from './portfolio/portfolioView'
import type {
  PortfolioPosition,
} from '../types/portfolio'
import { usePortfolioQueries } from './portfolio/usePortfolioQueries'
import type { FieldErrors, PositionForm, SellForm } from './portfolio/portfolioView'

export function PortfolioPage() {
  const [selectedSymbol, setSelectedSymbol] = useState('')
  const [editingSymbol, setEditingSymbol] = useState<string | null>(null)
  const [positionForm, setPositionForm] = useState<PositionForm>(emptyPositionForm)
  const [sellForm, setSellForm] = useState<SellForm>(emptySellForm)
  const [mutationError, setMutationError] = useState<string | null>(null)
  const [mutationMessage, setMutationMessage] = useState<string | null>(null)
  const [positionErrors, setPositionErrors] = useState<FieldErrors<keyof PositionForm>>({})
  const [sellErrors, setSellErrors] = useState<FieldErrors<keyof SellForm>>({})
  const [saving, setSaving] = useState(false)
  const [sellResult, setSellResult] = useState<Record<string, unknown> | null>(null)

  const { insights, intelligence, lots, portfolio, realized, taxSummary } = usePortfolioQueries(selectedSymbol)

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
    setPositionErrors({})
    try {
      const payload = payloadFromForm(positionForm)
      const errors: FieldErrors<keyof PositionForm> = {}
      if (!payload.symbol) errors.symbol = 'Symbol is required.'
      if (!Number.isFinite(payload.quantity) || payload.quantity <= 0) errors.quantity = 'Quantity must be greater than zero.'
      if (!Number.isFinite(payload.avg_price) || payload.avg_price <= 0) errors.avgPrice = 'Average price must be greater than zero.'
      if (Object.keys(errors).length) {
        setPositionErrors(errors)
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
      invalidateQueries(['portfolio'])
    } catch (error) {
      setMutationError(error instanceof Error ? error.message : 'Portfolio save failed.')
    } finally {
      setSaving(false)
    }
  }

  async function removePosition(symbol: string) {
    if (!window.confirm(`Delete ${symbol} from the portfolio?`)) return
    setSaving(true)
    setMutationError(null)
    setMutationMessage(null)
    try {
      await deletePortfolioPosition(symbol)
      setMutationMessage(`${symbol} deleted.`)
      if (selectedSymbol === symbol) setSelectedSymbol('')
      invalidateQueries(['portfolio'])
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
    setSellErrors({})
    setSellResult(null)
    try {
      const payload = sellPayloadFromForm(sellForm)
      const errors: FieldErrors<keyof SellForm> = {}
      if (!payload.symbol) errors.symbol = 'Symbol is required.'
      if (!Number.isFinite(payload.quantity) || payload.quantity <= 0) errors.quantity = 'Quantity must be greater than zero.'
      if (!Number.isFinite(payload.sell_price) || payload.sell_price <= 0) errors.sellPrice = 'Sell price must be greater than zero.'
      if (Object.keys(errors).length) {
        setSellErrors(errors)
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
        <IconButton
          disabled={portfolio.refreshing}
          label="Refresh portfolio"
          onClick={() => invalidateQueries(['portfolio'])}
          tone="primary"
        >
          {portfolio.loading || portfolio.refreshing ? 'Syncing' : 'Refresh'}
        </IconButton>
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

      <PortfolioSummary
        pnlPercent={pnlPercent}
        positions={positions}
        totalPnl={totalPnl}
        totalValue={totalValue}
      />

      <div className="mt-5 grid gap-4 xl:grid-cols-[1.5fr_0.9fr]">
        <HoldingsTable
          onDelete={(symbol) => void removePosition(symbol)}
          onEdit={startEdit}
          onSelect={syncSellPosition}
          portfolio={portfolio}
          positions={positions}
          saving={saving}
          selectedSymbol={selectedSymbol}
        />
        <PositionFormPanel
          editingSymbol={editingSymbol}
          errors={positionErrors}
          form={positionForm}
          onCancel={() => {
            setEditingSymbol(null)
            setPositionForm(emptyPositionForm)
          }}
          onChange={setPositionForm}
          onSubmit={(event) => void submitPosition(event)}
          saving={saving}
        />
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-2">
        <LotsTable lots={lots} selectedSymbol={selectedSymbol} />
        <SellSimulator
          errors={sellErrors}
          form={sellForm}
          onChange={setSellForm}
          onSubmit={(event) => void submitSellSimulation(event)}
          result={sellResult}
          saving={saving}
        />
      </div>

      <GainsTaxIntelligencePanel
        insights={insights}
        intelligence={intelligence}
        metricEntries={metricEntries}
        realized={realized}
        selectedSymbol={selectedSymbol}
        taxSummary={taxSummary}
      />
    </div>
  )
}
