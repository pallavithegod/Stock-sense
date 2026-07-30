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

export function formatDate(value: unknown, fallback = '--') {
  if (typeof value !== 'string' && typeof value !== 'number' && !(value instanceof Date)) return fallback
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return fallback
  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    timeZone: 'UTC',
    year: 'numeric',
  }).format(date)
}

export function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ')
}
