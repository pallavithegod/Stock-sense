type StatePanelProps = {
  title: string
  description: string
}

export function StatePanel({ title, description }: StatePanelProps) {
  return (
    <div className="nexus-state-panel">
      <div>{title}</div>
      <p>{description}</p>
    </div>
  )
}
