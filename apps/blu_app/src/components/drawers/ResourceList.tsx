import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

export interface ResourceItem {
  id: string
  title: string
  subtitle?: string
  meta?: string
  badge?: ReactNode
  /** Left slot — icon, orb, or thumbnail */
  icon?: ReactNode
  onClick?: () => void
}

interface ResourceListProps {
  items: ResourceItem[]
  className?: string
}

/**
 * Generic resource list used in drawers (suppliers, accounts, documents…).
 * Each row: [icon] [title + subtitle] [meta/badge]
 */
export function ResourceList({ items, className }: ResourceListProps) {
  return (
    <ul className={cn('divide-y divide-border', className)}>
      {items.map((item) => (
        <li key={item.id}>
          <button
            onClick={item.onClick}
            disabled={!item.onClick}
            className={cn(
              'w-full flex items-center gap-3 px-4 py-3 text-left',
              'transition-colors duration-normal',
              item.onClick
                ? 'hover:bg-elevated cursor-pointer focus-visible:outline-none focus-visible:ring-inset focus-visible:ring-2 focus-visible:ring-blu-500'
                : 'cursor-default'
            )}
          >
            {item.icon && (
              <span className="shrink-0 w-8 h-8 flex items-center justify-center text-gray-400">
                {item.icon}
              </span>
            )}
            <span className="flex-1 min-w-0">
              <span className="block text-body-sm text-white truncate font-medium">
                {item.title}
              </span>
              {item.subtitle && (
                <span className="block text-caption text-gray-400 truncate">
                  {item.subtitle}
                </span>
              )}
            </span>
            <span className="shrink-0 flex flex-col items-end gap-1">
              {item.meta && (
                <span className="text-caption-sm text-gray-500">{item.meta}</span>
              )}
              {item.badge}
            </span>
          </button>
        </li>
      ))}
    </ul>
  )
}
