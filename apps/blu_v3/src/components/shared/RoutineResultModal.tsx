import type { RoutineExecution } from '../../api/routines'
import Checkbox from './Checkbox'

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
  const lines = (execution.result_text ?? '').split('\n').filter(Boolean)
  const duration = formatDuration(execution.created_at, execution.completed_at)
  const failed = execution.status === 'failed'

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'rgba(0,0,0,.6)', backdropFilter: 'blur(4px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 16,
      }}
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        style={{
          background: 'var(--bg2, #1a1f2e)',
          border: '1px solid var(--gb)',
          borderRadius: 10,
          width: '100%', maxWidth: 520,
          display: 'flex', flexDirection: 'column',
          maxHeight: '80vh',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--gb)', display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 13, fontWeight: 700 }}>{routineName}</div>
            <div style={{ fontSize: 10.5, color: 'var(--mu)', marginTop: 2, display: 'flex', gap: 10 }}>
              <span>{execution.completed_at ? formatDateTime(execution.completed_at) : formatDateTime(execution.created_at)}</span>
              {duration && <span>⏱ {duration}</span>}
              <span style={{ color: failed ? 'var(--urg)' : 'var(--ok)' }}>
                {failed ? '✗ Falhou' : '✓ Concluída'}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: 'var(--mu)', cursor: 'pointer', fontSize: 18, lineHeight: 1, padding: '0 4px' }}
          >
            ✕
          </button>
        </div>

        {/* Result body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
          {lines.length === 0 ? (
            <div style={{ fontSize: 12, color: 'var(--mu)' }}>Sem resultado registrado.</div>
          ) : (
            lines.map((line, i) => {
              const colonIdx = line.indexOf(':')
              const hasLabel = colonIdx > 0 && colonIdx < 40
              const label = hasLabel ? line.slice(0, colonIdx).trim() : null
              const text = hasLabel ? line.slice(colonIdx + 1).trim() : line

              return (
                <div
                  key={i}
                  style={{
                    background: 'var(--glass)',
                    border: '1px solid var(--gb)',
                    borderRadius: 6,
                    padding: '8px 11px',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 8,
                  }}
                >
                  <div style={{ paddingTop: 1, flexShrink: 0 }}>
                    <Checkbox
                      checked={!failed}
                      disabled
                      onChange={() => {}}
                    />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    {label && (
                      <div style={{ fontSize: 10, color: 'var(--mu)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 4 }}>
                        {i + 1}. {label}
                      </div>
                    )}
                    <div style={{ fontSize: 12, lineHeight: 1.5, color: text ? 'inherit' : 'var(--mu)', fontStyle: text ? 'normal' : 'italic' }}>
                      {text || 'ok'}
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>

        {/* Footer */}
        <div style={{ padding: '10px 16px', borderTop: '1px solid var(--gb)' }}>
          <button className="btn bs" style={{ fontSize: 11, padding: '4px 12px' }} onClick={onClose}>Fechar</button>
        </div>
      </div>
    </div>
  )
}
