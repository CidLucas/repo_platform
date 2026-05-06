import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

interface ActionBarProps {
  left?: ReactNode
  right?: ReactNode
  className?: string
}

/**
 * Horizontal action bar — left slot for primary actions, right for secondary.
 * Used inside DeskSurface section headers.
 */
export function ActionBar({ left, right, className }: ActionBarProps) {
  return (
    <div className={cn('flex items-center justify-between gap-3', className)}>
      <div className="flex items-center gap-2">{left}</div>
      <div className="flex items-center gap-2">{right}</div>
    </div>
  )
}
