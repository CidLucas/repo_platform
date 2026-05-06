import { cn } from '@/utils/cn'
import { AlertCircle, RefreshCw } from 'lucide-react'

interface ErrorHumanProps {
  /** Friendly error message to show. Defaults to generic. */
  message?: string
  /** If provided, shows a Retry button */
  onRetry?: () => void
  className?: string
}

/**
 * Friendly error state. Never shows stack traces.
 * Used by TanStack Query global error handler and inline states.
 */
export function ErrorHuman({
  message = 'Algo deu errado. Tente novamente.',
  onRetry,
  className,
}: ErrorHumanProps) {
  return (
    <div
      role="alert"
      className={cn(
        'flex flex-col items-center gap-3 py-10 px-6 text-center',
        className
      )}
    >
      <div className="w-10 h-10 rounded-full bg-urgent/10 flex items-center justify-center">
        <AlertCircle size={20} className="text-urgent" strokeWidth={1.5} />
      </div>
      <div>
        <p className="text-body-sm text-gray-200 font-medium">{message}</p>
        <p className="text-caption text-gray-500 mt-0.5">
          Se o problema persistir, recarregue a página.
        </p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className={cn(
            'flex items-center gap-1.5 px-4 py-2 rounded text-body-sm',
            'bg-elevated border border-border text-gray-300',
            'hover:text-white hover:border-blu-500/50 transition-colors duration-normal cursor-pointer',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500'
          )}
        >
          <RefreshCw size={13} strokeWidth={1.5} />
          Tentar novamente
        </button>
      )}
    </div>
  )
}
