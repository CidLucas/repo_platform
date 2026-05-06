import { cn } from '@/utils/cn'
import { AgentBadge } from '@/components/navigation/AgentBadge'
import type { OrbShape } from '@/types/agent'

interface LoadingAgentProps {
  /** Agent orb shape */
  shape?: OrbShape
  color?: string
  glowColor?: string
  label?: string
  /**
   * compact — inline horizontal layout for use inside DeskSurface working banner.
   * Default (false) — centered column layout for full loading state.
   */
  compact?: boolean
  className?: string
}

/**
 * Agent orb with `animate-orb-pulse` + optional label.
 *
 * Default variant: centered column, `py-10`. Used as full loading state.
 * Compact variant: inline row. Used inside DeskSurface when agent current_status='working'.
 */
export function LoadingAgent({
  shape = 'circle',
  color = '#4A90D9',
  glowColor = 'rgba(74,144,217,0.3)',
  label = 'Processando…',
  compact = false,
  className,
}: LoadingAgentProps) {
  if (compact) {
    return (
      <div
        className={cn('flex items-center gap-2', className)}
        aria-label={label || 'Agente processando'}
        role="status"
      >
        <AgentBadge
          shape={shape}
          color={color}
          glowColor={glowColor}
          size={20}
          status="working"
        />
        {label && (
          <p className="text-caption text-blu-300">{label}</p>
        )}
      </div>
    )
  }

  return (
    <div
      className={cn('flex flex-col items-center gap-3 py-10', className)}
      aria-label={label}
      role="status"
    >
      <AgentBadge
        shape={shape}
        color={color}
        glowColor={glowColor}
        size={36}
        status="working"
      />
      <p className="text-caption text-gray-400 animate-pulse">{label}</p>
    </div>
  )
}
