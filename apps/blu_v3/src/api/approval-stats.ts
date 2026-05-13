import { supabase } from '@blu/auth'

export interface ApprovalStats {
  id: string
  client_id: string
  total_approved: number
  total_rejected: number
  total_snoozed: number
  trust_level: 'manual' | 'similar_toggle' | 'rules' | 'full_config'
  updated_at: string
}

export async function fetchApprovalStats(clientId: string): Promise<ApprovalStats | null> {
  const { data, error } = await supabase
    .from('client_approval_stats')
    .select('*')
    .eq('client_id', clientId)
    .maybeSingle()

  if (error) throw error
  return data ?? null
}
