import { useState } from 'react'
import { getAlerts, getMarketNews, getSymbolNews } from '../api/news'
import { MetricCard } from '../components/MetricCard'
import { SectionHeader } from '../components/SectionHeader'
import { StatePanel } from '../components/StatePanel'
import { useAsync } from '../hooks/useAsync'
import { cx, formatNumber } from '../utils/format'
import type { AlertItem, NewsArticle } from '../types/news'

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : []
}

function sentimentTone(label?: unknown) {
  const text = String(label ?? '').toLowerCase()
  if (text.includes('positive') || text.includes('bull')) return 'positive'
  if (text.includes('negative') || text.includes('bear')) return 'negative'
  return 'neutral'
}

function articleTime(article: NewsArticle) {
  return String(article.normalized_time ?? article.published ?? article.published_at ?? article.providerPublishTime ?? '')
}

function articleSource(article: NewsArticle) {
  return article.source ?? article.publisher ?? 'Unknown source'
}

function ArticleCard({ article }: { article: NewsArticle }) {
  const href = article.url ?? article.link
  return (
    <article className="rounded-lg border border-white/10 bg-slate-950/40 p-4">
      <div className="flex flex-wrap items-center gap-2 text-xs uppercase text-slate-500">
        <span>{articleSource(article)}</span>
        {article.sentiment ? <span>{article.sentiment}</span> : null}
        {article.sector ? <span>{article.sector}</span> : null}
      </div>
      <h3 className="mt-2 text-base font-semibold leading-6 text-white">{article.title || 'Market update'}</h3>
      {article.description ? (
        <p className="mt-2 line-clamp-3 text-sm leading-6 text-slate-400">{article.description}</p>
      ) : null}
      {article.why_it_matters ? (
        <p className="mt-2 rounded-md bg-cyan-300/10 px-3 py-2 text-xs leading-5 text-cyan-100">
          {article.why_it_matters}
        </p>
      ) : null}
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500">
        <span>{articleTime(article) || 'Recent'}</span>
        <span>Reliability {formatNumber(article.source_reliability ?? article.confidence)}</span>
        {href ? (
          <a
            className="rounded-md border border-white/10 px-2 py-1 text-slate-200 hover:border-cyan-300/40"
            href={href}
            rel="noreferrer"
            target="_blank"
          >
            Open
          </a>
        ) : null}
      </div>
    </article>
  )
}

function AlertsList({ alerts }: { alerts: AlertItem[] }) {
  if (!alerts.length) {
    return <StatePanel title="No active alerts" description="No alert rows are currently active." />
  }
  return (
    <div className="space-y-2">
      {alerts.slice(0, 6).map((alert, index) => (
        <div
          className={cx(
            'rounded-md border p-3 text-sm',
            alert.triggered ? 'border-amber-300/30 bg-amber-300/10' : 'border-white/10 bg-slate-950/40',
          )}
          key={`${alert.symbol}-${index}`}
        >
          <div className="flex justify-between gap-3">
            <span className="font-medium text-white">{alert.symbol ?? 'Alert'}</span>
            <span className={alert.triggered ? 'text-amber-200' : 'text-slate-400'}>
              {alert.triggered ? 'Triggered' : 'Watching'}
            </span>
          </div>
          <div className="mt-1 text-xs text-slate-500">
            {alert.condition ?? '--'} {formatNumber(alert.target_value)} | Current{' '}
            {formatNumber(alert.current_value)}
          </div>
        </div>
      ))}
    </div>
  )
}

export function NewsPage() {
  const [symbol, setSymbol] = useState('')
  const [submittedSymbol, setSubmittedSymbol] = useState('')
  const marketNews = useAsync(() => getMarketNews(), [])
  const alerts = useAsync(() => getAlerts(), [])
  const symbolNews = useAsync(
    () => (submittedSymbol ? getSymbolNews(submittedSymbol) : Promise.resolve({ articles: [] })),
    [submittedSymbol],
  )

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
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
          Track market news, sentiment, symbol-specific coverage, and backend alerts from the Flask
          news intelligence layer.
        </p>
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
              <StatePanel title="Loading news" description="Fetching market news from Flask." />
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
              <input
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
