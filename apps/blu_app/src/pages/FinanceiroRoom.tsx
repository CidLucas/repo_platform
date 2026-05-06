import { useQueries } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Landmark, FileBarChart2, ExternalLink } from 'lucide-react'
import { DeskLayout } from '@/components/layout/DeskLayout'
import { DeskSurface } from '@/components/desk/DeskSurface'
import { MetricCard } from '@/components/desk/MetricCard'
import { Corkboard } from '@/components/corkboard/Corkboard'
import { UnderDesk } from '@/components/underdesk/UnderDesk'
import { AgentIconBox } from '@/components/primitives/AgentIconBox'
import { SkeletonCard } from '@/components/primitives/SkeletonCard'
import { EmptyDrawer } from '@/components/drawers/EmptyDrawer'
import { AnalyticsCard } from '@/components/analytics/AnalyticsCard'
import { useAuth } from '@/hooks/useAuth'
import { fetchApprovalsByAgent } from '@/api/approvals'
import { fetchInsights } from '@/api/insights'
import { getFinanceIndicators } from '@/services/analyticsService'
import { fetchConnectedAccounts, fetchReportRuns } from '@/api/financeiro'
import { fetchRoutines } from '@/api/routines'
import { ActiveRoutinesSlot } from '@/components/desk/ActiveRoutinesSlot'
import { formatBRL as formatCurrency } from '@/utils/format'
import { relativeTime } from '@/utils/format'
import type { CorkboardInsight } from '@/components/corkboard/Corkboard'

const FINANCEIRO_ORB = {
  shape: 'circle' as const,
  color: '#10b981',
  glowColor: 'rgba(16,185,129,0.5)',
}

export function FinanceiroRoom() {
  const { clientId } = useAuth()

  const [approvalsQ, insightsQ, kpiQ, accountsQ, reportsQ, routinesQ] = useQueries({
    queries: [
      {
        queryKey: ['approvals', 'financeiro', clientId ?? ''],
        queryFn: () => fetchApprovalsByAgent('financeiro', clientId!),
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
        queryKey: ['finance-indicators', '30d'],
        queryFn: () => getFinanceIndicators('30d'),
        enabled: !!clientId,
        staleTime: 120_000,
      },
      {
        queryKey: ['financeiro-accounts', clientId ?? ''],
        queryFn: () => fetchConnectedAccounts(clientId!),
        enabled: !!clientId,
        staleTime: 60_000,
      },
      {
        queryKey: ['financeiro-reports', clientId ?? ''],
        queryFn: () => fetchReportRuns(clientId!),
        enabled: !!clientId,
        staleTime: 60_000,
      },
      {
        queryKey: ['routines', 'financeiro', clientId ?? ''],
        queryFn: () => fetchRoutines(clientId!, 'financeiro'),
        enabled: !!clientId,
        staleTime: 120_000,
      },
    ],
  })

  const finInsights: CorkboardInsight[] = (insightsQ.data ?? [])
    .filter((i) => !i.dimension || i.dimension === 'financeiro')
    .map((i) => ({ id: i.id, title: i.title, body: i.body, severity: undefined }))

  const fin = kpiQ.data

  return (
      <DeskLayout
        title="Financeiro"
        subtitle="Fluxo de caixa, pagamentos e relatórios"
        agentSlug="financeiro"
        agentIcon={<AgentIconBox icon={Landmark} color={FINANCEIRO_ORB.color} />}
        accentColor={FINANCEIRO_ORB.color}
        // ── Left drawer — Connected accounts ─────────────────
        leftTitle="Contas"
        leftPillLabel="Contas"
        leftPillIcon={<Landmark size={16} strokeWidth={1.5} />}
        leftContent={
          <AccountsDrawer
            accounts={accountsQ.data ?? []}
            loading={accountsQ.isLoading}
          />
        }
        // ── Right drawer — Reports ────────────────────────────
        rightTitle="Relatórios"
        rightPillLabel="Relatórios"
        rightPillIcon={<FileBarChart2 size={16} strokeWidth={1.5} />}
        rightContent={
          <ReportsDrawer
            reports={reportsQ.data ?? []}
            loading={reportsQ.isLoading}
          />
        }
        // ── Corkboard — Cost trend insights + AnalyticsCard ──
        corkboard={
          <>
            <Corkboard
              insights={finInsights}
              loading={insightsQ.isLoading}
              initialRows={1}
            />
            {/* AnalyticsCard: full KPI grid + charts, collapsed by default */}
            <AnalyticsCard className="mt-4" />
          </>
        }
        underDesk={
          <UnderDesk
            agentSlug="financeiro"
            routinePrefix="financeiro"
            accentColor={FINANCEIRO_ORB.color}
          />
        }
      >
        {/* ── KPI Summary strip ────────────────────────────── */}
        {kpiQ.isLoading ? (
          <SkeletonCard lines={2} className="mb-3" />
        ) : fin ? (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-3">
            <MetricCard
              label="Receita Líquida (30d)"
              value={formatCurrency(fin.receita_liquida)}
              trend={fin.receita_yoy_perc != null ? (fin.receita_yoy_perc > 0 ? 'up' : fin.receita_yoy_perc < 0 ? 'down' : 'flat') : 'flat'}
              delta={fin.receita_yoy_perc != null ? `${Math.abs(fin.receita_yoy_perc).toFixed(1)}%` : undefined}
            />
            <MetricCard
              label="Custo Total (30d)"
              value={formatCurrency(fin.custo_total)}
              trend="flat"
            />
            <MetricCard
              label="Margem Bruta"
              value={fin.margem_bruta_perc != null ? `${fin.margem_bruta_perc.toFixed(1)}%` : '—'}
              trend={fin.margem_bruta_perc != null ? (fin.margem_bruta_perc >= 0 ? 'up' : 'down') : 'flat'}
              className="col-span-2 md:col-span-1"
            />
          </div>
        ) : null}

        {/* ── Desk Surface — Pending approvals ─────────────── */}
        <DeskSurface
          approvals={approvalsQ.data ?? []}
          loading={approvalsQ.isLoading}
          agentName="Financeiro"
          agentOrbShape={FINANCEIRO_ORB.shape}
          agentOrbColor={FINANCEIRO_ORB.color}
          agentOrbGlow={FINANCEIRO_ORB.glowColor}
          tasksSlot={<ActiveRoutinesSlot routines={routinesQ.data ?? []} loading={routinesQ.isLoading} accentColor={FINANCEIRO_ORB.color} />}
        />
    </DeskLayout>
  )
}

// ── Connected accounts drawer ──────────────────────────────────
function AccountsDrawer({
  accounts,
  loading,
}: {
  accounts: import('@/api/financeiro').ConnectedAccount[]
  loading: boolean
}) {
  const navigate = useNavigate()

  if (loading) {
    return (
      <div className="px-4 py-3 space-y-3">
        {[...Array(3)].map((_, i) => <SkeletonCard key={i} lines={2} />)}
      </div>
    )
  }

  if (accounts.length === 0) {
    return (
      <EmptyDrawer
        message="Nenhuma conta conectada."
        cta="Conectar conta bancária"
        onCta={() => navigate('/admin')}
        icon={<Landmark size={18} strokeWidth={1.5} />}
      />
    )
  }

  return (
    <ul className="divide-y divide-border">
      {accounts.map((acc) => (
        <li key={acc.id} className="px-4 py-3 flex items-center gap-3 hover:bg-elevated transition-colors duration-normal">
          {/* Status dot */}
          <span
            className="w-2 h-2 rounded-full shrink-0"
            style={{
              backgroundColor:
                acc.status === 'active' ? 'var(--ok)' :
                acc.status === 'error' ? 'var(--urgent)' : 'var(--gray-500)',
            }}
          />
          <div className="flex-1 min-w-0">
            <p className="text-body-sm text-white font-medium truncate">
              {acc.account_name ?? acc.provider}
            </p>
            <p className="text-caption text-gray-400">{acc.provider}</p>
          </div>
          {acc.balance !== null && (
            <span className="text-body-sm font-mono text-white shrink-0">
              {formatCurrency(acc.balance)}
            </span>
          )}
        </li>
      ))}
    </ul>
  )
}

// ── Reports drawer ─────────────────────────────────────────────
const REPORT_LABELS: Record<string, string> = {
  dre: 'DRE',
  cash_flow: 'Fluxo de Caixa',
  margin: 'Margem',
  custom: 'Personalizado',
}

const REPORT_STATUS_COLOR: Record<string, string> = {
  ready: 'text-ok',
  generating: 'text-attention',
  error: 'text-urgent',
}

function ReportsDrawer({
  reports,
  loading,
}: {
  reports: import('@/api/financeiro').ReportRun[]
  loading: boolean
}) {
  if (loading) {
    return (
      <div className="px-4 py-3 space-y-3">
        {[...Array(3)].map((_, i) => <SkeletonCard key={i} lines={2} />)}
      </div>
    )
  }

  if (reports.length === 0) {
    return (
      <EmptyDrawer
        message="Nenhum relatório gerado."
        icon={<FileBarChart2 size={18} strokeWidth={1.5} />}
      />
    )
  }

  return (
    <ul className="divide-y divide-border">
      {reports.map((report) => (
        <li key={report.id} className="px-4 py-3 flex items-center gap-3 hover:bg-elevated transition-colors duration-normal">
          <div className="flex-1 min-w-0">
            <p className="text-body-sm text-white font-medium truncate">
              {REPORT_LABELS[report.report_type] ?? 'Relatório'} — {report.period}
            </p>
            <p className={`text-caption-sm ${REPORT_STATUS_COLOR[report.status] ?? 'text-gray-400'}`}>
              {report.status === 'ready' ? 'Pronto' : report.status === 'generating' ? 'Gerando…' : 'Erro'}
              {' · '}{relativeTime(report.created_at)}
            </p>
          </div>
          {report.file_url && report.status === 'ready' && (
            <a
              href={report.file_url}
              target="_blank"
              rel="noopener noreferrer"
              className="shrink-0 text-blu-400 hover:text-blu-300 transition-colors duration-normal cursor-pointer"
              aria-label="Baixar relatório"
            >
              <ExternalLink size={14} strokeWidth={1.5} />
            </a>
          )}
        </li>
      ))}
    </ul>
  )
}

