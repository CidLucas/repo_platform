import { useNavigate } from 'react-router-dom'
import { cn } from '@/utils/cn'
import { useAgents, useAgentReadinessMap } from '@/hooks/useAgent'
import { AgentBadge } from '@/components/navigation/AgentBadge'
import { AGENT_MAP } from '@/utils/constants'
import type { AgentStatus } from '@/types/agent'

/**
 * Desktop-only horizontal strip of 6 agent orbs.
 * Hidden on mobile (hidden md:flex) — the AgentNav covers this on small screens.
 */
export function AgentStatusRow() {
  const { data: agents } = useAgents()
  const readinessMap = useAgentReadinessMap()
  const navigate = useNavigate()

  return (
    <div className="hidden md:flex items-center gap-4 flex-wrap">
      {(agents ?? []).map((agent) => {
        const def = AGENT_MAP[agent.agent_slug]
        if (!def) return null

        const readiness = readinessMap[agent.agent_slug]
        // Overlay readiness onto the live operational status:
        // blocked → offline, partial → attention, ready → keep current_status
        const badgeStatus: AgentStatus =
          readiness?.status === 'blocked'  ? 'offline'
          : readiness?.status === 'partial' ? 'attention'
          : (agent.current_status as AgentStatus) ?? 'idle'

        const isBlocked = readiness?.status === 'blocked'
        const tooltipText = isBlocked && (readiness?.missing_docs?.length ?? 0) > 0
          ? `Documentos necessários: ${readiness.missing_docs.slice(0, 3).join(', ')}`
          : readiness?.status === 'partial'
          ? 'Capacidade parcial'
          : undefined

        return (
          <button
            key={agent.agent_slug}
            onClick={isBlocked ? undefined : () => navigate(def.route)}
            disabled={isBlocked}
            title={tooltipText}
            className={cn(
              'flex flex-col items-center gap-1.5 p-3 rounded-md min-w-[72px]',
              'bg-surface border border-border',
              'transition-colors group relative',
              isBlocked
                ? 'opacity-40 cursor-not-allowed'
                : 'hover:border-blu-500/40 hover:bg-elevated cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500'
            )}
            aria-label={`Ir para ${def.name}`}
          >
            <div className="relative">
              <AgentBadge
                shape={def.shape}
                color={def.color}
                glowColor={def.glowColor}
                size={32}
                status={badgeStatus}
              />
              {/* Pending count badge — hidden when blocked */}
              {!isBlocked && agent.pending_count > 0 && (
                <span
                  className={cn(
                    'absolute -top-1 -right-1 min-w-[16px] h-4 px-1',
                    'flex items-center justify-center rounded-full',
                    'text-caption-sm font-medium leading-none',
                    'bg-urgent text-white'
                  )}
                >
                  {agent.pending_count}
                </span>
              )}
            </div>
            <span className={cn(
              'text-caption-sm transition-colors',
              isBlocked ? 'text-gray-600' : 'text-gray-300 group-hover:text-white'
            )}>
              {def.name}
            </span>
          </button>
        )
      })}
    </div>
  )
}
