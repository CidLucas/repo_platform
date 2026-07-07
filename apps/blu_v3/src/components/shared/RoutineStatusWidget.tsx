import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../../hooks/useAuth'
import {
  fetchActiveRoutines,
  fetchLastExecution,
  toggleRoutine,
  type ClientRoutine,
  type RoutineExecution,
} from '../../api/routines'
import RoutineResultModal from './RoutineResultModal'
import Toggle from './Toggle'

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 60) return `há ${mins}min`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `há ${hrs}h`
  const days = Math.floor(hrs / 24)
  return `há ${days}d`
}

function RoutineRow({
  routine, clientId, onToggle,
}: {
  routine: ClientRoutine
  clientId: string
  onToggle: (id: string, enabled: boolean) => void
}) {
  const [modalExec, setModalExec] = useState<RoutineExecution | null>(null)

  const { data: lastExec } = useQuery({
    queryKey: ['last-execution', clientId, routine.routine_id],
    queryFn: () => fetchLastExecution(clientId, routine.routine_id),
    staleTime: 60_000,
  })

  const name = routine.cross_agent_routines?.name ?? routine.routine_id

  return (
    <>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '7px 0',
          borderBottom: '1px solid var(--gb)',
        }}
      >
        <div
          style={{
            width: 6, height: 6, borderRadius: 3, flexShrink: 0,
            background: 'var(--ok)',
          }}
        />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 11.5, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {name}
          </div>
          <div style={{ fontSize: 10, color: 'var(--mu)', marginTop: 1 }}>
            {routine.last_run_at
              ? `última: ${timeAgo(routine.last_run_at)}`
              : lastExec?.completed_at
              ? `última: ${timeAgo(lastExec.completed_at)}`
              : 'nunca executada'}
          </div>
        </div>
        {(lastExec?.result_text) && (
          <button
            className="btn bs"
            style={{ fontSize: 10, padding: '3px 8px', flexShrink: 0 }}
            onClick={() => setModalExec(lastExec)}
          >
            Ver →
          </button>
        )}
        <Toggle
          checked={routine.active}
          onChange={v => onToggle(routine.id, v)}
        />
      </div>

      {modalExec && (
        <RoutineResultModal
          execution={modalExec}
          routineName={name}
          onClose={() => setModalExec(null)}
        />
      )}
    </>
  )
}

export default function RoutineStatusWidget({ domain }: { domain: string }) {
  const { clientId } = useAuth()
  const qc = useQueryClient()

  const { data: routines = [], isLoading } = useQuery({
    queryKey: ['active-routines', clientId ?? '', domain],
    queryFn: () => fetchActiveRoutines(clientId!, domain),
    enabled: !!clientId,
    staleTime: 60_000,
  })

  const toggleMut = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      toggleRoutine(id, clientId!, enabled),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['active-routines', clientId ?? '', domain] }),
  })

  if (isLoading) {
    return <div style={{ fontSize: 11, color: 'var(--mu)', padding: '6px 0' }}>Carregando…</div>
  }

  if (routines.length === 0) {
    return (
      <div style={{ fontSize: 11, color: 'var(--mu)', padding: '6px 0', fontStyle: 'italic' }}>
        Nenhuma rotina ativa. Configure em Configurar.
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      {routines.map(r => (
        <RoutineRow
          key={r.id}
          routine={r}
          clientId={clientId!}
          onToggle={(id, enabled) => toggleMut.mutate({ id, enabled })}
        />
      ))}
    </div>
  )
}
