import { ShoppingCart, Users, Truck, Package } from 'lucide-react'
import { cn } from '@/utils/cn'
import { SkeletonCard } from '@/components/primitives/SkeletonCard'
import type { KpiMetrics } from '@/types/analytics'

interface AreaCardDef {
  key: keyof KpiMetrics
  label: string
  icon: React.ReactNode
  format: (v: number) => string
  colorClass: string
}

const AREA_CARDS: AreaCardDef[] = [
  {
    key: 'pedidos',
    label: 'Pedidos',
    icon: <ShoppingCart size={18} strokeWidth={1.5} />,
    format: (v) => v.toLocaleString('pt-BR'),
    colorClass: 'text-blu-400',
  },
  {
    key: 'clientes_ativos',
    label: 'Clientes',
    icon: <Users size={18} strokeWidth={1.5} />,
    format: (v) => v.toLocaleString('pt-BR'),
    colorClass: 'text-ok',
  },
  {
    key: 'fornecedores',
    label: 'Fornecedores',
    icon: <Truck size={18} strokeWidth={1.5} />,
    format: (v) => v.toLocaleString('pt-BR'),
    colorClass: 'text-attention',
  },
  {
    key: 'produtos',
    label: 'Produtos',
    icon: <Package size={18} strokeWidth={1.5} />,
    format: (v) => v.toLocaleString('pt-BR'),
    colorClass: 'text-gray-300',
  },
]

interface AreaCardsProps {
  metrics?: KpiMetrics
  loading?: boolean
  className?: string
}

export function AreaCards({ metrics, loading, className }: AreaCardsProps) {
  if (loading) {
    return (
      <div className={cn('grid grid-cols-2 md:grid-cols-4 gap-3', className)}>
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} lines={2} />
        ))}
      </div>
    )
  }

  if (!metrics) return null

  const visible = AREA_CARDS.filter((c) => metrics[c.key] !== undefined)
  if (visible.length === 0) return null

  return (
    <div className={cn('grid grid-cols-2 md:grid-cols-4 gap-3', className)}>
      {visible.map((card) => {
        const raw = metrics[card.key]
        const display = typeof raw === 'number' ? card.format(raw) : '—'
        return (
          <div
            key={card.key as string}
            className="bg-elevated border border-border rounded-md p-4 flex items-center gap-3"
          >
            <span className={cn('shrink-0', card.colorClass)}>{card.icon}</span>
            <div className="min-w-0">
              <p className="text-caption text-gray-400 truncate">{card.label}</p>
              <p className="text-body-sm font-mono font-medium text-white">{display}</p>
            </div>
          </div>
        )
      })}
    </div>
  )
}
