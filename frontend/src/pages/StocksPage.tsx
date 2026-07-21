import { useMemo, useState } from 'react'
import { getLivePrediction } from '../api/predictions'
import { getStocks, searchStocks } from '../api/stocks'
import { SectionHeader } from '../components/SectionHeader'
import { StatePanel } from '../components/StatePanel'
import { useAsync } from '../hooks/useAsync'
import { normalizeLivePrediction } from '../utils/predictionAdapter'
import { stockChange, stockDisplayName, stockDisplaySymbol, stockMetaLine, stockPrice } from '../utils/stockAdapter'
import { cx, formatNumber, formatPercent } from '../utils/format'
import type { StockSearchResult, StockSummary } from '../types/stock'

function changeClass(value?: number) {
  if (value === undefined) return 'text-slate-400'
  return value >= 0 ? 'text-emerald-300' : 'text-rose-300'
}

export function StocksPage() {
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState<StockSearchResult | StockSummary | null>(null)
  const popular = useAsync(() => getStocks(20), [])
  const normalizedQuery = query.trim()
  const search = useAsync(
    async () => ({
      query: normalizedQuery,
      results: normalizedQuery.length >= 2 ? await searchStocks(normalizedQuery, 30) : [],
    }),
    [normalizedQuery],
  )
  const livePrediction = useAsync(
    () => (selected ? getLivePrediction(stockDisplaySymbol(selected)) : Promise.resolve(null)),
    [selected],
  )

  const searchResults =
    normalizedQuery.length >= 2 && search.data?.query === normalizedQuery ? search.data.results : []
  const results = normalizedQuery.length >= 2 ? searchResults : popular.data ?? []
  const searchHasError = normalizedQuery.length >= 2 && Boolean(search.error)
  const searchIsPending =
    normalizedQuery.length >= 2 && !searchHasError && search.data?.query !== normalizedQuery
  const prediction = useMemo(
    () => normalizeLivePrediction(livePrediction.data),
    [livePrediction.data],
  )

  return (
    <div className="mx-auto max-w-7xl">
      <div className="mb-6">
        <div className="text-sm font-medium uppercase text-cyan-300">Universe</div>
        <h1 className="mt-1 text-2xl font-semibold text-white">Stock Search</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
          Search NSE/BSE symbols through the existing Flask market universe, then inspect live
          prediction horizons without leaving the React shell.
        </p>
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <SectionHeader eyebrow="Search" title="Find a stock" />
          <input
            className="mt-4 h-11 w-full rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-white outline-none placeholder:text-slate-500 focus:border-cyan-300/50"
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search RELIANCE, TCS, INFY..."
            value={query}
          />

          <div className="mt-4 space-y-2">
            {searchIsPending || (popular.loading && normalizedQuery.length < 2) ? (
              <StatePanel description="Loading stock universe from Flask." title="Syncing" />
            ) : searchHasError ? (
              <StatePanel
                description={`Search API failed: ${search.error}. Confirm Flask is running at http://127.0.0.1:5000.`}
                title="Search unavailable"
              />
            ) : results.length ? (
              results.map((stock) => (
                <button
                  className={cx(
                    'w-full rounded-md border p-3 text-left transition',
                    selected && stockDisplaySymbol(selected) === stockDisplaySymbol(stock)
                      ? 'border-cyan-300/40 bg-cyan-300/10'
                      : 'border-white/10 bg-slate-950/40 hover:border-white/20',
                  )}
                  key={`${stockDisplaySymbol(stock)}-${stockDisplayName(stock)}`}
                  onClick={() => setSelected(stock)}
                  type="button"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-medium text-white">{stockDisplaySymbol(stock)}</div>
                      <div className="mt-1 line-clamp-1 text-sm text-slate-400">
                        {stockDisplayName(stock)}
                      </div>
                    </div>
                    <div className={cx('text-sm font-medium', changeClass(stockChange(stock)))}>
                      {formatPercent(stockChange(stock))}
                    </div>
                  </div>
                  <div className="mt-2 text-xs text-slate-500">{stockMetaLine(stock)}</div>
                </button>
              ))
            ) : (
              <StatePanel
                description={normalizedQuery.length >= 2 ? 'No matching stocks found.' : 'Type at least two characters to search.'}
                title="No results"
              />
            )}
          </div>
        </section>

        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <SectionHeader eyebrow="Detail" title={selected ? stockDisplaySymbol(selected) : 'Select a stock'} />

          {selected ? (
            <div className="mt-5">
              <div className="rounded-lg border border-white/10 bg-slate-950/50 p-4">
                <div className="text-xl font-semibold text-white">{stockDisplayName(selected)}</div>
                <div className="mt-2 text-sm text-slate-400">{stockMetaLine(selected)}</div>
                <div className="mt-5 grid gap-3 sm:grid-cols-3">
                  <div className="rounded-md bg-white/[0.04] p-3">
                    <div className="text-xs uppercase text-slate-500">Price</div>
                    <div className="mt-2 text-lg font-semibold text-white">
                      {formatNumber(stockPrice(selected))}
                    </div>
                  </div>
                  <div className="rounded-md bg-white/[0.04] p-3">
                    <div className="text-xs uppercase text-slate-500">Change</div>
                    <div className={cx('mt-2 text-lg font-semibold', changeClass(stockChange(selected)))}>
                      {formatPercent(stockChange(selected))}
                    </div>
                  </div>
                  <div className="rounded-md bg-white/[0.04] p-3">
                    <div className="text-xs uppercase text-slate-500">Exchange</div>
                    <div className="mt-2 text-lg font-semibold text-white">
                      {'exchange' in selected ? selected.exchange ?? '--' : '--'}
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-4 rounded-lg border border-white/10 bg-slate-950/50 p-4">
                <SectionHeader eyebrow="Prediction" title="Live horizons" />
                {livePrediction.loading ? (
                  <div className="mt-4 text-sm text-slate-400">Loading prediction...</div>
                ) : prediction ? (
                  <div className="mt-4">
                    <div className="mb-4 flex flex-wrap gap-2 text-xs text-slate-400">
                      <span>Momentum: {prediction.momentum ?? '--'}</span>
                      <span>Volatility: {prediction.volatility ?? '--'}</span>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      {prediction.horizons.map((horizon) => (
                        <div className="rounded-md bg-white/[0.04] p-3" key={horizon.label}>
                          <div className="text-xs uppercase text-slate-500">{horizon.label}</div>
                          <div className="mt-2 text-lg font-semibold text-white">
                            {formatNumber(horizon.target)}
                          </div>
                          <div className={cx('mt-1 text-sm', changeClass(horizon.returnPercent))}>
                            {formatPercent(horizon.returnPercent)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <StatePanel
                    description="No live prediction payload is available for this symbol yet."
                    title="Prediction unavailable"
                  />
                )}
              </div>
            </div>
          ) : (
            <StatePanel
              description="Choose a stock from search results to load its detail and prediction horizons."
              title="Nothing selected"
            />
          )}
        </section>
      </div>
    </div>
  )
}
