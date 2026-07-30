import { useCallback, useState } from 'react'
import { getAlerts, getMarketNews, getSymbolNews } from '../api/news'
import { MetricCard } from '../components/MetricCard'
import { SectionHeader } from '../components/SectionHeader'
import { StatePanel } from '../components/StatePanel'
import { useQuery } from '../query/useQuery'
import { formatNumber } from '../utils/format'
import { AlertsList, ArticleCard } from './news/NewsPresentation'
import { asArray, asRecord, sentimentTone } from './news/newsView'

export function NewsPage() {
  const [symbol, setSymbol] = useState('')
  const [submittedSymbol, setSubmittedSymbol] = useState('')
  const loadMarketNews = useCallback((signal: AbortSignal) => getMarketNews({ signal }), [])
  const loadAlerts = useCallback((signal: AbortSignal) => getAlerts({ signal }), [])
  const loadSymbolNews = useCallback(
    (signal: AbortSignal) => getSymbolNews(submittedSymbol, { signal }),
    [submittedSymbol],
  )
  const marketNews = useQuery({
    key: ['news', 'market'],
    queryFn: loadMarketNews,
    retry: 1,
    staleMs: 60_000,
  })
  const alerts = useQuery({
    key: ['news', 'alerts'],
    queryFn: loadAlerts,
    retry: 1,
    staleMs: 60_000,
  })
  const symbolNews = useQuery({
    enabled: Boolean(submittedSymbol),
    key: ['news', 'symbol', submittedSymbol],
    queryFn: loadSymbolNews,
    retry: 1,
    staleMs: 60_000,
  })

  const sentiment = asRecord(marketNews.data?.sentiment)
  const articles = marketNews.data?.articles ?? []
  const symbolArticles = symbolNews.data?.articles ?? []
  const sectors = Object.entries(asRecord(marketNews.data?.sectorwise)).slice(0, 6)
  const heatmap = asArray(marketNews.data?.heatmap ?? sentiment.heatmap).slice(0, 6)

  return (
    <div className="mx-auto max-w-7xl">
      <div className="mb-6">
        <div className="text-sm font-medium uppercase text-cyan-300">News</div>
        <h1 className="mt-1 text-2xl font-semibold text-white">Market News Desk</h1>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        <MetricCard
          metric={{
            label: 'Sentiment',
            value: String(sentiment.label ?? marketNews.data?.label ?? 'neutral'),
            detail: `${formatNumber(sentiment.total_articles ?? articles.length)} articles`,
            tone: sentimentTone(sentiment.label ?? marketNews.data?.label),
          }}
        />
        <MetricCard
          metric={{
            label: 'Score',
            value: formatNumber(sentiment.overall_score ?? marketNews.data?.sentiment_score),
          }}
        />
        <MetricCard
          metric={{
            label: 'Confidence',
            value: formatNumber(sentiment.confidence ?? marketNews.data?.confidence),
          }}
        />
        <MetricCard
          metric={{
            label: 'Triggered alerts',
            value: alerts.data?.triggered_today ?? 0,
            detail: `${alerts.data?.active_alerts ?? 0} active`,
            tone: (alerts.data?.triggered_today ?? 0) > 0 ? 'warning' : 'neutral',
          }}
        />
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-[1.3fr_0.8fr]">
        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <SectionHeader eyebrow="Market" title="Latest articles" />
          <div className="mt-4 space-y-3">
            {marketNews.loading ? (
              <StatePanel title="Loading news" description="Fetching market news." />
            ) : marketNews.error ? (
              <StatePanel title="News unavailable" description={marketNews.error} />
            ) : articles.length ? (
              articles.slice(0, 8).map((article, index) => <ArticleCard article={article} key={`${article.title}-${index}`} />)
            ) : (
              <StatePanel title="No news" description="No market news is available right now." />
            )}
          </div>
        </section>

        <aside className="space-y-4">
          <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
            <SectionHeader eyebrow="Symbol" title="Focused news" />
            <form
              className="mt-4 flex gap-2"
              onSubmit={(event) => {
                event.preventDefault()
                setSubmittedSymbol(symbol.trim().toUpperCase())
              }}
            >
              <label className="sr-only" htmlFor="news-symbol">
                Stock symbol
              </label>
              <input
                id="news-symbol"
                className="h-10 min-w-0 flex-1 rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-white outline-none focus:border-cyan-300/50"
                onChange={(event) => setSymbol(event.target.value)}
                placeholder="INFY, TCS..."
                value={symbol}
              />
              <button className="rounded-md bg-cyan-300 px-3 text-sm font-medium text-slate-950" type="submit">
                Search
              </button>
            </form>
            <div className="mt-4 space-y-3">
              {submittedSymbol && symbolNews.loading ? (
                <StatePanel title="Loading symbol news" description={`Fetching ${submittedSymbol} coverage.`} />
              ) : submittedSymbol && symbolNews.error ? (
                <StatePanel title="Symbol news unavailable" description={symbolNews.error} />
              ) : submittedSymbol && symbolArticles.length ? (
                symbolArticles.slice(0, 4).map((article, index) => <ArticleCard article={article} key={`${article.title}-${index}`} />)
              ) : (
                <StatePanel title="No symbol selected" description="Search a symbol to load focused news." />
              )}
            </div>
          </section>

          <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
            <SectionHeader eyebrow="Alerts" title="Active watches" />
            <div className="mt-4">
              {alerts.loading ? (
                <StatePanel title="Loading alerts" description="Checking active alert rows." />
              ) : alerts.error ? (
                <StatePanel title="Alerts unavailable" description={alerts.error} />
              ) : (
                <AlertsList alerts={alerts.data?.alerts ?? []} />
              )}
            </div>
          </section>
        </aside>
      </div>

      <div className="mt-5 grid gap-4 xl:grid-cols-2">
        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <SectionHeader eyebrow="Sectors" title="Sector sentiment" />
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {sectors.length ? (
              sectors.map(([sector, value]) => (
                <div className="rounded-md bg-slate-950/40 p-3" key={sector}>
                  <div className="font-medium text-white">{sector}</div>
                  <div className="mt-1 text-xs text-slate-500">{String(value).slice(0, 120)}</div>
                </div>
              ))
            ) : (
              <StatePanel title="No sector data" description="Sector sentiment is not available yet." />
            )}
          </div>
        </section>

        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <SectionHeader eyebrow="Heatmap" title="Sentiment heat" />
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {heatmap.length ? (
              heatmap.map((item, index) => {
                const row = asRecord(item)
                return (
                  <div className="rounded-md bg-slate-950/40 p-3" key={index}>
                    <div className="font-medium text-white">{String(row.label ?? row.sector ?? `Signal ${index + 1}`)}</div>
                    <div className="mt-1 text-xs text-slate-500">
                      Score {formatNumber(row.score ?? row.value)} | {String(row.sentiment ?? '')}
                    </div>
                  </div>
                )
              })
            ) : (
              <StatePanel title="No heatmap" description="Sentiment heatmap data is not available yet." />
            )}
          </div>
        </section>
      </div>
    </div>
  )
}
