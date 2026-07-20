import { cx } from '../utils/format'
import type { DashboardMetric } from '../types/dashboard'

const toneClass: Record<NonNullable<DashboardMetric['tone']>, string> = {
  neutral: 'border-white/10 bg-white/[0.04]',
  positive: 'border-emerald-400/30 bg-emerald-400/[0.08]',
  negative: 'border-rose-400/30 bg-rose-400/[0.08]',
  warning: 'border-amber-300/30 bg-amber-300/[0.08]',
}

export function MetricCard({ metric }: { metric: DashboardMetric }) {
  return (
    <section className={cx('rounded-lg border p-4', toneClass[metric.tone ?? 'neutral'])}>
      <div className="text-xs font-medium uppercase text-slate-400">{metric.label}</div>
      <div className="mt-3 text-2xl font-semibold text-white">{metric.value}</div>
      {metric.detail ? <div className="mt-2 text-sm text-slate-400">{metric.detail}</div> : null}
    </section>
  )
}
