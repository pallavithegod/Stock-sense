export function formatNumber(value: unknown, fallback = '--') {
  const num = Number(value)
  if (!Number.isFinite(num)) return fallback
  return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(num)
}

export function formatPercent(value: unknown, fallback = '--') {
  const num = Number(value)
  if (!Number.isFinite(num)) return fallback
  return `${num >= 0 ? '+' : ''}${num.toFixed(2)}%`
}

export function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ')
}
