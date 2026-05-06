import { useQueries } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { TrendingUp, TrendingDown, Minus, BarChart2, Target } from 'lucide-react'
import { DeskLayout } from '@/components/layout/DeskLayout'
import { DeskSurface } from '@/components/desk/DeskSurface'
import { Corkboard } from '@/components/corkboard/Corkboard'
import { UnderDesk } from '@/components/underdesk/UnderDesk'
import { AgentIconBox } from '@/components/primitives/AgentIconBox'
import { SkeletonCard } from '@/components/primitives/SkeletonCard'
import { EmptyDrawer } from '@/components/drawers/EmptyDrawer'
import { useAuth } from '@/hooks/useAuth'
import { fetchApprovalsByAgent } from '@/api/approvals'
import { fetchInsights } from '@/api/insights'
import { fetchDimensionKpis, fetchEstrategiaHistory } from '@/api/estrategia'
import { fetchRoutines } from '@/api/routines'
import { ActiveRoutinesSlot } from '@/components/desk/ActiveRoutinesSlot'
import { relativeTime } from '@/utils/format'
import { cn } from '@/utils/cn'
import type { CorkboardInsight } from '@/components/corkboard/Corkboard'
import type { DimensionKpi, EstrategiaHistoryItem } from '@/api/estrategia'

const ESTRATEGIA_ORB = {
  shape: 'diamond' as const,
  color: '#3b82f6',
  glowColor: 'rgba(59,130,246,0.5)',
}

export function EstrategiaRoom() {
  const { clientId } = useAuth()

  const [approvalsQ, insightsQ, kpisQ, historyQ, routinesQ] = useQueries({
    queries: [
      {
        queryKey: ['approvals', 'estrategia', clientId ?? ''],
        queryFn: () => fetchApprovalsByAgent('estrategia', clientId!),
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
        queryKey: ['dimension-kpis', clientId ?? ''],
        queryFn: () => fetchDimensionKpis(clientId!),
        enabled: !!clientId,
        staleTime: 120_000,
      },
      {
        queryKey: ['estrategia-history', clientId ?? ''],
        queryFn: () => fetchEstrategiaHistory(clientId!),
        enabled: !!clientId,
        staleTime: 60_000,
      },
      {
        queryKey: ['routines', 'estrategia', clientId ?? ''],
        queryFn: () => fetchRoutines(clientId!, 'estrategia'),
        enabled: !!clientId,
        staleTime: 120_000,
      },
    ],
  })

  const estrategiaInsights: CorkboardInsight[] = (insightsQ.data ?? [])
    .filter((i) => !i.dimension || i.dimension === 'estrategia')
    .map((i) => ({ id: i.id, title: i.title, body: i.body, severity: undefined }))

  return (
      <DeskLayout
        title="Estratégia"
        subtitle="Análises, KPIs e tendências do negócio"
        agentSlug="estrategia"
        agentIcon={<AgentIconBox icon={Target} color={ESTRATEGIA_ORB.color} />}
        accentColor={ESTRATEGIA_ORB.color}
        // ── Left drawer — KPIs monitored ─────────────────────
        leftTitle="KPIs Monitorados"
        leftPillLabel="KPIs"
        leftPillIcon={<Target size={16} strokeWidth={1.5} />}
        leftContent={
          <KpiDrawer
            kpis={kpisQ.data ?? []}
            loading={kpisQ.isLoading}
          />
        }
        // ── Right drawer — Analyses history ───────────────────
        rightTitle="Análises"
        rightPillLabel="Histórico"
        rightPillIcon={<BarChart2 size={16} strokeWidth={1.5} />}
        rightContent={
          <EstrategiaHistoryDrawer
            items={historyQ.data ?? []}
            loading={historyQ.isLoading}
          />
        }
        corkboard={
          <Corkboard
            insights={estrategiaInsights}
            loading={insightsQ.isLoading}
            initialRows={1}
          />
        }
        underDesk={
          <UnderDesk
            agentSlug="estrategia"
            routinePrefix="estrategia"
            accentColor={ESTRATEGIA_ORB.color}
          />
        }
      >
        <DeskSurface
          approvals={approvalsQ.data ?? []}
          loading={approvalsQ.isLoading}
          agentName="Estratégia"
          agentOrbShape={ESTRATEGIA_ORB.shape}
          agentOrbColor={ESTRATEGIA_ORB.color}
          agentOrbGlow={ESTRATEGIA_ORB.glowColor}
          tasksSlot={<ActiveRoutinesSlot routines={routinesQ.data ?? []} loading={routinesQ.isLoading} accentColor={ESTRATEGIA_ORB.color} />}
          historySlot={
            <EstrategiaHistoryDrawer
              items={historyQ.data ?? []}
              loading={historyQ.isLoading}
            />
          }
        />
    </DeskLayout>
  )
}

// ── KPI drawer ─────────────────────────────────────────────────
function KpiDrawer({ kpis, loading }: { kpis: DimensionKpi[]; loading: boolean }) {
  const navigate = useNavigate()

  if (loading) {
    return (
      <div className="px-4 py-3 space-y-3">
        {[...Array(5)].map((_, i) => <SkeletonCard key={i} lines={2} />)}
      </div>
    )
  }

  if (kpis.length === 0) {
    return (
      <EmptyDrawer
        message="Nenhum KPI monitorado ainda."
        cta="Configurar KPIs"
        onCta={() => navigate('/admin')}
        icon={<Target size={18} strokeWidth={1.5} />}
      />
    )
  }

  // Group by dimension
  const grouped = kpis.reduce<Record<string, DimensionKpi[]>>((acc, kpi) => {
    const dim = kpi.dimension || 'Geral'
    if (!acc[dim]) acc[dim] = []
    acc[dim].push(kpi)
    return acc
  }, {})

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {Object.entries(grouped).map(([dim, items]) => (
        <div key={dim} className="mb-4">
          <p className="px-4 py-2 text-caption-sm text-gray-500 uppercase tracking-wider border-b border-border">
            {dim}
          </p>
          <ul className="divide-y divide-border">
            {items.map((kpi) => (
              <KpiRow key={kpi.id} kpi={kpi} />
            ))}
          </ul>
        </div>
      ))}
    </div>
  )
}

function KpiRow({ kpi }: { kpi: DimensionKpi }) {
  const TrendIcon =
    kpi.trend === 'up' ? TrendingUp : kpi.trend === 'down' ? TrendingDown : Minus

  const trendColor =
    kpi.trend === 'up' ? 'text-ok' : kpi.trend === 'down' ? 'text-urgent' : 'text-gray-400'

  const formatVal = (v: number | null) => {
    if (v === null) return '—'
    return kpi.unit === '%'
      ? `${v.toFixed(1)}%`
      : kpi.unit === 'BRL'
      ? `R$ ${v.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
      : String(v)
  }

  const pct = kpi.target_value && kpi.current_value != null
    ? Math.min((kpi.current_value / kpi.target_value) * 100, 100)
    : null

  return (
    <li className="px-4 py-3 hover:bg-elevated transition-colors duration-normal">
      <div className="flex items-center gap-2 mb-1">
        <p className="flex-1 text-body-sm text-gray-200 truncate">{kpi.label}</p>
        <span className={cn('flex items-center gap-0.5 text-caption-sm', trendColor)}>
          <TrendIcon size={12} strokeWidth={2} />
          <span className="font-mono">{formatVal(kpi.current_value)}</span>
        </span>
      </div>

      {/* Progress bar toward target */}
      {pct !== null && (
        <div className="h-1 bg-elevated rounded-full overflow-hidden mt-1">
          <div
            className="h-full rounded-full transition-all duration-slow"
            style={{
              width: `${pct}%`,
              backgroundColor: pct >= 80 ? 'var(--ok)' : pct >= 50 ? 'var(--attention)' : 'var(--urgent)',
            }}
          />
        </div>
      )}
    </li>
  )
}

// ── Estratégia history drawer ──────────────────────────────────
function EstrategiaHistoryDrawer({
  items,
  loading,
}: {
  items: EstrategiaHistoryItem[]
  loading: boolean
}) {
  if (loading) {
    return (
      <div className="px-4 py-3 space-y-3">
        {[...Array(4)].map((_, i) => <SkeletonCard key={i} lines={2} />)}
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <EmptyDrawer
        message="Nenhuma análise registrada."
        icon={<BarChart2 size={18} strokeWidth={1.5} />}
      />
    )
  }

  return (
    <ul className="divide-y divide-border">
      {items.map((item) => (
        <li key={item.id} className="px-4 py-3 hover:bg-elevated transition-colors duration-normal">
          <div className="flex items-start gap-2">
            <span
              className="w-2 h-2 rounded-full mt-1.5 shrink-0"
              style={{
                backgroundColor: item.action === 'approved' ? 'var(--ok)' : 'var(--urgent)',
              }}
            />
            <div className="flex-1 min-w-0">
              <p className="text-body-sm text-gray-200 truncate">{item.title}</p>
              {item.outcome_summary && (
                <p className="text-caption-sm text-blu-300 mt-0.5 line-clamp-2">
                  {item.outcome_summary}
                </p>
              )}
              <p className="text-caption-sm text-gray-500 mt-0.5">{relativeTime(item.created_at)}</p>
            </div>
          </div>
        </li>
      ))}
    </ul>
  )
}

