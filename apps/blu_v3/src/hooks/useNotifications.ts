import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@blu/auth'
import {
  fetchNotifications,
  markRead,
  dismiss,
  fetchPreferences,
  savePreferences,
  type NotificationPreferences,
} from '../api/notifications'

export function useNotifications(limit = 50) {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['notifications', clientId, limit],
    queryFn: () => fetchNotifications(clientId!, limit),
    enabled: !!clientId,
    staleTime: 30 * 1000,
  })
}

export function useMarkRead() {
  const { clientId } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (ids: string[]) => markRead(ids, clientId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notifications', clientId] })
    },
  })
}

export function useDismissNotification() {
  const { clientId } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => dismiss(id, clientId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notifications', clientId] })
    },
  })
}

export function useNotificationPreferences() {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['notificationPreferences', clientId],
    queryFn: () => fetchPreferences(clientId!),
    enabled: !!clientId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useSaveNotificationPreferences() {
  const { clientId } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (prefs: Partial<Omit<NotificationPreferences, 'client_id' | 'updated_at'>>) =>
      savePreferences(clientId!, prefs),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notificationPreferences', clientId] })
    },
  })
}
