import type { ReactNode } from 'react'
import { Plus } from 'lucide-react'
import { cn } from '@/utils/cn'

interface EmptyDrawerProps {
  message?: string
  cta?: string
  onCta?: () => void
  icon?: ReactNode
  className?: string
}

export function EmptyDrawer({
  message = 'Nenhum item encontrado.',
  cta,
  onCta,
  icon,
  className,
}: EmptyDrawerProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-8 px-4 text-center', className)}>
      <div className="w-10 h-10 rounded-full bg-elevated flex items-center justify-center mb-3 text-gray-500">
        {icon ?? <Plus size={18} strokeWidth={1.5} />}
      </div>
      <p className="text-body-sm text-gray-400 mb-3">{message}</p>
      {cta && onCta && (
        <button
          onClick={onCta}
          className={cn(
            'inline-flex items-center gap-1.5 px-3 py-1.5 rounded',
            'text-body-sm text-blu-400 hover:text-blu-300 border border-blu-500/30',
            'hover:bg-blu-500/10 transition-colors cursor-pointer',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500'
          )}
        >
          <Plus size={14} />
          {cta}
        </button>
      )}
    </div>
  )
}
