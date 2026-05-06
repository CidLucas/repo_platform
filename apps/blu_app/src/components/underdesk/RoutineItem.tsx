import { Clock, Play } from 'lucide-react'
import { cn } from '@/utils/cn'
import type { ClientRoutine } from '@/api/routines'

interface RoutineItemProps {
  routine: ClientRoutine
  onToggle: (id: string, enabled: boolean) => void
  loading?: boolean
  accentColor?: string
}

/** Formats routine_id "compras/check_stock" → "Check Stock" */
function formatRoutineId(id: string): string {
  const slug = id.split('/').pop() ?? id
  return slug
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

export function RoutineItem({ routine, onToggle, loading = false, accentColor }: RoutineItemProps) {
  const label = formatRoutineId(routine.routine_id)

  return (
    <div
      className={cn(
        'flex items-center gap-3 px-4 py-3',
        'border-b border-border last:border-0',
        !routine.active && 'opacity-50'
      )}
    >
      <div
        className="w-7 h-7 rounded flex items-center justify-center shrink-0"
        style={accentColor ? {
          background: `${accentColor}18`,
          border: `1px solid ${accentColor}35`,
          color: accentColor,
        } : { background: 'var(--color-elevated)', color: 'rgb(156,163,175)' }}
      >
        <Play size={13} strokeWidth={1.5} />
      </div>

      <div className="flex-1 min-w-0">
        <p className="text-body-sm text-white truncate">{label}</p>
        {routine.last_run_at && (
          <p className="text-caption-sm text-gray-500 flex items-center gap-1 mt-0.5">
            <Clock size={10} />
            Última execução: {new Date(routine.last_run_at).toLocaleDateString('pt-BR')}
          </p>
        )}
      </div>

      {/* Toggle */}
      <button
        role="switch"
        aria-checked={routine.active}
        aria-label={routine.active ? 'Desativar rotina' : 'Ativar rotina'}
        disabled={loading}
        onClick={() => onToggle(routine.id, !routine.active)}
        className={cn(
          'relative w-9 h-5 rounded-full transition-colors duration-normal cursor-pointer',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          !accentColor && (routine.active ? 'bg-blu-500' : 'bg-gray-600'),
          accentColor && !routine.active && 'bg-gray-600'
        )}
        style={accentColor && routine.active ? { background: accentColor } : undefined}
      >
        <span
          className={cn(
            'absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white',
            'transition-transform duration-normal',
            routine.active ? 'translate-x-4' : 'translate-x-0'
          )}
        />
      </button>
    </div>
  )
}
