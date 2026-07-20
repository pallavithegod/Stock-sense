type SectionHeaderProps = {
  title: string
  eyebrow?: string
  action?: React.ReactNode
}

export function SectionHeader({ title, eyebrow, action }: SectionHeaderProps) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        {eyebrow ? <div className="text-xs font-medium uppercase text-cyan-300">{eyebrow}</div> : null}
        <h2 className="mt-1 text-base font-semibold text-white">{title}</h2>
      </div>
      {action}
    </div>
  )
}
