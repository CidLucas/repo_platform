import type { RoutineExecution } from '../../api/routines'
import SmartRenderer from '../chat/SmartRenderer'
import Modal from './Modal'

interface Props {
  execution: RoutineExecution
  routineName: string
  onClose: () => void
}

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

export default function RoutineResultModal({ execution, routineName, onClose }: Props) {
  const duration = formatDuration(execution.created_at, execution.completed_at)
  const failed = execution.status === 'failed'
  const partial = execution.status === 'partial'

  return (
    <Modal open onClose={onClose} title={routineName} width="520px">
      {/* Metadata row */}
      <div style={{ fontSize: 10.5, color: 'var(--mu)', marginTop: -8, marginBottom: 12, display: 'flex', gap: 10 }}>
        <span>{execution.completed_at ? formatDateTime(execution.completed_at) : formatDateTime(execution.created_at)}</span>
        {duration && <span>⏱ {duration}</span>}
        <span style={{ color: failed ? 'var(--urg)' : partial ? 'var(--att)' : 'var(--ok)' }}>
          {failed ? '✗ Falhou' : partial ? '◐ Parcial' : '✓ Concluída'}
        </span>
      </div>

      {/* Result body */}
      <div style={{ maxHeight: '60vh', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
        {execution.result_text ? (
          <SmartRenderer content={execution.result_text} />
        ) : (
          <div style={{ fontSize: 12, color: 'var(--mu)' }}>Sem resultado registrado.</div>
        )}
      </div>

      {/* Footer */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 16 }}>
        <button className="btn bs" style={{ fontSize: 11, padding: '4px 12px' }} onClick={onClose}>Fechar</button>
      </div>
    </Modal>
  )
}
