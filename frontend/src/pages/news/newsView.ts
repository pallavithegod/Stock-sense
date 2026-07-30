export function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

export function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : []
}

export function sentimentTone(label?: unknown) {
  const text = String(label ?? '').toLowerCase()
  if (text.includes('positive') || text.includes('bull')) return 'positive'
  if (text.includes('negative') || text.includes('bear')) return 'negative'
  return 'neutral'
}
