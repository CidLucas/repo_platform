import { cn } from '@/utils/cn'

interface RedDotProps {
  className?: string
  /** 'urgent' = red pulse, 'attention' = yellow pulse */
  variant?: 'urgent' | 'attention'
  size?: 'sm' | 'md'
}

/**
 * Pulsing indicator dot — absolutely positioned on parent container.
 * Parent must have `relative` positioning.
 */
export function RedDot({ className, variant = 'urgent', size = 'sm' }: RedDotProps) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        'absolute rounded-full animate-orb-attention',
        size === 'sm' ? 'w-2 h-2' : 'w-2.5 h-2.5',
        variant === 'urgent' ? 'bg-urgent' : 'bg-attention',
        className
      )}
    />
  )
}
