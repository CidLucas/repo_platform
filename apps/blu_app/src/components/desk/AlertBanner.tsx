import type { ReactNode } from 'react'
import { AlertTriangle, X } from 'lucide-react'
import { cn } from '@/utils/cn'

interface AlertBannerProps {
  title: string
  description?: string
  cta?: ReactNode
  onDismiss?: () => void
  className?: string
}

/**
 * Full-width critical alert bar. Red gradient background.
 * Sits above the DeskSurface when an urgent condition is detected.
 */
export function AlertBanner({ title, description, cta, onDismiss, className }: AlertBannerProps) {
  return (
    <div
      role="alert"
      className={cn(
        'flex items-start gap-3 p-4 rounded-md mb-4',
        'bg-gradient-to-r from-urgent/20 to-urgent/10 border border-urgent/40',
        className
      )}
    >
      <AlertTriangle
        size={18}
        className="text-urgent shrink-0 mt-0.5"
        strokeWidth={1.5}
      />
      <div className="flex-1 min-w-0">
        <p className="text-body-sm font-medium text-white">{title}</p>
        {description && (
          <p className="text-caption text-gray-300 mt-0.5">{description}</p>
        )}
        {cta && <div className="mt-2">{cta}</div>}
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          aria-label="Fechar alerta"
          className="p-1 text-gray-400 hover:text-white transition-colors cursor-pointer
            rounded focus-visible:ring-2 focus-visible:ring-urgent shrink-0"
        >
          <X size={14} />
        </button>
      )}
    </div>
  )
}
