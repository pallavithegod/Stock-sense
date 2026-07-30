import type {
  PortfolioLot,
  PortfolioMutationPayload,
  PortfolioPosition,
  RealizedGain,
  SellSimulationPayload,
} from '../../types/portfolio'

export type PositionForm = {
  symbol: string
  quantity: string
  avgPrice: string
  purchaseDate: string
}

export type SellForm = {
  symbol: string
  quantity: string
  sellPrice: string
  fees: string
  sellDate: string
}

export type FieldErrors<T extends string> = Partial<Record<T, string>>

export const emptyPositionForm: PositionForm = {
  symbol: '',
  quantity: '',
  avgPrice: '',
  purchaseDate: '',
}

export const emptySellForm: SellForm = {
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

export function firstNumber(record: Record<string, unknown> | undefined, keys: string[]) {
  for (const key of keys) {
    const value = toNumber(record?.[key])
    if (value !== undefined) return value
  }
  return undefined
}

export function positionQuantity(position: PortfolioPosition) {
  return firstNumber(position, ['open_qty', 'quantity', 'qty'])
}

export function positionAverage(position: PortfolioPosition) {
  return firstNumber(position, ['avg_price', 'price', 'buy_price'])
}

export function positionValue(position: PortfolioPosition) {
  return firstNumber(position, ['current_value', 'market_value', 'value'])
}

export function positionPnl(position: PortfolioPosition) {
  return firstNumber(position, ['pnl', 'unrealized_pnl', 'unrealized_total'])
}

export function positionPnlPercent(position: PortfolioPosition) {
  const explicit = firstNumber(position, ['pnl_percent', 'unrealized_pnl_percent'])
  if (explicit !== undefined) return explicit

  const pnl = positionPnl(position)
  const quantity = positionQuantity(position)
  const average = positionAverage(position)
  const cost = quantity !== undefined && average !== undefined ? quantity * average : undefined
  return pnl !== undefined && cost ? (pnl / cost) * 100 : undefined
}

export function lotId(lot: PortfolioLot) {
  return lot.id ?? lot.lot_id ?? `${lot.symbol ?? 'LOT'}-${lot.buy_date ?? lot.purchase_date ?? ''}`
}

export function lotQuantity(lot: PortfolioLot) {
  return firstNumber(lot, ['open_qty', 'remaining_quantity', 'quantity', 'qty', 'original_quantity'])
}

export function lotPrice(lot: PortfolioLot) {
  return firstNumber(lot, ['buy_price', 'avg_price', 'purchase_price'])
}

export function lotDate(lot: PortfolioLot) {
  return String(lot.buy_date ?? lot.purchase_date ?? lot.added_date ?? '--')
}

export function gainValue(gain: RealizedGain) {
  return firstNumber(gain, ['realized_gain', 'gain', 'pnl'])
}

export function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

export function titleize(value: string) {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (match) => match.toUpperCase())
}

export function payloadFromForm(form: PositionForm): PortfolioMutationPayload {
  return {
    symbol: form.symbol.trim().toUpperCase(),
    quantity: Number(form.quantity),
    avg_price: Number(form.avgPrice),
    purchase_date: form.purchaseDate || undefined,
  }
}

export function sellPayloadFromForm(form: SellForm): SellSimulationPayload {
  return {
    symbol: form.symbol.trim().toUpperCase(),
    quantity: Number(form.quantity),
    sell_price: Number(form.sellPrice),
    sell_date: form.sellDate || undefined,
    fees: Number(form.fees || 0),
    methods: ['FIFO', 'LIFO', 'HIFO'],
  }
}
