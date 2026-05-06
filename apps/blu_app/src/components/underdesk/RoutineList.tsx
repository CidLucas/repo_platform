import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/hooks/useAuth'
import { fetchRoutines, toggleRoutine } from '@/api/routines'
import { RoutineItem } from './RoutineItem'
import { SkeletonCard } from '@/components/primitives/SkeletonCard'

interface RoutineListProps {
  /** Filter to routines whose routine_id starts with this prefix, e.g. "compras" */
  prefix?: string
  accentColor?: string
}

export function RoutineList({ prefix, accentColor }: RoutineListProps) {
  const { clientId } = useAuth()
  const qc = useQueryClient()

  const { data: routines = [], isLoading } = useQuery({
    queryKey: ['routines', prefix, clientId],
    queryFn: () => fetchRoutines(clientId!, prefix),
    enabled: !!clientId,
  })

  const toggle = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      toggleRoutine(id, clientId!, enabled),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['routines', prefix, clientId] })
    },
  })

  if (isLoading) {
    return (
      <div className="px-4 py-3">
        <SkeletonCard lines={1} />
      </div>
    )
  }

  if (routines.length === 0) {
    return (
      <p className="text-caption text-gray-500 text-center py-4">
        Nenhuma rotina configurada.
      </p>
    )
  }

  return (
    <div>
      {routines.map((routine) => (
        <RoutineItem
          key={routine.id}
          routine={routine}
          onToggle={(id, enabled) => toggle.mutate({ id, enabled })}
          loading={toggle.isPending}
          accentColor={accentColor}
        />
      ))}
    </div>
  )
}
