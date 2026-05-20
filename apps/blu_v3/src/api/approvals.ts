import { supabase } from './client'

export interface ApprovalRequest {
  id: string
  client_id: string
  agent_slug: string
  action_type: string
  title: string
  body: string | null
  priority: 'urgent' | 'high' | 'medium' | 'low'
  status: 'pending' | 'approved' | 'rejected' | 'snoozed'
  snooze_until: string | null
  created_at: string
  updated_at: string
  metadata: Record<string, unknown> | null
  payload?: Record<string, unknown> | null
}

export async function fetchPendingApprovals(clientId: string): Promise<ApprovalRequest[]> {
  const { data, error } = await supabase
    .from('approval_requests')
    .select('*')
    .eq('client_id', clientId)
    .eq('status', 'pending')
    .or('snooze_until.is.null,snooze_until.lt.now()')
    .order('priority', { ascending: false })
    .order('created_at', { ascending: true })

  if (error) throw error
  return data ?? []
}

export async function fetchApprovalsByAgent(
  agentSlug: string,
  clientId: string
): Promise<ApprovalRequest[]> {
  const { data, error } = await supabase
    .from('approval_requests')
    .select('*')
    .eq('client_id', clientId)
    .eq('agent_slug', agentSlug)
    .eq('status', 'pending')
    .or('snooze_until.is.null,snooze_until.lt.now()')
    .order('priority', { ascending: false })
    .order('created_at', { ascending: true })

  if (error) throw error
  return data ?? []
}

export async function approveRequest(id: string, clientId: string): Promise<void> {
  const { error } = await supabase
    .from('approval_requests')
    .update({ status: 'approved', updated_at: new Date().toISOString() })
    .eq('id', id)
    .eq('client_id', clientId)

  if (error) throw error
}

export async function rejectRequest(id: string, clientId: string): Promise<void> {
  const { error } = await supabase
    .from('approval_requests')
    .update({ status: 'rejected', updated_at: new Date().toISOString() })
    .eq('id', id)
    .eq('client_id', clientId)

  if (error) throw error
}

export async function snoozeApproval(
  id: string,
  clientId: string,
  snoozeUntil: string
): Promise<void> {
  const { error } = await supabase
    .from('approval_requests')
    .update({ snooze_until: snoozeUntil, updated_at: new Date().toISOString() })
    .eq('id', id)
    .eq('client_id', clientId)

  if (error) throw error
}
