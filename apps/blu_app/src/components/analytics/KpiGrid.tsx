import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn } from '@/utils/cn'
import { SkeletonCard } from '@/components/primitives/SkeletonCard'
import { formatBRL, formatPct } from '@/utils/format'
import type { KpiMetrics } from '@/types/analytics'

interface KpiCell {
  label: string
  value: string
  trend?: 'up' | 'down' | 'flat'
  delta?: string
  highlight?: boolean
}

function buildCells(m: KpiMetrics): KpiCell[] {
  const cells: KpiCell[] = []

  if (m.faturamento !== undefined) {
    cells.push({
      label: 'Faturamento',
      value: formatBRL(m.faturamento),
      trend:
        m.faturamento_trend !== undefined
          ? m.faturamento_trend > 0 ? 'up' : m.faturamento_trend < 0 ? 'down' : 'flat'
          : undefined,
    })
  }
  if (m.despesas !== undefined) {
    cells.push({
      label: 'Despesas',
      value: formatBRL(m.despesas),
      trend:
        m.despesas_trend !== undefined
          ? m.despesas_trend > 0 ? 'up' : m.despesas_trend < 0 ? 'down' : 'flat'
          : undefined,
    })
  }
  if (m.margem !== undefined) {
    cells.push({
      label: 'Margem Bruta',
      value: formatPct(m.margem),
      highlight: m.margem > 30,
      trend:
        m.margem_trend !== undefined
          ? m.margem_trend > 0 ? 'up' : m.margem_trend < 0 ? 'down' : 'flat'
          : undefined,
    })
  }
  if (m.ticket_medio !== undefined) {
    cells.push({
      label: 'Ticket Médio',
      value: formatBRL(m.ticket_medio),
    })
  }

  return cells
}

interface KpiGridProps {
  metrics?: KpiMetrics
  loading?: boolean
  /** 2 = 2-column grid; 4 = 4-across on desktop */
  columns?: 2 | 4
}

export function KpiGrid({ metrics, loading, columns = 2 }: KpiGridProps) {
  const count = columns === 4 ? 4 : 2

  if (loading) {
    return (
      <div className={cn('grid gap-3', columns === 4 ? 'grid-cols-2 md:grid-cols-4' : 'grid-cols-2')}>
        {Array.from({ length: count }).map((_, i) => (
          <SkeletonCard key={i} lines={2} />
        ))}
      </div>
    )
  }

  if (!metrics) return null

  const cells = buildCells(metrics)
  if (cells.length === 0) return null

  return (
    <div
      className={cn(
        'grid gap-3',
        columns === 4 ? 'grid-cols-2 md:grid-cols-4' : 'grid-cols-2'
      )}
    >
      {cells.map((cell) => (
        <KpiCellCard key={cell.label} {...cell} />
      ))}
    </div>
  )
}

function TrendIcon({ trend }: { trend: 'up' | 'down' | 'flat' }) {
  if (trend === 'up') return <TrendingUp size={13} strokeWidth={1.5} className="text-ok" />
  if (trend === 'down') return <TrendingDown size={13} strokeWidth={1.5} className="text-urgent" />
  return <Minus size={13} strokeWidth={1.5} className="text-gray-500" />
}

function KpiCellCard({ label, value, trend, delta, highlight }: KpiCell) {
  return (
    <div className="bg-elevated border border-border rounded-md p-4">
      <p className="text-caption text-gray-400 mb-1">{label}</p>
      <p className={cn('text-mono-lg font-mono font-medium leading-tight', highlight ? 'text-ok' : 'text-white')}>
        {value}
      </p>
      {(trend || delta) && (
        <div className="flex items-center gap-1.5 mt-1.5">
          {trend && <TrendIcon trend={trend} />}
          {delta && (
            <span
              className={cn(
                'text-caption-sm',
                trend === 'up' ? 'text-ok' : trend === 'down' ? 'text-urgent' : 'text-gray-500'
              )}
            >
              {delta}
            </span>
          )}
        </div>
      )}
    </div>
  )
}
