import { formatNumber, formatPercent } from './format'
import type {
  DashboardAlert,
  DashboardMetric,
  DashboardSignal,
  MarketIndex,
  NormalizedDashboard,
} from '../types/dashboard'

type AnyRecord = Record<string, unknown>

function isRecord(value: unknown): value is AnyRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function asArray(value: unknown): AnyRecord[] {
  if (Array.isArray(value)) return value.filter(isRecord)
  if (isRecord(value)) return Object.values(value).filter(isRecord)
  return []
}

function firstValue(...values: unknown[]) {
  return values.find((value) => value !== undefined && value !== null && value !== '')
}

function toNumber(value: unknown): number | undefined {
  const num = Number(value)
  return Number.isFinite(num) ? num : undefined
}

function toText(value: unknown): string | undefined {
  if (value === undefined || value === null || value === '') return undefined
  return String(value)
}

function normalizeIndices(raw: AnyRecord): MarketIndex[] {
  return asArray(firstValue(raw.live_indices, raw.indices, raw.market)).slice(0, 6).map((item) => ({
    name: toText(firstValue(item.name, item.label, item.symbol)) ?? 'Index',
    symbol: toText(item.symbol),
    price: toNumber(firstValue(item.price, item.value, item.last, item.close)),
    change: toNumber(firstValue(item.change, item.change_value)),
    changePercent: toNumber(firstValue(item.change_percent, item.changePercent, item.percent)),
  }))
}

function normalizeSignals(raw: AnyRecord): DashboardSignal[] {
  return asArray(firstValue(raw.top_stocks, raw.topStocks, raw.stocks, raw.opportunities))
    .slice(0, 8)
    .map((item) => ({
      symbol: toText(firstValue(item.symbol, item.ticker, item.name)) ?? 'UNKNOWN',
      price: toNumber(firstValue(item.current_price, item.price, item.last_price)),
      changePercent: toNumber(firstValue(item.change_percent, item.changePercent, item.return_percent)),
      signal: toText(firstValue(item.signal, item.action, item.recommendation)),
      confidence: toNumber(firstValue(item.confidence, item.score, item.probability)),
    }))
}

function normalizeAlerts(value: unknown): DashboardAlert[] {
  return asArray(value)
    .slice(0, 5)
    .map((item) => ({
      title: toText(firstValue(item.title, item.headline, item.message, item.symbol)) ?? 'Live alert',
      detail: toText(firstValue(item.detail, item.description, item.reason, item.action)),
      severity: toText(firstValue(item.severity, item.level, item.risk)),
      symbol: toText(item.symbol),
    }))
}

function normalizeNews(raw: AnyRecord): DashboardAlert[] {
  return asArray(firstValue(raw.news_items, raw.news, raw.articles))
    .slice(0, 5)
    .map((item) => ({
      title: toText(firstValue(item.title, item.headline)) ?? 'Market update',
      detail: toText(firstValue(item.source, item.publisher, item.summary, item.sentiment)),
      severity: toText(item.sentiment),
      symbol: toText(firstValue(item.related_symbol, item.symbol)),
    }))
}

function buildMetrics(raw: AnyRecord): DashboardMetric[] {
  const portfolioValue = firstValue(raw.portfolioValue, raw.portfolio_value)
  const activePositions = firstValue(raw.activePositions, raw.active_positions)
  const accuracy = firstValue(raw.directionalAccuracy, raw.directional_accuracy)
  const liquidity = firstValue(raw.liquidityScore, raw.liquidity_score)
  const bull = firstValue(raw.bull, isRecord(raw.marketSnapshot) ? raw.marketSnapshot.bull : undefined)
  const bear = firstValue(raw.bear, isRecord(raw.marketSnapshot) ? raw.marketSnapshot.bear : undefined)

  return [
    {
      label: 'Portfolio value',
      value: toNumber(portfolioValue) === undefined ? '--' : formatNumber(portfolioValue),
      detail: `${formatNumber(activePositions)} active positions`,
      tone: 'positive',
    },
    {
      label: 'Directional accuracy',
      value: toNumber(accuracy) === undefined ? '--' : formatPercent(accuracy),
      detail: 'Current AI performance signal',
    },
    {
      label: 'Liquidity score',
      value: toNumber(liquidity) === undefined ? '--' : formatNumber(liquidity),
      detail: 'Market execution quality proxy',
    },
    {
      label: 'Sentiment breadth',
      value: `${formatNumber(bull)} / ${formatNumber(bear)}`,
      detail: 'Bullish versus bearish news count',
      tone: toNumber(bull) && toNumber(bear) && Number(bull) < Number(bear) ? 'warning' : 'neutral',
    },
  ]
}

export function normalizeDashboard(payload: unknown): NormalizedDashboard {
  const raw = isRecord(payload) ? payload : {}
  return {
    metrics: buildMetrics(raw),
    indices: normalizeIndices(raw),
    signals: normalizeSignals(raw),
    alerts: normalizeAlerts(raw.alerts),
    news: normalizeNews(raw),
    lastUpdate: toText(firstValue(raw.lastUpdate, raw.last_update, raw.updated_at, raw.timestamp)),
    source: toText(raw.source),
    raw,
  }
}
