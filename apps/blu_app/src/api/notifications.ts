import { supabase } from './client'
import type { Notification } from '@/types/notification'

export async function fetchNotifications(clientId: string): Promise<Notification[]> {
  const { data, error } = await supabase
    .from('notifications')
    .select('*')
    .eq('client_id', clientId)
    .is('dismissed_at', null)
    .order('created_at', { ascending: false })
    .limit(30)

  if (error) throw error
  return data ?? []
}

export async function markNotificationsRead(
  ids: string[],
  clientId: string
): Promise<void> {
  if (ids.length === 0) return
  const { error } = await supabase
    .from('notifications')
    .update({ read_at: new Date().toISOString() })
    .in('id', ids)
    .eq('client_id', clientId)
    .is('read_at', null)

  if (error) throw error
}

export async function dismissNotification(
  id: string,
  clientId: string
): Promise<void> {
  const { error } = await supabase
    .from('notifications')
    .update({ dismissed_at: new Date().toISOString() })
    .eq('id', id)
    .eq('client_id', clientId)

  if (error) throw error
}
