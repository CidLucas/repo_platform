import { ArrowRight, X } from 'lucide-react'
import { cn } from '@/utils/cn'
import { useInsights, useDismissInsight } from '@/hooks/useInsight'
import type { ClientInsight } from '@/api/insights'


export function InsightsPanel() {
  const { data: insights, isLoading } = useInsights()
  const dismiss = useDismissInsight()

  if (isLoading) return null
  if (!insights || insights.length === 0) return null

  const visible = insights.slice(0, 3)
  const hasMore = insights.length > 3

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-display text-heading-lg text-white">Insights</h2>
        {hasMore && (
          <button className="text-caption text-blu-400 hover:text-blu-300 flex items-center gap-1 cursor-pointer transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500 rounded px-1">
            Ver todos {insights.length} <ArrowRight size={12} />
          </button>
        )}
      </div>

      <div className="space-y-3">
        {visible.map((insight) => (
          <InsightCard
            key={insight.id}
            insight={insight}
            onDismiss={() => dismiss.mutate(insight.id)}
          />
        ))}
      </div>
    </section>
  )
}

function severityAccent(severity: string | undefined) {
  if (severity === 'error' || severity === 'urgent') return 'border-l-urgent'
  if (severity === 'warning' || severity === 'attention') return 'border-l-attention'
  return 'border-l-blu-500'
}

function severityBg(severity: string | undefined) {
  if (severity === 'error' || severity === 'urgent') return 'bg-urgent-subtle'
  if (severity === 'warning' || severity === 'attention') return 'bg-attention-subtle'
  return ''
}

function InsightCard({
  insight,
  onDismiss,
}: {
  insight: ClientInsight
  onDismiss: () => void
}) {
  return (
    <div
      className={cn(
        'bg-surface border border-border border-l-[3px] rounded-md p-4',
        'relative group animate-fade-in',
        severityAccent(insight.severity),
        severityBg(insight.severity),
      )}
    >
      <button
        onClick={onDismiss}
        className={cn(
          'absolute top-3 right-3 p-1 rounded',
          'text-gray-500 hover:text-white hover:bg-elevated',
          'transition-colors cursor-pointer opacity-0 group-hover:opacity-100',
          'focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500'
        )}
        aria-label="Dispensar insight"
      >
        <X size={12} />
      </button>

      {insight.dimension && (
        <span className="text-section-label mb-1.5 block">
          {insight.dimension}
        </span>
      )}
      <p className="text-body-sm font-medium text-white mb-1 pr-6">{insight.title}</p>
      <p className="text-caption text-gray-300 line-clamp-3">{insight.observation}</p>
    </div>
  )
}
