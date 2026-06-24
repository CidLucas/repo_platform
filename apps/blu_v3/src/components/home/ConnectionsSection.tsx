import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getUploadedFiles } from '../../api/connectors'
import ConnectionsModal from '../onboarding/ConnectionsModal'

interface ConnectionsSectionProps {
  clientId: string
}

export default function ConnectionsSection({ clientId }: ConnectionsSectionProps) {
  const [modalOpen, setModalOpen] = useState(false)

  const connectionsQ = useQuery({
    queryKey: ['connections-section', 'uploaded-files', clientId],
    queryFn: () => getUploadedFiles(clientId),
    enabled: !!clientId,
    staleTime: 60_000,
  })

  const connections = connectionsQ.data ?? []

  return (
    <div className="connections-section">
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 8,
        }}
      >
        <div
          style={{
            fontSize: 11,
            fontWeight: 700,
            color: 'var(--mu, rgba(223,227,238,0.6))',
            letterSpacing: '.06em',
            textTransform: 'uppercase',
          }}
        >
          Conexões
        </div>
        <button
          type="button"
          onClick={() => setModalOpen(true)}
          style={{
            fontSize: 11.5,
            padding: '4px 10px',
            borderRadius: 6,
            border: '1px solid rgba(255,255,255,0.10)',
            background: 'rgba(140,95,219,0.12)',
            color: 'var(--fg, #E8EDF8)',
            cursor: 'pointer',
          }}
        >
          + Adicionar conexão
        </button>
      </div>

      {connectionsQ.isLoading && (
        <div style={{ fontSize: 11.5, color: 'var(--mu, rgba(223,227,238,0.5))' }}>
          Carregando conexões…
        </div>
      )}

      {!connectionsQ.isLoading && connections.length === 0 && (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 6,
            padding: '8px 0',
          }}
        >
          <div style={{ fontSize: 12, color: 'var(--fg, #DFE3EE)' }}>
            Nenhuma conexão
          </div>
          <div style={{ fontSize: 11, color: 'var(--mu, rgba(223,227,238,0.5))' }}>
            Conectar dados
          </div>
        </div>
      )}

      {!connectionsQ.isLoading && connections.length > 0 && (
        <div className="connections-list">
          {connections.map((c) => (
            <div
              key={c.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '6px 8px',
                borderRadius: 6,
                background: 'rgba(255,255,255,0.04)',
                fontSize: 11.5,
                color: 'var(--fg, #DFE3EE)',
                marginBottom: 4,
              }}
            >
              <span style={{ fontSize: 13 }}>🔗</span>
              <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {c.file_name}
              </span>
            </div>
          ))}
        </div>
      )}

      <ConnectionsModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </div>
  )
}
