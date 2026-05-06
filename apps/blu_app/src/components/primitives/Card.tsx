import { type HTMLAttributes, type ReactNode, type KeyboardEvent } from 'react'
import { cn } from '@/utils/cn'

type CardVariant = 'default' | 'hover' | 'active'
type CardAccent = 'blu' | 'ok' | 'urgent' | 'attention' | 'none'

const accentBorderMap: Record<Exclude<CardAccent, 'none'>, string> = {
  blu: 'border-l-blu-500',
  ok: 'border-l-ok',
  urgent: 'border-l-urgent',
  attention: 'border-l-attention',
}

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant
  accent?: CardAccent
  children?: ReactNode
  className?: string
  onClick?: () => void
}

export function Card({
  variant = 'default',
  accent = 'none',
  children,
  className,
  onClick,
  ...props
}: CardProps) {
  const isInteractive = typeof onClick === 'function'
  const hasAccent = accent !== 'none'

  function handleKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    if (isInteractive && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault()
      onClick?.()
    }
  }

  return (
    <div
      role={isInteractive ? 'button' : undefined}
      tabIndex={isInteractive ? 0 : undefined}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      className={cn(
        // Base
        'bg-surface border border-border rounded-md shadow',
        // Accent bar (left border)
        hasAccent && 'border-l-[3px] pl-[1px]',
        hasAccent && accentBorderMap[accent],
        // Hover variant
        variant === 'hover' && 'hover:bg-elevated hover:shadow-md hover:border-gray-500 transition-colors duration-normal cursor-pointer',
        // Active (selected) variant
        variant === 'active' && 'border-blu-500 shadow-glow-blu',
        // Interactive focus ring
        isInteractive && 'focus-visible:ring-2 focus-visible:ring-blu-500 focus-visible:ring-offset-1 focus-visible:ring-offset-base focus-visible:outline-none',
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}
