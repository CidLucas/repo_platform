import { cn } from '@/utils/cn'
import { useRecentActivity } from '@/hooks/useAnalytics'
import { AgentBadge } from '@/components/navigation/AgentBadge'
import { SkeletonCard } from '@/components/primitives/SkeletonCard'
import { relativeTime } from '@/utils/format'
import { AGENT_MAP } from '@/utils/constants'

interface ActivityFeedProps {
  className?: string
}

export function ActivityFeed({ className }: ActivityFeedProps) {
  const { data: entries, isLoading } = useRecentActivity(20)

  if (isLoading) {
    return (
      <div className={cn('space-y-2', className)}>
        {Array.from({ length: 5 }).map((_, i) => (
          <SkeletonCard key={i} lines={2} />
        ))}
      </div>
    )
  }

  if (!entries?.length) {
    return (
      <p className={cn('text-caption text-gray-500 text-center py-4', className)}>
        Nenhuma atividade recente
      </p>
    )
  }

  return (
    <ul className={cn('divide-y divide-border', className)}>
      {entries.map((entry) => {
        const agent = AGENT_MAP[entry.kind]

        return (
          <li
            key={entry.id}
            className="flex items-center gap-3 py-3 px-1 rounded hover:bg-elevated/40 transition-colors duration-normal"
          >
            {agent ? (
              <AgentBadge
                shape={agent.shape}
                color={agent.color}
                glowColor={agent.glowColor}
                size={20}
                status="idle"
              />
            ) : (
              <span className="w-5 h-5 rounded-full bg-gray-700 shrink-0" />
            )}
            <div className="flex-1 min-w-0">
              <p className="text-body-sm text-gray-200 truncate">{entry.title}</p>
              {entry.subtitle && (
                <p className="text-caption-sm text-gray-500 truncate">{entry.subtitle}</p>
              )}
            </div>
            <time
              dateTime={entry.occurredAt}
              className="text-caption-sm text-gray-500 shrink-0 whitespace-nowrap"
            >
              {relativeTime(entry.occurredAt)}
            </time>
          </li>
        )
      })}
    </ul>
  )
}
