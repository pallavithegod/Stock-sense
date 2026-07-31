type StatePanelProps = {
  title: string
  description: string
}

export function StatePanel({ title, description }: StatePanelProps) {
  return (
    <div className="stocksense-state-panel">
      <div>{title}</div>
      <p>{description}</p>
    </div>
  )
}
