import { type ReactNode } from 'react'
import { cn } from '@/utils/cn'

type BadgeVariant = 'ok' | 'urgent' | 'attention' | 'info'

interface BadgeProps {
  variant?: BadgeVariant
  count?: number
  children?: ReactNode
  className?: string
}

const statusClasses: Record<BadgeVariant, string> = {
  ok: 'bg-ok/10 text-ok border border-ok/20',
  urgent: 'bg-urgent/10 text-urgent border border-urgent/20',
  attention: 'bg-attention/10 text-attention border border-attention/20',
  info: 'bg-blu-500/10 text-blu-400 border border-blu-500/20',
}

export function Badge({ variant, count, children, className }: BadgeProps) {
  // Count mode — overrides everything else
  if (count !== undefined) {
    return (
      <span
        className={cn(
          'inline-flex items-center justify-center',
          'bg-urgent text-white rounded-full',
          'text-caption-sm font-medium px-1.5 py-0.5 min-w-[20px] text-center',
          'leading-none',
          className
        )}
      >
        {count > 99 ? '99+' : count}
      </span>
    )
  }

  // Status mode
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5',
        'text-caption-sm font-medium',
        variant ? statusClasses[variant] : statusClasses.info,
        className
      )}
    >
      {children}
    </span>
  )
}
