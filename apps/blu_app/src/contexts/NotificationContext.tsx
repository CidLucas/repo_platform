import {
  createContext,
  useMemo,
  type ReactNode,
} from 'react'
import { useNotifications } from '@/hooks/useNotification'
import type { Notification } from '@/types/notification'

interface NotificationContextValue {
  notifications: Notification[]
  unreadCount: number
  criticalCount: number
  isLoading: boolean
}

export const NotificationContext = createContext<NotificationContextValue | null>(null)
export type { NotificationContextValue }

export function NotificationProvider({ children }: { children: ReactNode }) {
  const { data: notifications = [], isLoading } = useNotifications()

  const { unreadCount, criticalCount } = useMemo(() => {
    const unread = notifications.filter((n) => !n.read_at)
    const critical = unread.filter((n) => n.urgency_level === 'critical')
    return { unreadCount: unread.length, criticalCount: critical.length }
  }, [notifications])

  return (
    <NotificationContext.Provider
      value={{ notifications, unreadCount, criticalCount, isLoading }}
    >
      {children}
    </NotificationContext.Provider>
  )
}

