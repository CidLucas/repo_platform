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

export async function createPaymentApproval(
  clientId: string,
  bill: { id: string; polp_account_id: number; due_date: string; total_amount: number },
  cardName: string
): Promise<void> {
  const fmtBRL = (v: number) => v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
  const fmtDate = (s: string) => new Date(s + 'T00:00:00').toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' })
  const { error } = await supabase
    .from('approval_requests')
    .insert({
      client_id: clientId,
      agent_slug: 'financeiro',
      action_type: 'pay_bill',
      title: `Pagar fatura ${cardName} — ${fmtBRL(bill.total_amount)}`,
      body: `Vencimento ${fmtDate(bill.due_date)} · Total ${fmtBRL(bill.total_amount)}`,
      priority: 'high',
      status: 'pending',
      metadata: {
        bill_id: bill.id,
        polp_account_id: bill.polp_account_id,
        amount: bill.total_amount,
        due_date: bill.due_date,
      },
    })
  if (error) throw error
}
