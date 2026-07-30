export type QueryKey = string | readonly unknown[]

type CacheEntry<T> = {
  data?: T
  error?: string
  updatedAt: number
}

const cache = new Map<string, CacheEntry<unknown>>()
const listeners = new Map<string, Set<() => void>>()

export function serializeQueryKey(key: QueryKey) {
  return typeof key === 'string' ? key : JSON.stringify(key)
}

export function readQueryCache<T>(key: QueryKey): CacheEntry<T> | undefined {
  return cache.get(serializeQueryKey(key)) as CacheEntry<T> | undefined
}

export function writeQueryCache<T>(key: QueryKey, entry: CacheEntry<T>) {
  cache.set(serializeQueryKey(key), entry)
}

export function subscribeQuery(key: QueryKey, listener: () => void) {
  const keyString = serializeQueryKey(key)
  const existing = listeners.get(keyString) ?? new Set<() => void>()
  existing.add(listener)
  listeners.set(keyString, existing)
  return () => {
    existing.delete(listener)
    if (!existing.size) listeners.delete(keyString)
  }
}

export function invalidateQueries(prefix?: QueryKey) {
  const prefixString = prefix === undefined ? undefined : serializeQueryKey(prefix)
  for (const [key, entry] of cache.entries()) {
    if (!prefixString || queryKeyMatches(key, prefixString)) {
      cache.set(key, { ...entry, updatedAt: 0 })
      notifyQuery(key)
    }
  }
}

function queryKeyMatches(key: string, prefix: string) {
  if (key === prefix) return true
  if (!prefix.endsWith(']')) return key.startsWith(prefix)
  return key.startsWith(`${prefix.slice(0, -1)},`)
}

function notifyQuery(key: string) {
  for (const listener of listeners.get(key) ?? []) listener()
}
