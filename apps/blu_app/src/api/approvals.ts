import { supabase } from './client'
import type { ApprovalRequest } from '@/types/approval'

export async function fetchPendingApprovals(clientId: string): Promise<ApprovalRequest[]> {
  const { data, error } = await supabase
    .from('approval_requests')
    .select('*')
    .eq('client_id', clientId)
    .eq('status', 'pending')
    .or('snooze_until.is.null,snooze_until.lt.now()')
    .order('priority', { ascending: false }) // urgent first
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

export async function approveRequest(
  id: string,
  clientId: string
): Promise<void> {
  const { error } = await supabase
    .from('approval_requests')
    .update({ status: 'approved', updated_at: new Date().toISOString() })
    .eq('id', id)
    .eq('client_id', clientId)

  if (error) throw error
}

export async function rejectRequest(
  id: string,
  clientId: string
): Promise<void> {
  const { error } = await supabase
    .from('approval_requests')
    .update({ status: 'rejected', updated_at: new Date().toISOString() })
    .eq('id', id)
    .eq('client_id', clientId)

  if (error) throw error
}

// snooze_count incremented server-side via DB trigger
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
