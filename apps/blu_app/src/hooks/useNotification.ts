import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/hooks/useAuth'
import {
  fetchNotifications,
  markNotificationsRead,
  dismissNotification,
} from '@/api/notifications'
import { QUERY_KEYS } from '@/utils/constants'

export function useNotifications() {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: QUERY_KEYS.notifications(clientId ?? ''),
    queryFn: () => fetchNotifications(clientId!),
    enabled: !!clientId,
  })
}

export function useMarkNotificationsRead() {
  const { clientId } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (ids: string[]) => markNotificationsRead(ids, clientId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notifications', clientId] })
    },
  })
}

export function useDismissNotification() {
  const { clientId } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => dismissNotification(id, clientId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notifications', clientId] })
    },
  })
}
