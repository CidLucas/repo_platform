import { type ReactNode } from 'react'
import { cn } from '@/utils/cn'

interface InsightActionProps {
  children: ReactNode
  onClick?: () => void
  variant?: 'primary' | 'ghost'
  className?: string
}

/**
 * Small CTA button inside an InsightCard.
 */
export function InsightAction({
  children,
  onClick,
  variant = 'ghost',
  className,
}: InsightActionProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded',
        'text-caption font-medium transition-colors cursor-pointer',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500',
        variant === 'primary'
          ? 'bg-blu-500/15 text-blu-300 hover:bg-blu-500/25 border border-blu-500/30'
          : 'text-gray-400 hover:text-white hover:bg-elevated border border-transparent',
        className
      )}
    >
      {children}
    </button>
  )
}
