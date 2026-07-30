export type Validator<T> = (value: unknown, label?: string) => T

export function recordOf(value: unknown, label = 'response'): Record<string, unknown> {
  if (value && typeof value === 'object' && !Array.isArray(value)) return value as Record<string, unknown>
  throw new Error(`${label} was not a JSON object.`)
}

export function optionalRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

export function arrayOf<T>(
  value: unknown,
  itemValidator: Validator<T> = passthrough as Validator<T>,
  label = 'response',
): T[] {
  if (!Array.isArray(value)) throw new Error(`${label} was not an array.`)
  return value.map((item, index) => itemValidator(item, `${label}[${index}]`))
}

export function optionalArray<T>(value: unknown, itemValidator: Validator<T> = passthrough as Validator<T>) {
  return Array.isArray(value) ? value.map((item, index) => itemValidator(item, `item[${index}]`)) : []
}

export function stringField(value: unknown, fallback = '') {
  return typeof value === 'string' ? value : fallback
}

export function numberField(value: unknown) {
  const number = Number(value)
  return Number.isFinite(number) ? number : undefined
}

function passthrough<T>(value: unknown) {
  return value as T
}
