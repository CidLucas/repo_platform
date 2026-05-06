import { Play, Clock } from 'lucide-react'
import { SkeletonCard } from '@/components/primitives/SkeletonCard'
import type { ClientRoutine } from '@/api/routines'

function formatRoutineId(id: string): string {
  const slug = id.split('/').pop() ?? id
  return slug
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

interface ActiveRoutinesSlotProps {
  routines: ClientRoutine[]
  loading: boolean
  accentColor?: string
}

/**
 * "Tarefas" tab slot — shows active (enabled) routines for an agent.
 * Drop-in replacement for the hardcoded *ActiveTasks stubs.
 */
export function ActiveRoutinesSlot({ routines, loading, accentColor }: ActiveRoutinesSlotProps) {
  if (loading) return <SkeletonCard lines={3} />

  const active = routines.filter((r) => r.active)

  if (active.length === 0) {
    return (
      <p className="text-caption text-gray-500 text-center py-4">
        Nenhuma rotina ativa configurada.
      </p>
    )
  }

  return (
    <div className="space-y-1">
      <p className="text-caption-sm text-gray-500 uppercase tracking-wider mb-2">
        Rotinas Ativas
      </p>
      {active.map((r) => (
        <div
          key={r.id}
          className="flex items-center gap-3 px-1 py-2 rounded hover:bg-elevated transition-colors duration-normal"
        >
          <span
            className="shrink-0 w-6 h-6 flex items-center justify-center"
            style={accentColor ? { color: accentColor } : undefined}
          >
            <Play size={13} strokeWidth={1.5} className={accentColor ? undefined : 'text-blu-400'} />
          </span>
          <span className="flex-1 text-body-sm text-gray-200 truncate">
            {formatRoutineId(r.routine_id)}
          </span>
          {r.last_run_at && (
            <span className="text-caption-sm text-gray-500 shrink-0 flex items-center gap-1">
              <Clock size={10} />
              {new Date(r.last_run_at).toLocaleDateString('pt-BR')}
            </span>
          )}
        </div>
      ))}
    </div>
  )
}
