import { useContext } from 'react'
import { NotificationContext, type NotificationContextValue } from '@/contexts/NotificationContext'

export function useNotificationContext(): NotificationContextValue {
  const ctx = useContext(NotificationContext)
  if (!ctx) throw new Error('useNotificationContext must be used within NotificationProvider')
  return ctx
}
