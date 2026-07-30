import { StatePanel } from '../../components/StatePanel'
import { cx, formatNumber } from '../../utils/format'
import { safeExternalUrl } from '../../utils/url'
import type { AlertItem, NewsArticle } from '../../types/news'

export function ArticleCard({ article }: { article: NewsArticle }) {
  const href = safeExternalUrl(article.url ?? article.link)
  return (
    <article className="rounded-lg border border-white/10 bg-slate-950/40 p-4">
      <div className="flex flex-wrap items-center gap-2 text-xs uppercase text-slate-500">
        <span>{article.source ?? article.publisher ?? 'Unknown source'}</span>
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
        <span>
          {String(article.normalized_time ?? article.published ?? article.published_at ?? article.providerPublishTime ?? '') || 'Recent'}
        </span>
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

export function AlertsList({ alerts }: { alerts: AlertItem[] }) {
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
