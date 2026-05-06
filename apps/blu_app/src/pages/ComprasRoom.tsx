import { useQueries } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { ShoppingCart, Boxes, History } from 'lucide-react'
import { DeskLayout } from '@/components/layout/DeskLayout'
import { DeskSurface } from '@/components/desk/DeskSurface'
import { Corkboard } from '@/components/corkboard/Corkboard'
import { UnderDesk } from '@/components/underdesk/UnderDesk'
import { AgentIconBox } from '@/components/primitives/AgentIconBox'
import { SupplierList } from '@/components/compras/SupplierList'
import { PurchaseHistory } from '@/components/compras/PurchaseHistory'
import { useAuth } from '@/hooks/useAuth'
import { fetchApprovalsByAgent } from '@/api/approvals'
import { fetchInsights } from '@/api/insights'
import { fetchSuppliers, fetchComprasHistory } from '@/api/suppliers'
import { fetchRoutines } from '@/api/routines'
import { ActiveRoutinesSlot } from '@/components/desk/ActiveRoutinesSlot'
import type { CorkboardInsight } from '@/components/corkboard/Corkboard'

const COMPRAS_ORB = {
  shape: 'hexagon' as const,
  color: '#f59e0b',
  glowColor: 'rgba(245,158,11,0.5)',
}

export function ComprasRoom() {
  const { clientId } = useAuth()
  const navigate = useNavigate()

  // ── Parallel data fetching ──────────────────────────────────
  const [approvalsQ, insightsQ, suppliersQ, historyQ, routinesQ] = useQueries({
    queries: [
      {
        queryKey: ['approvals', 'compras', clientId ?? ''],
        queryFn: () => fetchApprovalsByAgent('compras', clientId!),
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
        queryKey: ['suppliers', clientId ?? ''],
        queryFn: () => fetchSuppliers(clientId!),
        enabled: !!clientId,
        staleTime: 60_000,
      },
      {
        queryKey: ['compras-history', clientId ?? ''],
        queryFn: () => fetchComprasHistory(clientId!),
        enabled: !!clientId,
        staleTime: 60_000,
      },
      {
        queryKey: ['routines', 'compras', clientId ?? ''],
        queryFn: () => fetchRoutines(clientId!, 'compras'),
        enabled: !!clientId,
        staleTime: 120_000,
      },
    ],
  })

  // ── Compras-filtered insights ───────────────────────────────
  const comprasInsights: CorkboardInsight[] = (insightsQ.data ?? [])
    .filter((i) => !i.dimension || i.dimension === 'compras')
    .map((i) => ({
      id: i.id,
      title: i.title,
      body: i.observation,
      severity: undefined,
    }))

  return (
    <DeskLayout
        title="Compras"
        subtitle="Gestão de fornecedores, cotações e estoque"
        agentSlug="compras"
        agentIcon={<AgentIconBox icon={ShoppingCart} color={COMPRAS_ORB.color} />}
        accentColor={COMPRAS_ORB.color}
        // ── Left drawer — Supplier list ─────────────────────
        leftTitle="Fornecedores"
        leftPillLabel="Fornecedores"
        leftPillIcon={<Boxes size={16} strokeWidth={1.5} />}
        leftContent={
          <SupplierList
            suppliers={suppliersQ.data ?? []}
            loading={suppliersQ.isLoading}
            onAddSupplier={() => navigate('/admin')}
          />
        }
        // ── Right drawer — Purchase history ─────────────────
        rightTitle="Histórico"
        rightPillLabel="Histórico"
        rightPillIcon={<History size={16} strokeWidth={1.5} />}
        rightContent={
          <PurchaseHistory
            items={historyQ.data ?? []}
            loading={historyQ.isLoading}
          />
        }
        // ── Corkboard — Supplier/pricing insights ───────────
        corkboard={
          <Corkboard
            insights={comprasInsights}
            loading={insightsQ.isLoading}
            initialRows={1}
          />
        }
        // ── UnderDesk — Routines & config ───────────────────
        underDesk={
          <UnderDesk
            agentSlug="compras"
            routinePrefix="compras"
            accentColor={COMPRAS_ORB.color}
            extraSlot={
              <div className="px-4 py-3">
                <p className="text-caption-sm text-gray-500 uppercase tracking-wider mb-2">
                  Alertas
                </p>
                <p className="text-body-sm text-gray-400">
                  Configure limites de estoque e cotações automáticas abaixo.
                </p>
              </div>
            }
          />
        }
      >
        {/* ── Desk Surface (centre) ─────────────────────────── */}
        <DeskSurface
          approvals={approvalsQ.data ?? []}
          loading={approvalsQ.isLoading}
          agentName="Compras"
          agentOrbShape={COMPRAS_ORB.shape}
          agentOrbColor={COMPRAS_ORB.color}
          agentOrbGlow={COMPRAS_ORB.glowColor}
          tasksSlot={<ActiveRoutinesSlot routines={routinesQ.data ?? []} loading={routinesQ.isLoading} accentColor={COMPRAS_ORB.color} />}
          historySlot={
            <PurchaseHistory
              items={historyQ.data ?? []}
              loading={historyQ.isLoading}
            />
          }
        />
    </DeskLayout>
  )
}

