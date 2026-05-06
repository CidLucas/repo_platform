import { useState } from 'react'
import { BarChart2, ChevronDown, ChevronUp } from 'lucide-react'
import { cn } from '@/utils/cn'
import { useKpiSnapshot, useTimeSeries } from '@/hooks/useAnalytics'
import { formatBRL, formatPct } from '@/utils/format'
import { PeriodSelector } from './PeriodSelector'
import { KpiGrid } from './KpiGrid'
import { AreaCards } from './AreaCards'
import { ChartContainer } from './ChartContainer'
import { ActivityFeed } from './ActivityFeed'
import type { KpiPeriod } from '@/types/analytics'

interface AnalyticsCardProps {
  /** Start collapsed (default) or expanded */
  defaultExpanded?: boolean
  className?: string
}

/**
 * Collapsible analytics module used inside FinanceiroRoom (below Corkboard)
 * and as an expanded view inside NumbersPanel on the Home screen.
 *
 * Contains: PeriodSelector → KpiGrid → AreaCards → ChartContainer → ActivityFeed
 */
export function AnalyticsCard({ defaultExpanded = false, className }: AnalyticsCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const [period, setPeriod] = useState<KpiPeriod>('30d')

  const { data: snapshot, isLoading: kpiLoading } = useKpiSnapshot(period)
  const { data: series, isLoading: seriesLoading } = useTimeSeries(period)

  const m = snapshot?.metrics

  // 1-line summary shown in collapsed header
  const summary = m
    ? [
        m.faturamento !== undefined && `Faturamento: ${formatBRL(m.faturamento)}`,
        m.despesas !== undefined && `Despesas: ${formatBRL(m.despesas)}`,
        m.margem !== undefined && `Margem: ${formatPct(m.margem)}`,
      ]
        .filter(Boolean)
        .join(' · ')
    : null

  return (
    <section
      className={cn('bg-surface border border-border rounded-md shadow-md', className)}
      aria-label="Analytics financeiro"
    >
      {/* ── Collapsible header ──────────────────────────── */}
      <button
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
        className={cn(
          'w-full flex items-center gap-3 px-4 py-3 cursor-pointer',
          'transition-colors duration-normal hover:bg-elevated/60',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blu-500',
          expanded ? 'rounded-t-md' : 'rounded-md'
        )}
      >
        <BarChart2 size={16} strokeWidth={1.5} className="text-blu-400 shrink-0" />
        <div className="flex-1 min-w-0 text-left">
          <p className="text-body-sm font-medium text-white">Analytics</p>
          {summary && !expanded && (
            <p className="text-caption text-gray-400 truncate mt-0.5">{summary}</p>
          )}
        </div>
        {expanded
          ? <ChevronUp size={15} strokeWidth={1.5} className="text-gray-400 shrink-0" />
          : <ChevronDown size={15} strokeWidth={1.5} className="text-gray-400 shrink-0" />
        }
      </button>

      {/* ── Expanded content (CSS max-height accordion) ── */}
      <div
        className={cn(
          'overflow-hidden transition-[max-height] ease-in-out',
          // 900px is generous; accordion never layout-shifts because max-height animates
          expanded ? 'max-h-[960px] duration-slow' : 'max-h-0 duration-slow'
        )}
      >
        <div className="border-t border-border px-4 pt-4 pb-6 space-y-5">
          {/* Period selector row */}
          <div className="flex items-center justify-between">
            <span className="text-caption text-gray-400">Período de análise</span>
            <PeriodSelector value={period} onChange={setPeriod} />
          </div>

          {/* KPI grid — 4-across on desktop */}
          <KpiGrid metrics={m} loading={kpiLoading} columns={4} />

          {/* Area cards — Pedidos / Clientes / Fornecedores / Produtos */}
          <AreaCards metrics={m} loading={kpiLoading} />

          {/* Tabbed charts */}
          <ChartContainer data={series} loading={seriesLoading} />

          {/* Activity feed */}
          <div>
            <h4 className="text-body-sm font-medium text-gray-300 mb-3">Atividade recente</h4>
            <ActivityFeed />
          </div>
        </div>
      </div>
    </section>
  )
}
