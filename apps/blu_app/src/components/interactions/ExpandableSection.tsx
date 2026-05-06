import { useState, useId, type ReactNode } from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/utils/cn'

interface ExpandableSectionProps {
  title: ReactNode
  children: ReactNode
  defaultOpen?: boolean
  className?: string
  /** Optional right-side element in header (badge, count, etc.) */
  headerRight?: ReactNode
}

/**
 * CSS max-height accordion — no layout shift, no JS animation libraries.
 * Transition: 300ms ease-in-out (duration-slow in design tokens).
 */
export function ExpandableSection({
  title,
  children,
  defaultOpen = false,
  className,
  headerRight,
}: ExpandableSectionProps) {
  const [open, setOpen] = useState(defaultOpen)
  const contentId = useId()

  return (
    <div className={cn('border border-border rounded-md overflow-hidden', className)}>
      {/* Trigger */}
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={contentId}
        className={cn(
          'w-full flex items-center justify-between gap-3',
          'px-4 py-3 text-left cursor-pointer',
          'bg-surface hover:bg-elevated',
          'transition-colors duration-normal',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blu-500'
        )}
      >
        <span className="text-body-sm font-medium text-gray-200 flex-1 min-w-0">
          {title}
        </span>
        {headerRight && (
          <span className="shrink-0 text-caption text-gray-400">{headerRight}</span>
        )}
        <ChevronDown
          size={16}
          className={cn(
            'shrink-0 text-gray-400 transition-transform duration-slow',
            open && 'rotate-180'
          )}
        />
      </button>

      {/* Expandable content — CSS max-height accordion */}
      <div
        id={contentId}
        role="region"
        className={cn(
          'grid transition-[grid-template-rows] duration-slow ease-in-out',
          open ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'
        )}
      >
        <div className="overflow-hidden">
          <div className="px-4 py-3 bg-base border-t border-border">
            {children}
          </div>
        </div>
      </div>
    </div>
  )
}
