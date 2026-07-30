import type { StockSearchResult } from '../types/stock'

function compact(value: string | undefined) {
  return (value ?? '').toUpperCase().replace(/\.NS$|\.BO$/g, '').replace(/[^A-Z0-9]/g, '')
}

export function searchRank(query: string, stock: StockSearchResult) {
  const q = compact(query)
  const symbol = compact(stock.symbol)
  const display = compact(stock.display)
  const name = compact(stock.name)

  if (!q) return 99
  if (symbol === q || display === q) return 0
  if (symbol.startsWith(q) || display.startsWith(q)) return 1
  if (name.startsWith(q)) return 2
  if (symbol.includes(q) || display.includes(q)) return 3
  if (name.includes(q)) return 4
  return 99
}

export function normalizeSearchResults(query: string, results: StockSearchResult[], limit: number) {
  return results
    .filter((stock) => searchRank(query, stock) < 99)
    .sort((a, b) => {
      const rankDelta = searchRank(query, a) - searchRank(query, b)
      if (rankDelta !== 0) return rankDelta
      const aSymbol = compact(a.display || a.symbol)
      const bSymbol = compact(b.display || b.symbol)
      const lengthDelta = Math.abs(aSymbol.length - compact(query).length) - Math.abs(bSymbol.length - compact(query).length)
      if (lengthDelta !== 0) return lengthDelta
      return aSymbol.localeCompare(bSymbol)
    })
    .slice(0, limit)
}
