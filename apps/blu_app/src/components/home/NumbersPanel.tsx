import { useState } from 'react'
import type React from 'react'
import { ChevronDown, ChevronUp, TrendingDown, ShoppingCart, Users, Receipt, DollarSign, Percent } from 'lucide-react'
import { cn } from '@/utils/cn'
import { useKpiSnapshot } from '@/hooks/useAnalytics'
import { SkeletonCard } from '@/components/primitives/SkeletonCard'
import { formatBRL, formatPct } from '@/utils/format'

interface KpiItem {
  label: string
  value: string
  icon: React.ElementType
  color: string
  highlight?: boolean
}

function IconBox({ icon: Icon, color }: { icon: React.ElementType; color: string }) {
  return (
    <div
      className="w-14 h-14 rounded-2xl flex items-center justify-center shrink-0 relative overflow-hidden"
      style={{
        background: `linear-gradient(135deg, ${color}, ${color}cc)`,
        boxShadow: `0 8px 24px ${color}60, 0 0 0 1px ${color}30`,
      }}
    >
      {/* White shimmer overlay */}
      <div
        className="absolute inset-0"
        style={{ background: 'linear-gradient(135deg, rgba(255,255,255,0.18), transparent)' }}
      />
      <Icon size={24} strokeWidth={1.75} color="white" style={{ position: 'relative', zIndex: 1 }} />
    </div>
  )
}

function MetricCard({ item }: { item: KpiItem }) {
  return (
    <div
      className={cn(
        'bg-surface rounded-md p-5 relative overflow-hidden',
        'border border-[rgba(255,255,255,0.08)]',
        'shadow-[0_4px_24px_rgba(0,0,0,0.4)]',
        'transition-all duration-normal cursor-default',
        'hover:-translate-y-1 hover:shadow-[0_8px_32px_rgba(0,0,0,0.5)]',
      )}
    >
      {/* Left accent bar */}
      <div
        className="absolute top-0 left-0 w-[3px] h-full"
        style={{ background: item.color }}
      />

      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-section-label mb-2">{item.label}</p>
          <p className={cn(
            'font-display text-display-md leading-none',
            item.highlight ? 'text-ok' : 'text-white'
          )}>
            {item.value}
          </p>
        </div>
        <IconBox icon={item.icon} color={item.color} />
      </div>
    </div>
  )
}

export function NumbersPanel() {
  const { data: snapshot, isLoading } = useKpiSnapshot('30d')
  const [expanded, setExpanded] = useState(true)

  if (isLoading) {
    return <SkeletonCard lines={1} className="h-12 py-3" />
  }

  const m = snapshot?.metrics

  if (!m) return null

  const items: KpiItem[] = [
    m.faturamento !== undefined && {
      label: 'Faturamento',
      value: formatBRL(m.faturamento),
      icon: DollarSign,
      color: '#10b981',
    },
    m.despesas !== undefined && {
      label: 'Despesas',
      value: formatBRL(m.despesas),
      icon: TrendingDown,
      color: '#E07A5F',
    },
    m.margem !== undefined && {
      label: 'Margem',
      value: formatPct(m.margem),
      highlight: m.margem > 30,
      icon: Percent,
      color: '#a855f7',
    },
    m.pedidos !== undefined && {
      label: 'Pedidos',
      value: m.pedidos.toLocaleString('pt-BR'),
      icon: ShoppingCart,
      color: '#3b82f6',
    },
    m.clientes_ativos !== undefined && {
      label: 'Clientes',
      value: m.clientes_ativos.toLocaleString('pt-BR'),
      icon: Users,
      color: '#f97316',
    },
    m.ticket_medio !== undefined && {
      label: 'Ticket médio',
      value: formatBRL(m.ticket_medio),
      icon: Receipt,
      color: '#06b6d4',
    },
  ].filter(Boolean) as KpiItem[]

  const summaryItems = items.slice(0, 3)

  return (
    <section>
      {/* Collapsed header */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className={cn(
          'w-full flex items-center justify-between px-1 py-2 mb-3 cursor-pointer',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500 rounded'
        )}
        aria-expanded={expanded}
        aria-label="Números do período"
      >
        <div className="flex items-center gap-3 min-w-0 flex-1 overflow-hidden">
          {summaryItems.map((item, i) => (
            <span key={item.label} className="flex items-center gap-1.5 shrink-0">
              {i > 0 && <span className="text-gray-600 select-none">·</span>}
              <span className="text-caption text-gray-400">{item.label}:</span>
              <span className="text-caption font-medium text-white">{item.value}</span>
            </span>
          ))}
        </div>
        <span className="text-gray-400 ml-3 shrink-0 flex items-center gap-1 text-caption">
          {expanded ? 'Recolher' : 'Ver números'}
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </span>
      </button>

      {/* Expanded grid of standalone KPI cards */}
      {expanded && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 animate-fade-in">
          {items.map((item) => (
            <MetricCard key={item.label} item={item} />
          ))}
        </div>
      )}

      {expanded && (
        <p className="text-caption-sm text-gray-500 mt-3 px-1">Últimos 30 dias</p>
      )}
    </section>
  )
}
