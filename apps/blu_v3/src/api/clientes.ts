import { supabase } from './client'

export type CustomerCluster = 'Alto' | 'Médio' | 'Baixo'

export interface CustomerSegment {
  cluster: CustomerCluster
  count: number
  avg_ticket: number | null
  revenue_share: number | null
}

export interface CustomerRecord {
  id: string
  name: string
  cluster: CustomerCluster | null
  total_purchases: number
  last_purchase_at: string | null
  avg_ticket: number | null
}

export interface CustomerTransaction {
  id: string
  customer_id: string
  customer_name: string
  description: string
  amount: number
  date: string
  status: 'completed' | 'pending' | 'cancelled'
}

export interface ClientesHistoryItem {
  id: string
  title: string
  action: 'approved' | 'rejected'
  created_at: string
  outcome_summary: string | null
}

export async function fetchCustomerSegments(clientId: string): Promise<CustomerSegment[]> {
  const { data, error } = await supabase
    .rpc('get_customer_segments', { p_client_id: clientId })

  if (error) {
    console.warn('fetchCustomerSegments:', error.message)
    return [
      { cluster: 'Alto', count: 0, avg_ticket: null, revenue_share: null },
      { cluster: 'Médio', count: 0, avg_ticket: null, revenue_share: null },
      { cluster: 'Baixo', count: 0, avg_ticket: null, revenue_share: null },
    ]
  }

  if (!data || (Array.isArray(data) && data.length === 0)) {
    return [
      { cluster: 'Alto', count: 0, avg_ticket: null, revenue_share: null },
      { cluster: 'Médio', count: 0, avg_ticket: null, revenue_share: null },
      { cluster: 'Baixo', count: 0, avg_ticket: null, revenue_share: null },
    ]
  }

  return (data ?? []).map((row: Record<string, unknown>) => ({
    cluster: row.nivel_cluster as CustomerCluster,
    count: Number(row.count ?? 0),
    avg_ticket: typeof row.avg_ticket === 'number' ? row.avg_ticket : null,
    revenue_share: typeof row.revenue_share === 'number' ? row.revenue_share : null,
  }))
}

export async function fetchTopCustomers(clientId: string): Promise<CustomerRecord[]> {
  const { data, error } = await supabase
    .rpc('get_top_customers', { p_client_id: clientId, p_limit: 20 })

  if (error) {
    console.warn('fetchTopCustomers:', error.message)
    return []
  }

  return (data ?? []).map((row: Record<string, unknown>) => ({
    id: String(row.client_id ?? row.id ?? ''),
    name: String(row.nome ?? row.name ?? 'Cliente'),
    cluster: (row.nivel_cluster as CustomerCluster) ?? null,
    total_purchases: Number(row.total_purchases ?? 0),
    last_purchase_at: row.last_purchase_at ? String(row.last_purchase_at) : null,
    avg_ticket: typeof row.avg_ticket === 'number' ? row.avg_ticket : null,
  }))
}

export async function fetchRecentTransactions(clientId: string): Promise<CustomerTransaction[]> {
  const { data, error } = await supabase
    .rpc('get_recent_transactions', { p_client_id: clientId, p_limit: 20 })

  if (error) {
    console.warn('fetchRecentTransactions:', error.message)
    return []
  }

  return (data ?? []).map((row: Record<string, unknown>) => ({
    id: String(row.id ?? ''),
    customer_id: String(row.client_id ?? ''),
    customer_name: String(row.nome ?? 'Cliente'),
    description: String(row.descricao ?? row.description ?? 'Transação'),
    amount: Number(row.valor ?? row.amount ?? 0),
    date: String(row.data ?? row.date ?? new Date().toISOString()),
    status: (row.status ?? 'completed') as CustomerTransaction['status'],
  }))
}

export async function fetchClientesHistory(clientId: string): Promise<ClientesHistoryItem[]> {
  const { data, error } = await supabase
    .from('approval_requests')
    .select('id, title, status, created_at, payload')
    .eq('client_id', clientId)
    .eq('agent_slug', 'clientes')
    .in('status', ['approved', 'rejected'])
    .order('created_at', { ascending: false })
    .limit(15)

  if (error) throw error

  return (data ?? []).map((row) => {
    const meta = (row.payload ?? {}) as Record<string, unknown>
    return {
      id: row.id,
      title: row.title,
      action: row.status as 'approved' | 'rejected',
      created_at: row.created_at,
      outcome_summary: typeof meta.outcome_summary === 'string' ? meta.outcome_summary : null,
    }
  })
}
