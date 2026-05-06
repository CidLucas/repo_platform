import { cn } from '@/utils/cn'

type PillVariant = 'urgent' | 'attention' | 'ok' | 'info' | 'neutral'

interface StatusPillProps {
  variant?: PillVariant
  children: React.ReactNode
  className?: string
}

const variantClasses: Record<PillVariant, string> = {
  urgent: 'bg-urgent/15 text-urgent border border-urgent/30',
  attention: 'bg-attention/15 text-attention border border-attention/30',
  ok: 'bg-ok/15 text-ok border border-ok/30',
  info: 'bg-blu-500/15 text-blu-400 border border-blu-500/30',
  neutral: 'bg-elevated text-gray-300 border border-border',
}

export function StatusPill({ variant = 'neutral', children, className }: StatusPillProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full',
        'text-caption-sm font-medium',
        variantClasses[variant],
        className
      )}
    >
      {children}
    </span>
  )
}
