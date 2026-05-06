import { useState } from 'react'
import { Lightbulb, X } from 'lucide-react'
import { cn } from '@/utils/cn'

interface InsightBannerProps {
  text: string
  cta?: string
  onCta?: () => void
  className?: string
}

/**
 * Highlighted analytics insight banner — dismissible.
 * Used inside AnalyticsCard to surface a key finding from the data.
 */
export function InsightBanner({ text, cta, onCta, className }: InsightBannerProps) {
  const [dismissed, setDismissed] = useState(false)

  if (dismissed) return null

  return (
    <div
      className={cn(
        'flex items-start gap-3 px-4 py-3 rounded-md',
        'bg-blu-900/50 border border-blu-800',
        className
      )}
      role="note"
    >
      <Lightbulb
        size={15}
        strokeWidth={1.5}
        className="text-blu-400 shrink-0 mt-0.5"
        aria-hidden
      />
      <p className="flex-1 text-body-sm text-blu-300 leading-snug">
        {text}
        {cta && onCta && (
          <button
            onClick={onCta}
            className="ml-2 text-blu-400 underline underline-offset-2 hover:text-blu-300 transition-colors duration-normal cursor-pointer focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-blu-500 rounded"
          >
            {cta}
          </button>
        )}
      </p>
      <button
        onClick={() => setDismissed(true)}
        aria-label="Fechar insight"
        className="shrink-0 text-gray-500 hover:text-gray-300 transition-colors duration-normal cursor-pointer focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-blu-500 rounded"
      >
        <X size={14} strokeWidth={1.5} />
      </button>
    </div>
  )
}
