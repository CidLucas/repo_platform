import { useState, useMemo } from 'react'
import { useQueries } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Users, ShoppingBag, TrendingUp, TrendingDown, Minus, User } from 'lucide-react'
import { DeskLayout } from '@/components/layout/DeskLayout'
import { DeskSurface } from '@/components/desk/DeskSurface'
import { Corkboard } from '@/components/corkboard/Corkboard'
import { UnderDesk } from '@/components/underdesk/UnderDesk'
import { AgentIconBox } from '@/components/primitives/AgentIconBox'
import { SkeletonCard } from '@/components/primitives/SkeletonCard'
import { EmptyDrawer } from '@/components/drawers/EmptyDrawer'
import { CategoryTags } from '@/components/drawers/CategoryTags'
import { useAuth } from '@/hooks/useAuth'
import { fetchApprovalsByAgent } from '@/api/approvals'
import { fetchInsights } from '@/api/insights'
import { fetchCustomerSegments, fetchTopCustomers, fetchRecentTransactions } from '@/api/clientes'
import { formatBRL as formatCurrency } from '@/utils/format'
import { relativeTime } from '@/utils/format'
import { cn } from '@/utils/cn'
import type { CorkboardInsight } from '@/components/corkboard/Corkboard'
import type { CustomerRecord, CustomerSegment, CustomerTransaction, CustomerCluster } from '@/api/clientes'

const CLIENTES_ORB = {
  shape: 'pentagon' as const,
  color: '#f97316',
  glowColor: 'rgba(249,115,22,0.5)',
}

const CLUSTER_COLORS: Record<CustomerCluster, string> = {
  Alto: 'text-ok',
  Médio: 'text-attention',
  Baixo: 'text-gray-400',
}

const CLUSTER_BG: Record<CustomerCluster, string> = {
  Alto: 'bg-ok/10 border-ok/30',
  Médio: 'bg-attention/10 border-attention/30',
  Baixo: 'bg-elevated border-border',
}

export function ClientesRoom() {
  const { clientId } = useAuth()

  const [approvalsQ, insightsQ, segmentsQ, customersQ, transactionsQ] = useQueries({
    queries: [
      {
        queryKey: ['approvals', 'clientes', clientId ?? ''],
        queryFn: () => fetchApprovalsByAgent('clientes', clientId!),
        enabled: !!clientId,
        staleTime: 30_000,
      },
      {
        queryKey: ['insights'],
        queryFn: () => fetchInsights(),
        enabled: !!clientId,
        staleTime: 60_000,
      },
      {
        queryKey: ['customer-segments', clientId ?? ''],
        queryFn: () => fetchCustomerSegments(clientId!),
        enabled: !!clientId,
        staleTime: 120_000,
      },
      {
        queryKey: ['top-customers', clientId ?? ''],
        queryFn: () => fetchTopCustomers(clientId!),
        enabled: !!clientId,
        staleTime: 60_000,
      },
      {
        queryKey: ['recent-transactions', clientId ?? ''],
        queryFn: () => fetchRecentTransactions(clientId!),
        enabled: !!clientId,
        staleTime: 60_000,
      },
    ],
  })

  const clientesInsights: CorkboardInsight[] = (insightsQ.data ?? [])
    .filter((i) => !i.dimension || i.dimension === 'clientes')
    .map((i) => ({ id: i.id, title: i.title, body: i.body, severity: undefined }))

  return (
      <DeskLayout
        title="Clientes"
        subtitle="Segmentos, atividade e histórico de transações"
        agentSlug="clientes"
        agentIcon={<AgentIconBox icon={Users} color={CLIENTES_ORB.color} />}
        accentColor={CLIENTES_ORB.color}
        // ── Left drawer — Customer segments ──────────────────
        leftTitle="Segmentos"
        leftPillLabel="Segmentos"
        leftPillIcon={<Users size={16} strokeWidth={1.5} />}
        leftContent={
          <SegmentsDrawer
            segments={segmentsQ.data ?? []}
            customers={customersQ.data ?? []}
            loading={segmentsQ.isLoading || customersQ.isLoading}
          />
        }
        // ── Right drawer — Transaction history ───────────────
        rightTitle="Transações"
        rightPillLabel="Transações"
        rightPillIcon={<ShoppingBag size={16} strokeWidth={1.5} />}
        rightContent={
          <TransactionsDrawer
            transactions={transactionsQ.data ?? []}
            loading={transactionsQ.isLoading}
          />
        }
        corkboard={
          <Corkboard
            insights={clientesInsights}
            loading={insightsQ.isLoading}
            initialRows={1}
          />
        }
        underDesk={
          <UnderDesk
            agentSlug="clientes"
            routinePrefix="clientes"
            accentColor={CLIENTES_ORB.color}
          />
        }
      >
        {/* ── Segment summary strip ─────────────────────────── */}
        {!segmentsQ.isLoading && segmentsQ.data && segmentsQ.data.length > 0 && (
          <SegmentSummary segments={segmentsQ.data} />
        )}

        {/* ── Desk Surface — Approvals + top customers ─────── */}
        <DeskSurface
          approvals={approvalsQ.data ?? []}
          loading={approvalsQ.isLoading}
          agentName="Clientes"
          agentOrbShape={CLIENTES_ORB.shape}
          agentOrbColor={CLIENTES_ORB.color}
          agentOrbGlow={CLIENTES_ORB.glowColor}
          tasksSlot={<ClientesActiveTasks customers={customersQ.data ?? []} loading={customersQ.isLoading} />}
          historySlot={
            <TransactionsDrawer
              transactions={transactionsQ.data ?? []}
              loading={transactionsQ.isLoading}
            />
          }
        />
    </DeskLayout>
  )
}

// ── Segment summary strip ──────────────────────────────────────
function SegmentSummary({ segments }: { segments: CustomerSegment[] }) {
  return (
    <div className="grid grid-cols-3 gap-2 mb-3">
      {segments.map((seg) => (
        <div
          key={seg.cluster}
          className={cn('border rounded-md p-3 text-center', CLUSTER_BG[seg.cluster])}
        >
          <p className={cn('text-mono-lg font-mono font-medium', CLUSTER_COLORS[seg.cluster])}>
            {seg.count}
          </p>
          <p className="text-caption text-gray-400 mt-0.5">{seg.cluster}</p>
          {seg.avg_ticket !== null && (
            <p className="text-caption-sm text-gray-500 mt-0.5">{formatCurrency(seg.avg_ticket)}</p>
          )}
        </div>
      ))}
    </div>
  )
}

// ── Segments + customers drawer ────────────────────────────────
function SegmentsDrawer({
  segments,
  customers,
  loading,
}: {
  segments: CustomerSegment[]
  customers: CustomerRecord[]
  loading: boolean
}) {
  const navigate = useNavigate()
  const [activeCluster, setActiveCluster] = useState<string>('Todos')

  const clusters = useMemo(
    () => segments.map((s) => s.cluster),
    [segments]
  )

  const filtered = useMemo(() => {
    if (activeCluster === 'Todos') return customers
    return customers.filter((c) => c.cluster === activeCluster)
  }, [customers, activeCluster])

  if (loading) {
    return (
      <div className="px-4 py-3 space-y-3">
        {[...Array(5)].map((_, i) => <SkeletonCard key={i} lines={2} />)}
      </div>
    )
  }

  if (customers.length === 0) {
    return (
      <EmptyDrawer
        message="Nenhum cliente encontrado."
        cta="Importar clientes"
        onCta={() => navigate('/admin')}
        icon={<Users size={18} strokeWidth={1.5} />}
      />
    )
  }

  return (
    <div className="flex flex-col h-full">
      <CategoryTags
        categories={clusters}
        active={activeCluster}
        onChange={setActiveCluster}
        allLabel="Todos"
      />
      <ul className="divide-y divide-border flex-1 overflow-y-auto">
        {filtered.map((customer) => (
          <CustomerRow key={customer.id} customer={customer} />
        ))}
      </ul>
    </div>
  )
}

function CustomerRow({ customer }: { customer: CustomerRecord }) {
  return (
    <li className="flex items-center gap-3 px-4 py-3 hover:bg-elevated transition-colors duration-normal cursor-default">
      <div className="w-8 h-8 rounded-full bg-elevated border border-border flex items-center justify-center shrink-0">
        <User size={14} strokeWidth={1.5} className="text-gray-500" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-body-sm text-white truncate">{customer.name}</p>
        <div className="flex items-center gap-2 mt-0.5">
          {customer.cluster && (
            <span className={cn('text-caption-sm font-medium', CLUSTER_COLORS[customer.cluster])}>
              {customer.cluster}
            </span>
          )}
          {customer.avg_ticket !== null && (
            <span className="text-caption-sm text-gray-500">
              ticket médio {formatCurrency(customer.avg_ticket)}
            </span>
          )}
        </div>
      </div>
      <div className="text-right shrink-0">
        <p className="text-caption-sm text-gray-400">{customer.total_purchases} compras</p>
        {customer.last_purchase_at && (
          <p className="text-caption-sm text-gray-500">{relativeTime(customer.last_purchase_at)}</p>
        )}
      </div>
    </li>
  )
}

// ── Transactions drawer ────────────────────────────────────────
function TransactionsDrawer({
  transactions,
  loading,
}: {
  transactions: CustomerTransaction[]
  loading: boolean
}) {
  if (loading) {
    return (
      <div className="px-4 py-3 space-y-3">
        {[...Array(5)].map((_, i) => <SkeletonCard key={i} lines={2} />)}
      </div>
    )
  }

  if (transactions.length === 0) {
    return (
      <EmptyDrawer
        message="Nenhuma transação recente."
        icon={<ShoppingBag size={18} strokeWidth={1.5} />}
      />
    )
  }

  return (
    <ul className="divide-y divide-border">
      {transactions.map((tx) => (
        <li key={tx.id} className="px-4 py-3 hover:bg-elevated transition-colors duration-normal">
          <div className="flex items-start gap-3">
            <div className="flex-1 min-w-0">
              <p className="text-body-sm text-white truncate">{tx.customer_name}</p>
              <p className="text-caption-sm text-gray-400 truncate">{tx.description}</p>
              <p className="text-caption-sm text-gray-500 mt-0.5">{relativeTime(tx.date)}</p>
            </div>
            <div className="text-right shrink-0">
              <p className="text-body-sm font-mono text-white">{formatCurrency(tx.amount)}</p>
              <span
                className="text-caption-sm"
                style={{
                  color:
                    tx.status === 'completed' ? 'var(--ok)' :
                    tx.status === 'pending' ? 'var(--attention)' : 'var(--gray-400)',
                }}
              >
                {tx.status === 'completed' ? 'Concluído' : tx.status === 'pending' ? 'Pendente' : 'Cancelado'}
              </span>
            </div>
          </div>
        </li>
      ))}
    </ul>
  )
}

// ── Active tasks slot ──────────────────────────────────────────
function ClientesActiveTasks({
  customers,
  loading,
}: {
  customers: CustomerRecord[]
  loading: boolean
}) {
  if (loading) {
    return <SkeletonCard lines={3} />
  }

  const topCustomers = customers.slice(0, 3)

  if (topCustomers.length === 0) {
    return (
      <p className="text-caption text-gray-500 text-center py-4">
        Nenhum cliente ativo no momento.
      </p>
    )
  }

  return (
    <div className="space-y-2">
      <p className="text-caption-sm text-gray-500 uppercase tracking-wider mb-2">Top Clientes</p>
      {topCustomers.map((c) => {
        const TrendIcon = c.cluster === 'Alto' ? TrendingUp : c.cluster === 'Médio' ? Minus : TrendingDown
        const trendColor = c.cluster === 'Alto' ? 'text-ok' : c.cluster === 'Médio' ? 'text-attention' : 'text-gray-400'

        return (
          <div key={c.id} className="flex items-center gap-3 px-1 py-2 rounded hover:bg-elevated transition-colors duration-normal">
            <TrendIcon size={14} strokeWidth={1.5} className={cn('shrink-0 w-5 h-5', trendColor)} />
            <span className="flex-1 text-body-sm text-gray-200 truncate">{c.name}</span>
            {c.avg_ticket !== null && (
              <span className="text-caption-sm text-gray-500 shrink-0 font-mono">
                {formatCurrency(c.avg_ticket)}
              </span>
            )}
          </div>
        )
      })}
    </div>
  )
}
