import { createPortal } from 'react-dom'

const CONN_OPTIONS = [
  { id: 'bling',    icon: '📦', name: 'Bling',        sub: 'ERP / NF-e' },
  { id: 'omie',     icon: '⚙️',  name: 'Omie',         sub: 'ERP' },
  { id: 'gdrive',   icon: '📁', name: 'Google Drive',  sub: 'Planilhas' },
  { id: 'csv',      icon: '📄', name: 'Planilha CSV',  sub: 'Excel / CSV' },
  { id: 'bigquery', icon: '📊', name: 'BigQuery',      sub: 'Data warehouse' },
]

interface ConnectionsModalProps {
  open: boolean
  onClose: () => void
}

export default function ConnectionsModal({ open, onClose }: ConnectionsModalProps) {
  if (!open) return null

  return createPortal(
    <>
      <div
        style={{
          position: 'fixed', inset: 0, zIndex: 200,
          background: 'rgba(3,8,24,0.70)',
          backdropFilter: 'blur(8px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: 20,
        }}
        onClick={onClose}
      >
        <div
          style={{
            width: '100%', maxWidth: 480,
            background: 'rgba(8,18,48,0.92)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 14,
            backdropFilter: 'blur(16px)',
            padding: '28px 28px 24px',
            boxShadow: '0 24px 80px rgba(0,0,0,.4)',
            animation: 'cmFadeIn .3s ease',
          }}
          onClick={e => e.stopPropagation()}
        >
          <div style={{ fontSize: 20, fontWeight: 800, marginBottom: 6, color: '#E8EDF8', letterSpacing: '-.03em' }}>
            Conectar seus dados
          </div>
          <div style={{ fontSize: 13, color: 'rgba(232,237,248,0.55)', marginBottom: 20, lineHeight: 1.5 }}>
            Seu agente aprende sobre seu negócio a partir dos seus dados. Escolha de onde vêm.
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            {CONN_OPTIONS.map(opt => (
              <div
                key={opt.id}
                onClick={onClose}
                className="conn-opt-item"
                style={{
                  background: 'rgba(255,255,255,0.045)',
                  border: '1.5px solid rgba(255,255,255,0.08)',
                  borderRadius: 8, padding: '14px 12px', textAlign: 'center',
                  cursor: 'pointer', transition: 'all .12s',
                  fontSize: 12.5, color: 'rgba(232,237,248,0.55)',
                }}
                onMouseEnter={e => {
                  const el = e.currentTarget as HTMLDivElement
                  el.style.borderColor = '#3B82F6'
                  el.style.background = 'rgba(59,130,246,0.07)'
                  el.style.color = '#E8EDF8'
                }}
                onMouseLeave={e => {
                  const el = e.currentTarget as HTMLDivElement
                  el.style.borderColor = 'rgba(255,255,255,0.08)'
                  el.style.background = 'rgba(255,255,255,0.045)'
                  el.style.color = 'rgba(232,237,248,0.55)'
                }}
              >
                <span style={{ fontSize: 22, display: 'block', marginBottom: 6 }}>{opt.icon}</span>
                <div style={{ fontWeight: 600, color: 'inherit' }}>{opt.name}</div>
                <div style={{ fontSize: 10.5, color: 'rgba(232,237,248,0.38)', marginTop: 2 }}>{opt.sub}</div>
              </div>
            ))}
          </div>

          <div style={{ marginTop: 16, textAlign: 'center' }}>
            <span
              style={{ fontSize: 12, color: 'rgba(232,237,248,0.45)', cursor: 'pointer' }}
              onClick={onClose}
            >
              Prefiro ver uma demonstração primeiro →
            </span>
          </div>

          <button
            onClick={onClose}
            style={{
              width: '100%', marginTop: 12, padding: '9px 16px',
              borderRadius: 8, border: '1px solid rgba(255,255,255,0.1)',
              background: 'rgba(255,255,255,0.05)', color: 'rgba(232,237,248,0.7)',
              fontSize: 13, cursor: 'pointer',
            }}
          >
            ← Voltar
          </button>
        </div>
      </div>

      <style>{`
        @keyframes cmFadeIn {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </>,
    document.body,
  )
}
