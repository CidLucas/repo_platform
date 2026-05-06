/**
 * IntegrationCard / ConnectorsPanel
 *
 * Full connector management panel for the Admin > Integrações tab.
 * Mirrors the connector setup flow from blu_dashboard:
 *   – Catalog of all available connector types
 *   – Configured connectors with status, sync, and disconnect actions
 *   – ConnectorModal for entering credentials
 */

import { useState } from 'react'
import {
  CheckCircle,
  AlertCircle,
  Circle,
  RefreshCw,
  Unlink,
  Plus,
  PlugZap,
} from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { cn } from '@/utils/cn'
import { Button } from '@/components/primitives/Button'
import { relativeTime } from '@/utils/format'
import { fetchIntegrations, syncIntegration, disconnectIntegration } from '@/api/admin'
import { deleteConnection } from '@/api/connectors'
import { ConnectorModal } from './ConnectorModal'
import { useAuth } from '@/hooks/useAuth'
import type { Integration, IntegrationStatus } from '@/api/admin'

// ── Connector catalog ──────────────────────────────────────────────────────
// Same connectors available in blu_dashboard.

export interface ConnectorDef {
  id: string
  label: string
  description: string
  color: string
  category: 'ecommerce' | 'database' | 'messaging' | 'payment' | 'erp'
}

export const CONNECTOR_CATALOG: ConnectorDef[] = [
  {
    id: 'shopify',
    label: 'Shopify',
    description: 'Pedidos e dados de vendas da sua loja',
    color: '#96BF48',
    category: 'ecommerce',
  },
  {
    id: 'vtex',
    label: 'VTEX',
    description: 'Plataforma de e-commerce VTEX',
    color: '#F71963',
    category: 'ecommerce',
  },
  {
    id: 'loja_integrada',
    label: 'Loja Integrada',
    description: 'Dados de vendas da Loja Integrada',
    color: '#FF6B35',
    category: 'ecommerce',
  },
  {
    id: 'bigquery',
    label: 'BigQuery',
    description: 'Data warehouse do Google Cloud',
    color: '#4285F4',
    category: 'database',
  },
  {
    id: 'postgresql',
    label: 'PostgreSQL',
    description: 'Banco de dados relacional PostgreSQL',
    color: '#336791',
    category: 'database',
  },
  {
    id: 'mysql',
    label: 'MySQL',
    description: 'Banco de dados relacional MySQL',
    color: '#00618A',
    category: 'database',
  },
  {
    id: 'whatsapp',
    label: 'WhatsApp Business',
    description: 'Envio de aprovações e alertas via WhatsApp',
    color: '#25D366',
    category: 'messaging',
  },
  {
    id: 'google_calendar',
    label: 'Google Calendar',
    description: 'Sincroniza eventos e agenda do negócio',
    color: '#4285F4',
    category: 'erp',
  },
  {
    id: 'google_sheets',
    label: 'Google Sheets',
    description: 'Importa dados de planilhas automaticamente',
    color: '#34A853',
    category: 'erp',
  },
  {
    id: 'stripe',
    label: 'Stripe',
    description: 'Dados de pagamento e transações',
    color: '#635BFF',
    category: 'payment',
  },
  {
    id: 'mercado_pago',
    label: 'Mercado Pago',
    description: 'Integração com pagamentos e carteiras',
    color: '#009EE3',
    category: 'payment',
  },
  {
    id: 'totvs',
    label: 'TOTVS',
    description: 'ERP e dados operacionais',
    color: '#E31F26',
    category: 'erp',
  },
  {
    id: 'conta_azul',
    label: 'Conta Azul',
    description: 'NFs, contas a pagar e financeiro',
    color: '#0066FF',
    category: 'erp',
  },
]

function getConnectorDef(provider: string): ConnectorDef {
  return (
    CONNECTOR_CATALOG.find((c) => c.id === provider.toLowerCase()) ?? {
      id: provider,
      label: provider.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
      description: 'Integração externa',
      color: '#4A90D9',
      category: 'erp',
    }
  )
}

// ── Provider badge ─────────────────────────────────────────────────────────

function ProviderBadge({ color, label }: { color: string; label: string }) {
  const initials = label
    .split(' ')
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
  return (
    <div
      className="w-10 h-10 rounded-md flex items-center justify-center shrink-0 text-caption font-medium"
      style={{ backgroundColor: `${color}22`, border: `1px solid ${color}33` }}
    >
      <span style={{ color }}>{initials}</span>
    </div>
  )
}

// ── Status indicator ───────────────────────────────────────────────────────

function StatusIndicator({ status }: { status: IntegrationStatus }) {
  if (status === 'connected')
    return (
      <span className="inline-flex items-center gap-1.5 text-caption text-ok font-medium">
        <CheckCircle size={13} strokeWidth={2} />
        Conectado
      </span>
    )
  if (status === 'error')
    return (
      <span className="inline-flex items-center gap-1.5 text-caption text-urgent font-medium">
        <AlertCircle size={13} strokeWidth={2} />
        Erro
      </span>
    )
  return (
    <span className="inline-flex items-center gap-1.5 text-caption text-gray-400">
      <Circle size={13} strokeWidth={2} />
      Não conectado
    </span>
  )
}

// ── Configured integration card ────────────────────────────────────────────

interface IntegrationCardProps {
  integration: Integration
  onRemove: (id: string) => void
  removeLoading: boolean
}

function IntegrationCard({ integration, onRemove, removeLoading }: IntegrationCardProps) {
  const qc = useQueryClient()
  const def = getConnectorDef(integration.provider)

  const syncMutation = useMutation({
    mutationFn: () => syncIntegration(integration.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['integrations'] }),
  })

  return (
    <div
      className={cn(
        'bg-surface border rounded-md p-4 transition-colors duration-normal',
        integration.status === 'error'
          ? 'border-urgent/40 shadow-glow-urgent'
          : integration.status === 'connected'
          ? 'border-border hover:border-gray-500'
          : 'border-border opacity-60',
      )}
    >
      {/* Header */}
      <div className="flex items-start gap-3">
        <ProviderBadge color={def.color} label={def.label} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-body-sm font-medium text-white truncate">{def.label}</h3>
            <StatusIndicator status={integration.status} />
          </div>
          <p className="text-caption text-gray-400 mt-0.5">{def.description}</p>
          {integration.connection_detail && (
            <p className="text-caption-sm text-gray-500 mt-0.5 font-mono truncate" title={integration.connection_detail}>
              {integration.connection_detail}
            </p>
          )}
          {integration.last_synced_at && (
            <p className="text-caption-sm text-gray-500 mt-1">
              Última sync: {relativeTime(integration.last_synced_at)}
            </p>
          )}
          {integration.status === 'error' && integration.error_message && (
            <p className="text-caption-sm text-urgent/80 mt-1 truncate">
              {integration.error_message}
            </p>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 mt-3 pt-3 border-t border-border/50 flex-wrap">
        {integration.status !== 'disconnected' && (
          <Button
            variant="ghost"
            size="sm"
            loading={syncMutation.isPending}
            onClick={() => syncMutation.mutate()}
            leftIcon={<RefreshCw size={13} strokeWidth={1.5} />}
          >
            Sincronizar
          </Button>
        )}
        <Button
          variant="danger"
          size="sm"
          loading={removeLoading}
          onClick={() => onRemove(integration.id)}
          leftIcon={<Unlink size={13} strokeWidth={1.5} />}
          className="ml-auto"
        >
          Remover
        </Button>
      </div>
    </div>
  )
}

// ── Catalog card (unconfigured connector) ──────────────────────────────────

interface CatalogCardProps {
  def: ConnectorDef
  onAdd: () => void
}

function CatalogCard({ def, onAdd }: CatalogCardProps) {
  return (
    <div className="bg-surface border border-border rounded-md p-4 hover:border-gray-500 transition-colors duration-normal">
      <div className="flex items-start gap-3">
        <ProviderBadge color={def.color} label={def.label} />
        <div className="flex-1 min-w-0">
          <h3 className="text-body-sm font-medium text-white truncate">{def.label}</h3>
          <p className="text-caption text-gray-400 mt-0.5">{def.description}</p>
        </div>
      </div>
      <div className="mt-3 pt-3 border-t border-border/50">
        <Button
          variant="secondary"
          size="sm"
          onClick={onAdd}
          leftIcon={<Plus size={13} strokeWidth={1.5} />}
        >
          Conectar
        </Button>
      </div>
    </div>
  )
}

// ── Skeleton loader ────────────────────────────────────────────────────────

function SkeletonGrid({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="h-28 bg-surface border border-border rounded-md animate-pulse" />
      ))}
    </div>
  )
}

// ── IntegrationsPanel (self-contained, placed in Admin > Integrações) ──────

export function IntegrationsPanel() {
  const { clientId } = useAuth()
  const qc = useQueryClient()
  const [modalConnector, setModalConnector] = useState<ConnectorDef | null>(null)
  const [removingId, setRemovingId] = useState<string | null>(null)

  const { data: integrations = [], isLoading } = useQuery({
    queryKey: ['integrations', clientId ?? ''],
    queryFn: () => fetchIntegrations(clientId!),
    enabled: !!clientId,
    staleTime: 60_000,
  })

  const removeMutation = useMutation({
    mutationFn: (id: string) => {
      if (!clientId) throw new Error('Sessão inválida')
      return deleteConnection(id, clientId)
    },
    onMutate: (id) => setRemovingId(id),
    onSettled: () => setRemovingId(null),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['integrations'] }),
  })

  // Separate configured integrations from unconfigured catalog entries.
  // A connector type may appear in both if the user has configured one instance
  // but the catalog still shows it as "add another".
  const configuredProviders = new Set(integrations.map((i) => i.provider.toLowerCase()))
  const unconfiguredDefs = CONNECTOR_CATALOG.filter(
    (def) => !configuredProviders.has(def.id.toLowerCase()),
  )

  if (!clientId || isLoading) return <SkeletonGrid />

  return (
    <div className="flex flex-col gap-8">
      {/* ── Configured integrations ──────────────────────────────────── */}
      {integrations.length > 0 && (
        <section>
          <h2 className="text-body-sm font-medium text-gray-200 mb-3">Conectados</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {integrations.map((integration) => (
              <IntegrationCard
                key={integration.id}
                integration={integration}
                onRemove={(id) => removeMutation.mutate(id)}
                removeLoading={removingId === integration.id}
              />
            ))}
          </div>
        </section>
      )}

      {/* ── Available connectors catalog ─────────────────────────────── */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <PlugZap size={15} strokeWidth={1.5} className="text-gray-400" />
          <h2 className="text-body-sm font-medium text-gray-200">
            {integrations.length > 0 ? 'Adicionar conector' : 'Conectores disponíveis'}
          </h2>
        </div>

        {unconfiguredDefs.length === 0 ? (
          <p className="text-caption text-gray-500">
            Todos os conectores disponíveis já estão configurados.
          </p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {unconfiguredDefs.map((def) => (
              <CatalogCard key={def.id} def={def} onAdd={() => setModalConnector(def)} />
            ))}
          </div>
        )}
      </section>

      {/* ── Connector modal ───────────────────────────────────────────── */}
      {modalConnector && (
        <ConnectorModal
          connector={modalConnector}
          open={!!modalConnector}
          onClose={() => setModalConnector(null)}
        />
      )}
    </div>
  )
}

// Re-export Integration type for backwards compatibility
export type { Integration, IntegrationStatus }
