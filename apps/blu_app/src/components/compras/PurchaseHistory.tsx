import { useMemo } from 'react'
import { CheckCircle, XCircle, ShoppingCart } from 'lucide-react'
import { cn } from '@/utils/cn'
import { SkeletonCard } from '@/components/primitives/SkeletonCard'
import { formatBRL, relativeTime } from '@/utils/format'
import type { PurchaseHistoryItem } from '@/api/suppliers'

// ── Spend by category ──────────────────────────────────────────
interface CategorySpend {
  category: string
  total: number
  count: number
}

function SpendByCategory({ items }: { items: PurchaseHistoryItem[] }) {
  const byCategory = useMemo(() => {
    const map = new Map<string, CategorySpend>()
    items.forEach((item) => {
      if (item.status !== 'approved') return
      const cat = item.category ?? 'Outros'
      const existing = map.get(cat) ?? { category: cat, total: 0, count: 0 }
      existing.total += item.amount ?? 0
      existing.count += 1
      map.set(cat, existing)
    })
    return Array.from(map.values()).sort((a, b) => b.total - a.total)
  }, [items])

  const grandTotal = byCategory.reduce((s, c) => s + c.total, 0)

  if (byCategory.length === 0) return null

  return (
    <div className="px-4 py-3 border-t border-border">
      <p className="text-section-label mb-3">Gastos por categoria</p>
      <div className="space-y-2">
        {byCategory.map((cat) => {
          const pct = grandTotal > 0 ? (cat.total / grandTotal) * 100 : 0
          return (
            <div key={cat.category}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-caption text-gray-300">{cat.category}</span>
                <span className="text-caption-sm text-gray-400">
                  {grandTotal > 0 ? formatBRL(cat.total) : `${cat.count} compra${cat.count !== 1 ? 's' : ''}`}
                </span>
              </div>
              {/* Progress bar */}
              <div className="h-1 bg-elevated rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full bg-attention transition-all duration-slow"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
      {grandTotal > 0 && (
        <p className="text-caption-sm text-gray-500 mt-3 text-right">
          Total: {formatBRL(grandTotal)}
        </p>
      )}
    </div>
  )
}

// ── Purchase history list ──────────────────────────────────────
function PurchaseRow({ item }: { item: PurchaseHistoryItem }) {
  const approved = item.status === 'approved'

  return (
    <li className="flex items-start gap-3 px-4 py-3 hover:bg-elevated transition-colors duration-normal">
      {/* Status icon */}
      <span
        className={cn(
          'shrink-0 mt-0.5',
          approved ? 'text-ok' : 'text-urgent'
        )}
      >
        {approved
          ? <CheckCircle size={16} strokeWidth={1.5} />
          : <XCircle size={16} strokeWidth={1.5} />}
      </span>

      {/* Title + meta */}
      <div className="flex-1 min-w-0">
        <p className="text-body-sm text-gray-200 leading-snug line-clamp-2">
          {item.title}
        </p>
        <div className="flex items-center gap-2 mt-0.5">
          {item.category && (
            <span className="text-caption-sm text-gray-500">{item.category}</span>
          )}
          {item.amount != null && item.amount > 0 && (
            <span className={cn('text-caption-sm font-medium', approved ? 'text-ok' : 'text-gray-500')}>
              {formatBRL(item.amount)}
            </span>
          )}
        </div>
      </div>

      {/* Timestamp */}
      <span className="shrink-0 text-caption-sm text-gray-500">
        {relativeTime(item.created_at)}
      </span>
    </li>
  )
}

// ── PurchaseHistory ────────────────────────────────────────────
interface PurchaseHistoryProps {
  items: PurchaseHistoryItem[]
  loading?: boolean
}

export function PurchaseHistory({ items, loading = false }: PurchaseHistoryProps) {
  if (loading) {
    return (
      <div className="px-4 py-3 space-y-3">
        {[...Array(5)].map((_, i) => (
          <SkeletonCard key={i} lines={2} />
        ))}
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
        <div className="w-10 h-10 rounded-full bg-elevated flex items-center justify-center mb-3 text-gray-500">
          <ShoppingCart size={18} strokeWidth={1.5} />
        </div>
        <p className="text-body-sm text-gray-400">
          Nenhuma compra registrada ainda.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col">
      {/* History label */}
      <div className="px-4 pt-3 pb-1">
      <p className="text-section-label mb-2">Últimas compras</p>
      </div>

      {/* Rows */}
      <ul className="divide-y divide-border">
        {items.map((item) => (
          <PurchaseRow key={item.id} item={item} />
        ))}
      </ul>

      {/* Spend by category summary */}
      <SpendByCategory items={items} />
    </div>
  )
}
