import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, ClipboardList } from 'lucide-react'
import { cn } from '@/utils/cn'
import { Button } from '@/components/primitives/Button'
import { AgentBadge } from '@/components/navigation/AgentBadge'
import { relativeTime } from '@/utils/format'
import { fetchAuditLog } from '@/api/admin'
import type { AuditEntry } from '@/api/admin'

// ── Agent orb config per slug ──────────────────────────────────────────────

const AGENT_ORB: Record<string, { shape: 'hexagon' | 'circle' | 'diamond'; color: string }> = {
  compras: { shape: 'hexagon', color: '#D4A843' },
  financeiro: { shape: 'circle', color: '#5FB8A3' },
  agenda: { shape: 'diamond', color: '#9FC8EA' },
  documentos: { shape: 'circle', color: '#B8C4D4' },
  estrategia: { shape: 'hexagon', color: '#E07A5F' },
  clientes: { shape: 'circle', color: '#4A90D9' },
}

// ── AuditEntryRow ──────────────────────────────────────────────────────────

function AuditEntryRow({ entry }: { entry: AuditEntry }) {
  const orbConfig = entry.agent_slug ? AGENT_ORB[entry.agent_slug] : null

  return (
    <div className="flex items-start gap-3 py-3 border-b border-border/40 last:border-0">
      {/* Agent orb or generic icon */}
      <div className="shrink-0 mt-0.5">
        {orbConfig ? (
          <AgentBadge
            shape={orbConfig.shape}
            color={orbConfig.color}
            glowColor={`${orbConfig.color}33`}
            size={24}
            status="idle"
          />
        ) : (
          <div className="w-6 h-6 rounded-full bg-elevated border border-border flex items-center justify-center">
            <ClipboardList size={12} strokeWidth={1.5} className="text-gray-400" />
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-body-sm text-gray-200 leading-snug">{entry.action}</p>
        <div className="flex items-center gap-2 mt-0.5 flex-wrap">
          {entry.entity_type && (
            <span className="text-caption-sm text-gray-500">{entry.entity_type}</span>
          )}
          {entry.actor && (
            <span className="text-caption-sm text-gray-500">· {entry.actor}</span>
          )}
          {entry.agent_slug && (
            <span className="text-caption-sm text-gray-500">
              · Agente: {entry.agent_slug}
            </span>
          )}
        </div>
      </div>

      {/* Timestamp */}
      <span className="text-caption-sm text-gray-500 shrink-0 mt-0.5">
        {relativeTime(entry.created_at)}
      </span>
    </div>
  )
}

// ── AuditLog ───────────────────────────────────────────────────────────────

const PAGE_SIZE = 50

interface AuditLogProps {
  clientId: string
}

export function AuditLog({ clientId }: AuditLogProps) {
  const [page, setPage] = useState(1)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['audit-log', clientId, page],
    queryFn: () => fetchAuditLog(clientId, page, PAGE_SIZE),
    staleTime: 30_000,
  })

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 1

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 8 }).map((_, i) => (
          <div
            key={i}
            className={cn(
              'h-12 bg-surface border border-border rounded',
              'animate-shimmer'
            )}
            style={{
              backgroundImage:
                'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.03) 50%, transparent 100%)',
              backgroundSize: '200% 100%',
              animation: 'shimmer 2s linear infinite',
            }}
          />
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <div className="text-center py-10 text-gray-400">
        <p className="text-body-sm">Erro ao carregar auditoria.</p>
      </div>
    )
  }

  const entries = data?.entries ?? []

  if (entries.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        <ClipboardList size={32} strokeWidth={1} className="mx-auto mb-3 opacity-40" />
        <p className="text-body-sm">Nenhuma entrada de auditoria encontrada.</p>
      </div>
    )
  }

  return (
    <div>
      {/* Count */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-caption text-gray-400">
          {data?.total ?? 0} entradas no total
        </p>
        <p className="text-caption text-gray-500">
          Página {page} de {totalPages}
        </p>
      </div>

      {/* Entries */}
      <div className="bg-surface border border-border rounded-md px-4">
        {entries.map((entry) => (
          <AuditEntryRow key={entry.id} entry={entry} />
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3 mt-4">
          <Button
            variant="ghost"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            leftIcon={<ChevronLeft size={14} strokeWidth={1.5} />}
          >
            Anterior
          </Button>
          <span className="text-caption text-gray-400 min-w-[60px] text-center">
            {page} / {totalPages}
          </span>
          <Button
            variant="ghost"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            rightIcon={<ChevronRight size={14} strokeWidth={1.5} />}
          >
            Próxima
          </Button>
        </div>
      )}
    </div>
  )
}
