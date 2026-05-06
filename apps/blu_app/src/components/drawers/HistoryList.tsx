import { cn } from '@/utils/cn'
import { AgentBadge } from '@/components/navigation/AgentBadge'
import { AGENT_MAP } from '@/utils/constants'
import { relativeTime } from '@/utils/format'
import type { AgentSlug } from '@/types/agent'

export interface HistoryItem {
  id: string
  title: string
  agentSlug: AgentSlug
  action: 'approved' | 'rejected' | 'snoozed' | 'other'
  timestamp: string
}

interface HistoryListProps {
  items: HistoryItem[]
  loading?: boolean
  className?: string
}

const actionLabel: Record<HistoryItem['action'], string> = {
  approved: 'Aprovado',
  rejected: 'Rejeitado',
  snoozed: 'Adiado',
  other: 'Atualizado',
}

const actionColor: Record<HistoryItem['action'], string> = {
  approved: 'text-ok',
  rejected: 'text-urgent',
  snoozed: 'text-attention',
  other: 'text-gray-400',
}

export function HistoryList({ items, loading = false, className }: HistoryListProps) {
  if (loading) {
    return (
      <div className={cn('space-y-3 px-4 py-3', className)}>
        {[...Array(3)].map((_, i) => (
          <div key={i} className="flex items-center gap-3">
            <div className="w-6 h-6 rounded-full bg-elevated animate-shimmer" />
            <div className="flex-1 space-y-1.5">
              <div className="h-3 w-3/4 rounded bg-elevated animate-shimmer" />
              <div className="h-2.5 w-1/3 rounded bg-elevated animate-shimmer" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <p className="text-caption text-gray-500 text-center py-6">
        Nenhum histórico disponível.
      </p>
    )
  }

  return (
    <ul className={cn('divide-y divide-border', className)}>
      {items.map((item) => {
        const agent = AGENT_MAP[item.agentSlug]
        return (
          <li
            key={item.id}
            className="flex items-start gap-3 px-4 py-3"
          >
            {agent && (
              <AgentBadge
                shape={agent.shape}
                color={agent.color}
                glowColor={agent.glowColor}
                size={20}
                status="offline"
              />
            )}
            <div className="flex-1 min-w-0">
              <p className="text-body-sm text-gray-200 truncate">{item.title}</p>
              <p className={cn('text-caption-sm mt-0.5', actionColor[item.action])}>
                {actionLabel[item.action]}
              </p>
            </div>
            <span className="text-caption-sm text-gray-500 shrink-0">
              {relativeTime(item.timestamp)}
            </span>
          </li>
        )
      })}
    </ul>
  )
}
