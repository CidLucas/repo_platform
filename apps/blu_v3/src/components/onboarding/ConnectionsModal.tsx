import Modal from '../shared/Modal'

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
  return (
    <Modal open={open} onClose={onClose} width="460px">
      <div style={{ fontSize: 20, fontWeight: 800, marginBottom: 6, color: 'var(--fg)', letterSpacing: '-.03em' }}>
        Conectar seus dados
      </div>
      <div style={{ fontSize: 13, color: 'var(--mu2)', marginBottom: 20, lineHeight: 1.5 }}>
        Seu agente aprende sobre seu negócio a partir dos seus dados. Escolha de onde vêm.
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        {CONN_OPTIONS.map(opt => (
          <button
            key={opt.id}
            onClick={onClose}
            className="btn btn-ghost"
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              padding: '14px 12px',
              fontSize: 12.5,
            }}
          >
            <span style={{ fontSize: 22, display: 'block', marginBottom: 6 }}>{opt.icon}</span>
            <span style={{ fontWeight: 600, color: 'inherit' }}>{opt.name}</span>
            <span style={{ fontSize: 10.5, color: 'var(--mu)', marginTop: 2 }}>{opt.sub}</span>
          </button>
        ))}
      </div>

      <div style={{ marginTop: 16, textAlign: 'center' }}>
        <span
          style={{ fontSize: 12, color: 'var(--mu)', cursor: 'pointer' }}
          onClick={onClose}
        >
          Prefiro ver uma demonstração primeiro →
        </span>
      </div>

      <button
        onClick={onClose}
        className="btn bg"
        style={{ width: '100%', marginTop: 12, fontSize: 13 }}
      >
        ← Voltar
      </button>
    </Modal>
  )
}
