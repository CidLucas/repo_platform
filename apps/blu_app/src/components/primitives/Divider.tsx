import { cn } from '@/utils/cn'

interface DividerProps {
  orientation?: 'horizontal' | 'vertical'
  className?: string
}

export function Divider({ orientation = 'horizontal', className }: DividerProps) {
  if (orientation === 'vertical') {
    return (
      <div
        role="separator"
        aria-orientation="vertical"
        className={cn('w-px bg-border self-stretch', className)}
      />
    )
  }

  return (
    <hr
      role="separator"
      className={cn('border-0 border-t border-border', className)}
    />
  )
}
