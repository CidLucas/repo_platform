import { useState, useMemo } from 'react'
import { Package } from 'lucide-react'
import { cn } from '@/utils/cn'
import { CategoryTags } from '@/components/drawers/CategoryTags'
import { EmptyDrawer } from '@/components/drawers/EmptyDrawer'
import { SkeletonCard } from '@/components/primitives/SkeletonCard'
import type { Supplier } from '@/api/suppliers'

// ── Star rating ────────────────────────────────────────────────
function StarRating({ value, max = 5 }: { value: number; max?: number }) {
  return (
    <span className="flex gap-px" aria-label={`${value} de ${max} estrelas`}>
      {Array.from({ length: max }, (_, i) => (
        <svg
          key={i}
          width="12"
          height="12"
          viewBox="0 0 12 12"
          fill="none"
          className="shrink-0"
        >
          <polygon
            points="6,1 7.5,4.5 11,5 8.5,7.5 9,11 6,9 3,11 3.5,7.5 1,5 4.5,4.5"
            fill={i < value ? '#f59e0b' : 'none'}
            stroke={i < value ? '#f59e0b' : '#3D4D66'}
            strokeWidth="0.8"
          />
        </svg>
      ))}
    </span>
  )
}

// ── Category pill ──────────────────────────────────────────────
function CategoryPill({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-caption-sm bg-elevated border border-border text-gray-400">
      {label}
    </span>
  )
}

// ── Supplier row ───────────────────────────────────────────────
function SupplierRow({ supplier }: { supplier: Supplier }) {
  const rating = supplier.rating ?? 0

  return (
    <li className="group">
      <div
        className={cn(
          'flex items-start gap-3 px-4 py-3',
          'hover:bg-elevated transition-colors duration-normal cursor-default'
        )}
      >
        {/* Icon */}
        <span className="shrink-0 w-8 h-8 rounded flex items-center justify-center border border-[rgba(245,158,11,0.3)]"
          style={{ background: 'rgba(245,158,11,0.1)', color: '#f59e0b' }}>
          <Package size={14} strokeWidth={1.5} />
        </span>

        {/* Main info */}
        <div className="flex-1 min-w-0 space-y-1">
          <div className="flex items-center justify-between gap-2">
            <p className="text-body-sm text-white font-medium truncate">
              {supplier.name}
            </p>
            <StarRating value={rating} />
          </div>

          {/* Category + summary */}
          <div className="flex items-center gap-2 flex-wrap">
            {supplier.category && (
              <CategoryPill label={supplier.category} />
            )}
            {supplier.performance_summary && (
              <p className="text-caption text-gray-400 truncate flex-1">
                {supplier.performance_summary}
              </p>
            )}
          </div>
        </div>
      </div>
    </li>
  )
}

// ── SupplierList ───────────────────────────────────────────────
interface SupplierListProps {
  suppliers: Supplier[]
  loading?: boolean
  onAddSupplier?: () => void
}

const ALL_LABEL = 'Todos'

export function SupplierList({
  suppliers,
  loading = false,
  onAddSupplier,
}: SupplierListProps) {
  const [activeCategory, setActiveCategory] = useState(ALL_LABEL)

  // Derive unique categories from data
  const categories = useMemo(() => {
    const cats = new Set<string>()
    suppliers.forEach((s) => {
      if (s.category) cats.add(s.category)
    })
    return Array.from(cats).sort()
  }, [suppliers])

  // Filtered list
  const filtered = useMemo(() => {
    if (activeCategory === ALL_LABEL) return suppliers
    return suppliers.filter((s) => s.category === activeCategory)
  }, [suppliers, activeCategory])

  if (loading) {
    return (
      <div className="px-4 py-3 space-y-3">
        {[...Array(4)].map((_, i) => (
          <SkeletonCard key={i} lines={2} />
        ))}
      </div>
    )
  }

  if (suppliers.length === 0) {
    return (
      <EmptyDrawer
        message="Nenhum fornecedor cadastrado ainda."
        cta="Adicionar primeiro fornecedor"
        onCta={onAddSupplier}
        icon={<Package size={18} strokeWidth={1.5} />}
      />
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Category filter strip */}
      <CategoryTags
        categories={categories}
        active={activeCategory}
        onChange={setActiveCategory}
        allLabel={ALL_LABEL}
      />

      {/* Supplier rows */}
      {filtered.length === 0 ? (
        <EmptyDrawer
          message={`Nenhum fornecedor em "${activeCategory}".`}
          icon={<Package size={18} strokeWidth={1.5} />}
        />
      ) : (
        <ul className="divide-y divide-border flex-1">
          {filtered.map((supplier) => (
            <SupplierRow key={supplier.id} supplier={supplier} />
          ))}
        </ul>
      )}
    </div>
  )
}
