import { supabase } from './client'

export interface ApprovalRule {
  id: string
  client_id: string
  agent_slug: string
  rule_type: string
  condition: Record<string, unknown>
  action: string
  enabled: boolean
  created_at: string
}

export async function fetchApprovalRules(clientId: string): Promise<ApprovalRule[]> {
  const { data, error } = await supabase
    .from('client_approval_rules')
    .select('*')
    .eq('client_id', clientId)
    .order('created_at')

  if (error) throw error
  return data ?? []
}

export async function createApprovalRule(
  rule: Omit<ApprovalRule, 'id' | 'created_at'>
): Promise<ApprovalRule> {
  const { data, error } = await supabase
    .from('client_approval_rules')
    .insert(rule)
    .select()
    .single()

  if (error) throw error
  return data
}

export async function deleteApprovalRule(id: string, clientId: string): Promise<void> {
  const { error } = await supabase
    .from('client_approval_rules')
    .delete()
    .eq('id', id)
    .eq('client_id', clientId)

  if (error) throw error
}
