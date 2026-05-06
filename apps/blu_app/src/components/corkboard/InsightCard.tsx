import { useState } from 'react'
import { X, ChevronDown, ChevronUp } from 'lucide-react'
import { cn } from '@/utils/cn'
import { InsightSeverity } from './InsightSeverity'
import { InsightAction } from './InsightAction'

type SeverityLevel = 'critical' | 'warning' | 'info' | 'positive'

interface InsightCardProps {
  id: string
  title: string
  body: string
  severity?: SeverityLevel
  ctaLabel?: string
  onCta?: () => void
  onDismiss?: (id: string) => void
  className?: string
}

export function InsightCard({
  id,
  title,
  body,
  severity = 'info',
  ctaLabel,
  onCta,
  onDismiss,
  className,
}: InsightCardProps) {
  const [expanded, setExpanded] = useState(false)
  const isLong = body.length > 120
  const displayBody = !isLong || expanded ? body : body.slice(0, 120) + '…'

  return (
    <div
      className={cn(
        'bg-surface border border-border rounded-md p-4',
        'hover:border-blu-500/30 transition-colors duration-normal',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-start gap-2 mb-2">
        <div className="flex-1 min-w-0">
          <p className="text-body-sm font-medium text-white leading-snug">{title}</p>
          <InsightSeverity level={severity} className="mt-1" />
        </div>
        {onDismiss && (
          <button
            onClick={() => onDismiss(id)}
            aria-label="Dispensar insight"
            className="shrink-0 w-6 h-6 flex items-center justify-center rounded
              text-gray-500 hover:text-white hover:bg-elevated
              transition-colors cursor-pointer
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500"
          >
            <X size={13} />
          </button>
        )}
      </div>

      {/* Body */}
      <p className="text-caption text-gray-300 leading-relaxed mb-3">{displayBody}</p>

      {/* Expand/collapse long body */}
      {isLong && (
        <button
          onClick={() => setExpanded((v) => !v)}
          className="flex items-center gap-1 text-caption text-blu-400
            hover:text-blu-300 transition-colors cursor-pointer mb-2"
        >
          {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          {expanded ? 'Ver menos' : 'Ver mais'}
        </button>
      )}

      {/* CTA */}
      {ctaLabel && onCta && (
        <InsightAction variant="primary" onClick={onCta}>
          {ctaLabel}
        </InsightAction>
      )}
    </div>
  )
}
