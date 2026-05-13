import { supabase } from '@blu/auth'

export interface Notification {
  id: string
  client_id: string
  user_id: string | null
  kind: string
  title: string
  body: string | null
  severity: 'info' | 'warning' | 'error' | string
  read: boolean
  dismissed: boolean
  target_route: string | null
  metadata: Record<string, unknown> | null
  created_at: string
  read_at: string | null
}

export interface NotificationPreferences {
  client_id: string
  channel_email: boolean
  channel_push: boolean
  channel_whatsapp: boolean
  kinds_enabled: string[]
  updated_at: string
}

export async function fetchNotifications(clientId: string, limit = 50): Promise<Notification[]> {
  const { data, error } = await supabase
    .from('notifications')
    .select('*')
    .eq('client_id', clientId)
    .eq('dismissed', false)
    .order('created_at', { ascending: false })
    .limit(limit)

  if (error) throw new Error(error.message)
  return (data ?? []) as Notification[]
}

export async function markRead(ids: string[], clientId: string): Promise<void> {
  const { error } = await supabase
    .from('notifications')
    .update({ read: true, read_at: new Date().toISOString() })
    .in('id', ids)
    .eq('client_id', clientId)

  if (error) throw new Error(error.message)
}

export async function dismiss(id: string, clientId: string): Promise<void> {
  const { error } = await supabase
    .from('notifications')
    .update({ dismissed: true })
    .eq('id', id)
    .eq('client_id', clientId)

  if (error) throw new Error(error.message)
}

export async function fetchPreferences(clientId: string): Promise<NotificationPreferences | null> {
  const { data, error } = await supabase
    .from('client_notification_preferences')
    .select('*')
    .eq('client_id', clientId)
    .maybeSingle()

  if (error) throw new Error(error.message)
  return (data ?? null) as NotificationPreferences | null
}

export async function savePreferences(
  clientId: string,
  prefs: Partial<Omit<NotificationPreferences, 'client_id' | 'updated_at'>>,
): Promise<NotificationPreferences> {
  const { data, error } = await supabase
    .from('client_notification_preferences')
    .upsert({ client_id: clientId, ...prefs, updated_at: new Date().toISOString() })
    .select()
    .single()

  if (error) throw new Error(error.message)
  return data as NotificationPreferences
}
