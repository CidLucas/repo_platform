import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { cn } from '@/utils/cn'
import type { ReactNode } from 'react'

interface RightPanelCardProps {
  title: string
  children: ReactNode
  headerActions?: ReactNode
  /** Agent accent color — drives the top strip and title tint */
  accentColor?: string
  /** Show content expanded by default */
  defaultExpanded?: boolean
}

/**
 * Stacked expandable card used in the desktop right sidebar of DeskLayout.
 * Shows a preview of the content (clipped) and expands on toggle.
 */
export function RightPanelCard({
  title,
  children,
  headerActions,
  accentColor,
  defaultExpanded = true,
}: RightPanelCardProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)

  return (
    <div className="bg-gray-900 border border-border rounded-lg overflow-hidden flex flex-col shrink-0">
      {/* Colored top accent strip */}
      {accentColor && (
        <div className="h-[3px] w-full shrink-0" style={{ background: `linear-gradient(90deg, ${accentColor}, ${accentColor}55)` }} />
      )}

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
        <h3
          className="text-heading-sm font-medium"
          style={accentColor ? { color: accentColor } : { color: 'white' }}
        >
          {title}
        </h3>
        {headerActions && (
          <div className="flex items-center gap-2">{headerActions}</div>
        )}
      </div>

      {/* Content — clipped when collapsed, scrollable when expanded */}
      <div
        className={cn(
          'relative transition-[max-height] duration-300 ease-in-out',
          isExpanded
            ? 'max-h-[50vh] overflow-y-auto scroll-container'
            : 'max-h-52 overflow-hidden'
        )}
      >
        {children}

        {/* Gradient fade hint when collapsed */}
        {!isExpanded && (
          <div className="absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-gray-900 to-transparent pointer-events-none" />
        )}
      </div>

      {/* Expand / collapse toggle */}
      <button
        onClick={() => setIsExpanded((v) => !v)}
        className={cn(
          'flex items-center justify-center gap-1.5 py-2.5 shrink-0',
          'border-t border-border text-caption text-gray-400',
          'hover:bg-elevated hover:text-white transition-colors cursor-pointer'
        )}
      >
        <span>{isExpanded ? 'Ver menos' : 'Ver mais'}</span>
        {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>
    </div>
  )
}
