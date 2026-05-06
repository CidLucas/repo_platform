import { Star, ChevronRight, X } from 'lucide-react'
import { cn } from '@/utils/cn'
import { useTrust } from '@/hooks/useTrust'

interface TrustMilestoneInsightProps {
  /** Called when user clicks the CTA button */
  onCta?: () => void
  className?: string
}

/**
 * Gamification moment card shown in Corkboard when a trust milestone is crossed.
 * Pulls the active milestone from TrustContext.
 *
 * 10 approvals → similar_toggle
 * 25 approvals → rules (advanced rules unlocked)
 * 50 approvals → full_config (full unlock + toast)
 */
export function TrustMilestoneInsight({ onCta, className }: TrustMilestoneInsightProps) {
  const { activeMilestone, dismissMilestone } = useTrust()

  if (!activeMilestone) return null

  const isFull = activeMilestone.trustLevel === 'full_config'

  const borderColor = isFull
    ? 'border-ok/40'
    : activeMilestone.trustLevel === 'rules'
    ? 'border-blu-500/40'
    : 'border-attention/40'

  const glowColor = isFull
    ? 'shadow-[0_0_16px_rgba(74,196,142,0.15)]'
    : activeMilestone.trustLevel === 'rules'
    ? 'shadow-[0_0_16px_rgba(62,107,255,0.15)]'
    : 'shadow-[0_0_16px_rgba(255,185,55,0.15)]'

  const badgeColor = isFull
    ? 'bg-ok/10 text-ok'
    : activeMilestone.trustLevel === 'rules'
    ? 'bg-blu-500/10 text-blu-400'
    : 'bg-attention/10 text-attention'

  const badgeLabel = isFull
    ? 'Configuração completa'
    : activeMilestone.trustLevel === 'rules'
    ? 'Regras avançadas'
    : 'Automação similar'

  return (
    <div
      className={cn(
        'relative bg-surface border rounded-md p-4',
        'transition-colors duration-normal',
        borderColor,
        glowColor,
        className
      )}
    >
      {/* Dismiss */}
      <button
        onClick={dismissMilestone}
        aria-label="Dispensar conquista"
        className={cn(
          'absolute top-3 right-3 w-6 h-6 flex items-center justify-center rounded',
          'text-gray-500 hover:text-white hover:bg-elevated',
          'transition-colors cursor-pointer',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500'
        )}
      >
        <X size={13} />
      </button>

      {/* Badge */}
      <span
        className={cn(
          'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-caption font-medium mb-3',
          badgeColor
        )}
      >
        <Star size={10} className="fill-current" />
        {badgeLabel}
      </span>

      {/* Content */}
      <p className="text-body-sm font-semibold text-white mb-1 pr-6">
        {activeMilestone.title}
      </p>
      <p className="text-caption text-gray-400 leading-relaxed mb-4">
        {activeMilestone.body}
      </p>

      {/* CTA */}
      <button
        onClick={() => {
          onCta?.()
          dismissMilestone()
        }}
        className={cn(
          'flex items-center gap-1.5 text-body-sm font-medium',
          'transition-colors cursor-pointer',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500 rounded',
          isFull
            ? 'text-ok hover:text-ok/80'
            : activeMilestone.trustLevel === 'rules'
            ? 'text-blu-400 hover:text-blu-300'
            : 'text-attention hover:text-attention/80'
        )}
      >
        {activeMilestone.ctaLabel}
        <ChevronRight size={14} strokeWidth={1.5} />
      </button>
    </div>
  )
}
