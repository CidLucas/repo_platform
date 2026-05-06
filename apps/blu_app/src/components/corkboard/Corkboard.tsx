import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { cn } from '@/utils/cn'
import { InsightCard } from './InsightCard'
import { SkeletonCard } from '@/components/primitives/SkeletonCard'
import { useDismissInsight } from '@/hooks/useInsight'
import { TrustMilestoneInsight } from '@/components/trust/TrustMilestoneInsight'
import { useTrust } from '@/hooks/useTrust'

export interface CorkboardInsight {
  id: string
  title: string
  body: string
  severity?: 'critical' | 'warning' | 'info' | 'positive'
  ctaLabel?: string
  onCta?: () => void
}

interface CorkboardProps {
  insights: CorkboardInsight[]
  loading?: boolean
  /** How many rows visible before "Ver mais" (each row = 1 card on mobile, 2 on md, 3 on lg) */
  initialRows?: number
  /** Optional callback when the trust milestone CTA is clicked (e.g. open UnderDesk) */
  onTrustCta?: () => void
  className?: string
}

/** Collapsed by default to 1 row; "Ver mais" expands all */
export function Corkboard({
  insights,
  loading = false,
  initialRows = 1,
  onTrustCta,
  className,
}: CorkboardProps) {
  const [expanded, setExpanded] = useState(false)
  const dismiss = useDismissInsight()
  const { activeMilestone } = useTrust()

  // On mobile: 1 col, md: 2 col, lg: 3 col
  // initialRows=1 → show 1/2/3 cards respectively; we clamp to a safe initial slice
  const INITIAL_VISIBLE = initialRows * 3 // show at most 3*initialRows cards (enough for 1 row on all breakpoints)
  const visible = expanded ? insights : insights.slice(0, INITIAL_VISIBLE)
  const hasMore = insights.length > INITIAL_VISIBLE

  if (loading) {
    return (
      <div className={cn('grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3', className)}>
        {[...Array(3)].map((_, i) => (
          <SkeletonCard key={i} lines={2} />
        ))}
      </div>
    )
  }

  const isEmpty = insights.length === 0 && !activeMilestone

  if (isEmpty) {
    return (
      <p className="text-caption text-gray-500 text-center py-6">
        Nenhum insight disponível.
      </p>
    )
  }

  return (
    <div className={cn('space-y-3', className)}>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {/* Trust milestone card — always first, spans one column */}
        {activeMilestone && (
          <TrustMilestoneInsight onCta={onTrustCta} />
        )}

        {visible.map((insight) => (
          <InsightCard
            key={insight.id}
            id={insight.id}
            title={insight.title}
            body={insight.body}
            severity={insight.severity}
            ctaLabel={insight.ctaLabel}
            onCta={insight.onCta}
            onDismiss={(id) => dismiss.mutate(id)}
          />
        ))}
      </div>

      {hasMore && (
        <div className="flex justify-center">
          <button
            onClick={() => setExpanded((v) => !v)}
            className="flex items-center gap-1.5 text-caption text-gray-400
              hover:text-white transition-colors cursor-pointer py-1 px-3 rounded
              hover:bg-elevated focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500"
          >
            {expanded ? (
              <>
                <ChevronUp size={13} /> Ver menos
              </>
            ) : (
              <>
                <ChevronDown size={13} />
                Ver mais {insights.length - INITIAL_VISIBLE} insights →
              </>
            )}
          </button>
        </div>
      )}
    </div>
  )
}
