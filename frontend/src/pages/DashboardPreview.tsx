import { getLiveDashboard } from '../api/dashboard'
import { MetricCard } from '../components/MetricCard'
import { StatePanel } from '../components/StatePanel'
import { useAsync } from '../hooks/useAsync'
import { formatNumber } from '../utils/format'
import type { DashboardMetric } from '../types/dashboard'

function buildMetrics(data: Record<string, unknown> | null): DashboardMetric[] {
  const portfolioValue =
    data?.portfolioValue ?? data?.portfolio_value ?? data?.total_value ?? data?.totalPortfolioValue
  const activePositions = data?.activePositions ?? data?.active_positions
  const marketStatus = data?.marketStatus ?? data?.market_status ?? data?.status

  return [
    {
      label: 'Portfolio value',
      value: portfolioValue ? formatNumber(portfolioValue) : '--',
      detail: 'Sourced from Flask dashboard payload',
      tone: 'positive',
    },
    {
      label: 'Active positions',
      value: activePositions ? formatNumber(activePositions) : '--',
      detail: 'Portfolio state will move into React later',
    },
    {
      label: 'Market status',
      value: marketStatus ? String(marketStatus) : 'Waiting',
      detail: 'Live API connection probe',
      tone: marketStatus ? 'neutral' : 'warning',
    },
  ]
}

export function DashboardPreview() {
  const { data, error, loading } = useAsync(() => getLiveDashboard(), [])
  const metrics = buildMetrics((data as Record<string, unknown> | null) ?? null)

  return (
    <div className="mx-auto max-w-7xl">
      <div className="grid gap-4 md:grid-cols-3">
        {metrics.map((metric) => (
          <MetricCard key={metric.label} metric={metric} />
        ))}
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-[1.4fr_0.8fr]">
        <section className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-base font-semibold text-white">Backend contract preview</h2>
              <p className="mt-1 text-sm text-slate-400">
                This shell keeps Flask as the API source while the React frontend is rebuilt.
              </p>
            </div>
            <div className="rounded-md bg-cyan-400/10 px-2 py-1 text-xs font-medium text-cyan-200">
              Phase 1
            </div>
          </div>

          <div className="mt-5 rounded-md bg-slate-900/80 p-4">
            {loading ? (
              <div className="text-sm text-slate-400">Checking Flask API...</div>
            ) : error ? (
              <div className="text-sm text-amber-200">
                Flask API is not reachable yet: {error}. Start `python app.py` and refresh.
              </div>
            ) : (
              <pre className="max-h-80 overflow-auto text-xs leading-6 text-slate-300">
                {JSON.stringify(data, null, 2)}
              </pre>
            )}
          </div>
        </section>

        <div className="space-y-4">
          <StatePanel
            description="The new frontend is intentionally thin: it fetches, validates shape gently, and displays. Finance and prediction logic stays in the backend."
            title="Migration rule"
          />
          <StatePanel
            description="Next phase will replace this preview with a proper dashboard page using the same API client and typed modules."
            title="Next checkpoint"
          />
        </div>
      </div>
    </div>
  )
}
