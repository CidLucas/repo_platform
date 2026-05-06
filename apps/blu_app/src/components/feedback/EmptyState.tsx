import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

interface EmptyStateProps {
  icon?: ReactNode
  title: string
  body?: string
  action?: ReactNode
  className?: string
}

/**
 * Generic empty state. Warm sand background, icon + title + body + CTA.
 * Used in drawers, lists, and rooms when there's no data.
 */
export function EmptyState({
  icon,
  title,
  body,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center gap-3 text-center px-6 py-10 rounded-md',
        'bg-[rgba(232,220,196,0.06)] border border-[rgba(232,220,196,0.10)]',
        className
      )}
    >
      {icon && (
        <div className="w-10 h-10 rounded-full bg-elevated flex items-center justify-center text-gray-400">
          {icon}
        </div>
      )}
      <div>
        <p className="text-body-sm font-medium text-gray-200">{title}</p>
        {body && (
          <p className="text-caption text-gray-500 mt-0.5 max-w-[260px] mx-auto">{body}</p>
        )}
      </div>
      {action && <div className="mt-1">{action}</div>}
    </div>
  )
}
