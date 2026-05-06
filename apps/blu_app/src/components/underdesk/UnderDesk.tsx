import { useState, type ReactNode } from 'react'
import { ChevronRight } from 'lucide-react'
import { cn } from '@/utils/cn'
import { RoutineList } from './RoutineList'
import { ConfigPanel } from './ConfigPanel'
import { RuleBuilder } from './RuleBuilder'
import { TrustLevelBadge } from '@/components/trust/TrustMilestoneToast'
import { useTrust } from '@/hooks/useTrust'
import type { AgentSlug } from '@/types/agent'

interface UnderDeskProps {
  agentSlug: AgentSlug
  /** Prefix for filtering routines, e.g. "compras" */
  routinePrefix?: string
  /**
   * Override trust level. If omitted, reads from TrustContext automatically.
   * Useful in stories or isolated renders.
   */
  trustLevel?: string
  /** Optional extra slot rendered above routines (room-specific) */
  extraSlot?: ReactNode
  /** Agent accent color — drives icon tints, toggles, and section labels */
  accentColor?: string
  className?: string
}

/**
 * [▶ Rotinas e Configurações] pill at the bottom of the desk.
 * Expands via CSS max-height accordion — no layout shift.
 * Trust level is read from TrustContext unless overridden by prop.
 */
export function UnderDesk({
  agentSlug,
  routinePrefix,
  trustLevel: trustLevelProp,
  extraSlot,
  accentColor,
  className,
}: UnderDeskProps) {
  const [open, setOpen] = useState(false)
  const { trustLevel: ctxTrustLevel } = useTrust()
  const trustLevel = trustLevelProp ?? ctxTrustLevel

  return (
    <div
      className={cn(
        'mt-4 border border-border rounded-md bg-surface overflow-hidden',
        className
      )}
    >
      {/* Colored top accent strip */}
      {accentColor && (
        <div className="h-[3px] w-full" style={{ background: `linear-gradient(90deg, ${accentColor}, ${accentColor}55)` }} />
      )}

      {/* Toggle pill */}
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className={cn(
          'w-full flex items-center gap-2 px-4 py-3 text-left',
          'text-body-sm text-gray-400 hover:text-white transition-colors cursor-pointer',
          'focus-visible:outline-none focus-visible:ring-inset focus-visible:ring-2 focus-visible:ring-blu-500'
        )}
      >
        <ChevronRight
          size={14}
          strokeWidth={1.5}
          className={cn(
            'shrink-0 transition-transform duration-slow',
            open && 'rotate-90'
          )}
          style={open && accentColor ? { color: accentColor } : undefined}
        />
        <span className="flex-1" style={open && accentColor ? { color: accentColor } : undefined}>
          Rotinas e Configurações
        </span>
        {/* Trust level badge — visible in collapsed state so it's discoverable */}
        <TrustLevelBadge trustLevel={trustLevel} />
      </button>

      {/* Accordion content — CSS max-height transition */}
      <div
        className={cn(
          'overflow-hidden transition-all duration-slow ease-in-out',
          open ? 'max-h-[800px] opacity-100' : 'max-h-0 opacity-0'
        )}
        aria-hidden={!open}
      >
        <div className="border-t border-border divide-y divide-border">
          {/* Context hint when trust not yet established */}
          {trustLevel === 'none' && (
            <div className="px-4 py-3 bg-elevated/50">
              <p className="text-caption text-gray-400">
                Rotinas e automações são desbloqueadas conforme você aprova decisões.
                Quanto mais o Blu conhece seu negócio, mais autônomo ele fica.
              </p>
            </div>
          )}

          {/* Extra room-specific slot */}
          {extraSlot && (
            <div className="py-2">{extraSlot}</div>
          )}

          {/* Routine list */}
          <div className="py-2">
            <p className="text-section-label px-4 py-2">Rotinas</p>
            <RoutineList prefix={routinePrefix ?? agentSlug} accentColor={accentColor} />
          </div>

          {/* Rule builder (trust-gated — hidden until 25 approvals) */}
          <div className="py-2">
            <RuleBuilder
              agentSlug={agentSlug}
              trustLevel="rules"
              currentTrustLevel={trustLevel}
            />
          </div>

          {/* Config panel */}
          <div className="py-2">
            <ConfigPanel agentSlug={agentSlug} accentColor={accentColor} />
          </div>
        </div>
      </div>
    </div>
  )
}
