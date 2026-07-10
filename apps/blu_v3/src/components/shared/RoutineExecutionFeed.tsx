import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../../hooks/useAuth'
import { fetchExecutionHistory, type RoutineExecution } from '../../api/routines'
import RoutineResultModal from './RoutineResultModal'
import Checkbox from './Checkbox'

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  })
}

function formatDuration(start: string, end: string | null) {
  if (!end) return null
  const ms = new Date(end).getTime() - new Date(start).getTime()
  if (ms < 60_000) return `${Math.round(ms / 1000)}s`
  return `${Math.round(ms / 60_000)}min`
}

function ExecutionRow({
  exec, routineName,
}: {
  exec: RoutineExecution
  routineName: string
}) {
  const [showModal, setShowModal] = useState(false)
  const duration = formatDuration(exec.created_at, exec.completed_at)
  const firstLine = exec.result_text?.split('\n').find(l => l.trim()) ?? null

  return (
    <>
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: 10,
          padding: '10px 0',
          borderBottom: '1px solid var(--gb)',
        }}
      >
        <span style={{ fontSize: 14, lineHeight: 1.2, flexShrink: 0, marginTop: 1 }}>
          <Checkbox
            checked={exec.status === 'completed'}
            disabled
            onChange={() => {}}
          />
        </span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 12.5, fontWeight: 500 }}>
            {routineName}
            {exec.status === 'partial' && (
              <span style={{ marginLeft: 6, fontSize: 10, color: 'var(--att)' }}>◐ parcial</span>
            )}
            {exec.status === 'failed' && (
              <span style={{ marginLeft: 6, fontSize: 10, color: 'var(--urg)' }}>✗ falhou</span>
            )}
          </div>
          {firstLine && (
            <div style={{ fontSize: 11, color: 'var(--mu)', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {firstLine}
            </div>
          )}
          <div style={{ fontSize: 10, color: 'var(--mu)', marginTop: 3, display: 'flex', gap: 8 }}>
            <span>{formatDateTime(exec.created_at)}</span>
            {duration && <span>⏱ {duration}</span>}
          </div>
        </div>
        {exec.result_text && (
          <button
            className="btn bs"
            style={{ fontSize: 10, padding: '3px 8px', flexShrink: 0 }}
            onClick={() => setShowModal(true)}
          >
            Ver →
          </button>
        )}
      </div>

      {showModal && (
        <RoutineResultModal
          execution={exec}
          routineName={routineName}
          onClose={() => setShowModal(false)}
        />
      )}
    </>
  )
}

export default function RoutineExecutionFeed({ domain }: { domain: string }) {
  const { clientId } = useAuth()

  const { data: executions = [], isLoading } = useQuery({
    queryKey: ['execution-history', clientId ?? '', domain],
    queryFn: () => fetchExecutionHistory(clientId!, domain),
    enabled: !!clientId,
    staleTime: 60_000,
  })

  if (isLoading) {
    return <div style={{ fontSize: 12, color: 'var(--mu)', padding: '12px 0' }}>Carregando…</div>
  }

  if (executions.length === 0) {
    return (
      <div className="empty" style={{ padding: '24px 0' }}>
        <div className="ei">⚙️</div>
        <div className="et">Nenhuma execução ainda</div>
        <div className="eb">Quando uma rotina for executada, o resultado aparece aqui.</div>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      {executions.map(exec => (
        <ExecutionRow
          key={exec.id}
          exec={exec}
          routineName={exec.routine_name ?? exec.routine_id}
        />
      ))}
    </div>
  )
}
