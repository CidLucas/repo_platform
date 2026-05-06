import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

export interface MiniListItem {
  id: string
  label: string
  sublabel?: string
  meta?: string
  icon?: ReactNode
  onClick?: () => void
}

interface MiniListProps {
  items: MiniListItem[]
  className?: string
  emptyText?: string
}

/**
 * Compact list used inside DeskSurface "Active tasks" section.
 */
export function MiniList({ items, className, emptyText = 'Nenhum item' }: MiniListProps) {
  if (items.length === 0) {
    return (
      <p className="text-caption text-gray-500 py-2 text-center">{emptyText}</p>
    )
  }

  return (
    <ul className={cn('space-y-1', className)}>
      {items.map((item) => (
        <li key={item.id}>
          <button
            onClick={item.onClick}
            disabled={!item.onClick}
            className={cn(
              'w-full flex items-center gap-3 px-3 py-2 rounded text-left',
              'transition-colors duration-normal',
              item.onClick
                ? 'hover:bg-elevated cursor-pointer focus-visible:ring-2 focus-visible:ring-blu-500 focus-visible:outline-none'
                : 'cursor-default'
            )}
          >
            {item.icon && (
              <span className="shrink-0 text-gray-400">{item.icon}</span>
            )}
            <span className="flex-1 min-w-0">
              <span className="block text-body-sm text-gray-200 truncate">{item.label}</span>
              {item.sublabel && (
                <span className="block text-caption text-gray-500 truncate">{item.sublabel}</span>
              )}
            </span>
            {item.meta && (
              <span className="text-caption-sm text-gray-500 shrink-0">{item.meta}</span>
            )}
          </button>
        </li>
      ))}
    </ul>
  )
}
