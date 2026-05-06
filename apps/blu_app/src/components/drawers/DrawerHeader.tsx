import type { ReactNode } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { cn } from '@/utils/cn'

interface DrawerHeaderProps {
  title: string
  side?: 'left' | 'right'
  /** Desktop: collapse toggle button */
  onCollapse?: () => void
  collapsed?: boolean
  /** Optional actions slot (right side of header) */
  actions?: ReactNode
  className?: string
}

export function DrawerHeader({
  title,
  side = 'left',
  onCollapse,
  collapsed,
  actions,
  className,
}: DrawerHeaderProps) {
  const CollapseIcon = collapsed
    ? side === 'left'
      ? ChevronRight
      : ChevronLeft
    : side === 'left'
      ? ChevronLeft
      : ChevronRight

  return (
    <div
      className={cn(
        'flex items-center justify-between gap-2 px-4 py-3',
        'border-b border-border shrink-0',
        className
      )}
    >
      <h3 className="text-heading-sm text-white font-medium truncate">{title}</h3>
      <div className="flex items-center gap-1">
        {actions}
        {onCollapse && (
          <button
            onClick={onCollapse}
            aria-label={collapsed ? 'Expandir painel' : 'Recolher painel'}
            className={cn(
              'w-7 h-7 flex items-center justify-center rounded',
              'text-gray-400 hover:text-white hover:bg-elevated',
              'transition-colors cursor-pointer',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500'
            )}
          >
            <CollapseIcon size={14} strokeWidth={1.5} />
          </button>
        )}
      </div>
    </div>
  )
}
