import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { cx } from '../utils/format'

type IconButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  label: string
  tone?: 'default' | 'danger' | 'primary'
  children: ReactNode
}

export function IconButton({ children, className, label, tone = 'default', type = 'button', ...props }: IconButtonProps) {
  const toneClass =
    tone === 'primary'
      ? 'border-cyan-300/30 bg-cyan-300/10 text-cyan-100 hover:bg-cyan-300/15'
      : tone === 'danger'
        ? 'border-rose-400/30 text-rose-200 hover:bg-rose-400/10'
        : 'border-white/10 text-slate-200 hover:border-cyan-300/40'

  return (
    <button
      aria-label={label}
      className={cx(
        'nexus-action-btn disabled:cursor-not-allowed disabled:opacity-50',
        toneClass,
        className,
      )}
      title={label}
      type={type}
      {...props}
    >
      {children}
    </button>
  )
}
