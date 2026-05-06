import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, X } from 'lucide-react'
import { cn } from '@/utils/cn'
import { useNotificationContext } from '@/hooks/useNotificationContext'
import { useMarkNotificationsRead } from '@/hooks/useNotification'
import { AGENT_MAP } from '@/utils/constants'
import type { Notification } from '@/types/notification'

function formatRelativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 1) return 'Agora'
  if (mins < 60) return `Há ${mins} min`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `Há ${hrs}h`
  return `Há ${Math.floor(hrs / 24)}d`
}

function urgencyDot(urgency: Notification['urgency_level']) {
  const map: Record<string, string> = {
    critical: 'bg-urgent animate-orb-attention',
    high: 'bg-urgent',
    normal: 'bg-blu-500',
    low: 'bg-gray-400',
  }
  return map[urgency] ?? 'bg-gray-400'
}

function agentRouteFromSlug(slug: string | null): string {
  if (!slug) return '/'
  return AGENT_MAP[slug]?.route ?? '/'
}

interface NotificationDropdownProps {
  onClose: () => void
}

export function NotificationDropdown({ onClose }: NotificationDropdownProps) {
  const { notifications } = useNotificationContext()
  const markRead = useMarkNotificationsRead()
  const navigate = useNavigate()

  // Mark all unread as read when dropdown opens
  useEffect(() => {
    const unreadIds = notifications.filter((n) => !n.read_at).map((n) => n.id)
    if (unreadIds.length > 0) {
      markRead.mutate(unreadIds)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleItemClick = (n: Notification) => {
    onClose()
    if (n.agent_slug) {
      navigate(agentRouteFromSlug(n.agent_slug))
    }
  }

  return (
    <div
      className={cn(
        'absolute right-0 top-full mt-2 w-80 max-h-96 overflow-y-auto',
        'bg-surface border border-border rounded-md shadow-xl z-dropdown',
        'animate-slide-up scroll-container'
      )}
      role="menu"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border sticky top-0 bg-surface z-10">
        <div className="flex items-center gap-2 text-white">
          <Bell size={14} strokeWidth={1.5} />
          <span className="text-body-sm font-medium">Notificações</span>
        </div>
        <button
          onClick={onClose}
          aria-label="Fechar"
          className="text-gray-400 hover:text-white cursor-pointer transition-colors duration-fast"
        >
          <X size={14} />
        </button>
      </div>

      {/* List */}
      {notifications.length === 0 ? (
        <div className="flex flex-col items-center py-8 text-gray-400">
          <Bell size={24} strokeWidth={1} className="mb-2 opacity-40" />
          <p className="text-body-sm">Nenhuma notificação</p>
        </div>
      ) : (
        <ul>
          {notifications.map((n) => (
            <li key={n.id}>
              <button
                onClick={() => handleItemClick(n)}
                className={cn(
                  'w-full text-left px-4 py-3 flex items-start gap-3',
                  'hover:bg-elevated transition-colors duration-fast cursor-pointer',
                  'border-b border-border/50 last:border-0',
                  !n.read_at && 'bg-elevated/30'
                )}
                role="menuitem"
              >
                {/* Urgency dot */}
                <span
                  className={cn(
                    'w-2 h-2 rounded-full mt-1.5 shrink-0',
                    urgencyDot(n.urgency_level)
                  )}
                />

                <div className="flex-1 min-w-0">
                  <p className={cn('text-body-sm', n.read_at ? 'text-gray-300' : 'text-white')}>
                    {n.title}
                  </p>
                  {n.body && (
                    <p className="text-caption text-gray-400 line-clamp-2 mt-0.5">
                      {n.body}
                    </p>
                  )}
                  <p className="text-caption-sm text-gray-500 mt-1">
                    {formatRelativeTime(n.created_at)}
                  </p>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
