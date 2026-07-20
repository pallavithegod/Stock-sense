type StatePanelProps = {
  title: string
  description: string
}

export function StatePanel({ title, description }: StatePanelProps) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.04] p-6">
      <div className="text-sm font-semibold text-white">{title}</div>
      <p className="mt-2 text-sm leading-6 text-slate-400">{description}</p>
    </div>
  )
}
