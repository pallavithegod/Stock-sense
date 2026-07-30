import { useCallback } from 'react'
import {
  getPortfolioIntelligenceSuite,
  getPortfolioLotInsights,
  getPortfolioLots,
  getPortfolioState,
  getPortfolioTaxSummary,
  getRealizedGains,
} from '../../api/portfolio'
import { useQuery } from '../../query/useQuery'

export function usePortfolioQueries(selectedSymbol: string) {
  const loadPortfolio = useCallback((signal: AbortSignal) => getPortfolioState({ signal }), [])
  const loadLots = useCallback(
    (signal: AbortSignal) => getPortfolioLots(selectedSymbol || undefined, { signal }),
    [selectedSymbol],
  )
  const loadRealized = useCallback(
    (signal: AbortSignal) => getRealizedGains(selectedSymbol || undefined, { signal }),
    [selectedSymbol],
  )
  const loadTaxSummary = useCallback((signal: AbortSignal) => getPortfolioTaxSummary({ signal }), [])
  const loadInsights = useCallback(
    (signal: AbortSignal) => getPortfolioLotInsights(selectedSymbol || undefined, { signal }),
    [selectedSymbol],
  )
  const loadIntelligence = useCallback((signal: AbortSignal) => getPortfolioIntelligenceSuite({ signal }), [])

  return {
    insights: useQuery({
      key: ['portfolio', 'insights', selectedSymbol || 'all'],
      queryFn: loadInsights,
      retry: 1,
      staleMs: 30_000,
    }),
    intelligence: useQuery({
      key: ['portfolio', 'intelligence'],
      queryFn: loadIntelligence,
      retry: 1,
      staleMs: 30_000,
    }),
    lots: useQuery({
      key: ['portfolio', 'lots', selectedSymbol || 'all'],
      queryFn: loadLots,
      retry: 1,
      staleMs: 30_000,
    }),
    portfolio: useQuery({
      key: ['portfolio', 'state'],
      queryFn: loadPortfolio,
      retry: 1,
      staleMs: 30_000,
    }),
    realized: useQuery({
      key: ['portfolio', 'realized', selectedSymbol || 'all'],
      queryFn: loadRealized,
      retry: 1,
      staleMs: 30_000,
    }),
    taxSummary: useQuery({
      key: ['portfolio', 'tax-summary'],
      queryFn: loadTaxSummary,
      retry: 1,
      staleMs: 30_000,
    }),
  }
}
