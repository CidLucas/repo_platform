import { supabase } from './client'

export interface Supplier {
  id: string
  client_id: string
  name: string
  cnpj: string | null
  category: string | null
  tags: string[] | null
  rating: number | null
  contact_phone: string | null
  contact_email: string | null
  city: string | null
  state: string | null
  performance_summary: string | null
  is_active: boolean
  // analytics fields from analytics_v2.dim_fornecedores
  receita_total: number | null
  ticket_medio: number | null
  total_pedidos_recebidos: number | null
  nivel_cluster: string | null
  dias_recencia: number | null
  frequencia_mensal: number | null
  updated_at: string
}

export interface PurchaseHistoryItem {
  id: string
  title: string
  amount: number | null
  category: string | null
  status: 'approved' | 'rejected'
  created_at: string
}

export async function fetchSuppliers(clientId: string): Promise<Supplier[]> {
  const { data, error } = await supabase
    .from('suppliers')
    .select('*')
    .eq('client_id', clientId)
    .order('name')

  if (error) throw error
  return data ?? []
}

/** Last 10 completed purchase decisions from approval_requests */
export async function fetchComprasHistory(clientId: string): Promise<PurchaseHistoryItem[]> {
  const { data, error } = await supabase
    .from('approval_requests')
    .select('id, title, payload, status, created_at')
    .eq('client_id', clientId)
    .eq('agent_slug', 'compras')
    .in('status', ['approved', 'rejected'])
    .order('created_at', { ascending: false })
    .limit(10)

  if (error) throw error

  return (data ?? []).map((row) => {
    const payload = (row.payload ?? {}) as Record<string, unknown>
    return {
      id: row.id,
      title: row.title,
      amount: typeof payload.amount === 'number' ? payload.amount : null,
      category: typeof payload.category === 'string' ? payload.category : null,
      status: row.status as 'approved' | 'rejected',
      created_at: row.created_at,
    }
  })
}
