import { supabase } from './client'

export interface ConnectedAccount {
  id: string
  // Normalized from real DB columns (tipo_servico, nome_servico, connection_metadata, updated_at)
  provider: string
  account_name: string | null
  balance: number | null
  currency: string
  status: 'active' | 'error' | 'disconnected'
  last_sync_at: string | null
}

export interface ReportRun {
  id: string
  report_type: 'dre' | 'cash_flow' | 'margin' | 'custom'
  label: string
  period: string
  status: 'ready' | 'generating' | 'error'
  created_at: string
  file_url: string | null
}

export async function fetchConnectedAccounts(clientId: string): Promise<ConnectedAccount[]> {
  const { data, error } = await supabase
    .from('credencial_servico_externo')
    .select('id, tipo_servico, nome_servico, status, ativo, connection_metadata, updated_at')
    .eq('client_id', clientId)
    .order('tipo_servico')

  if (error) throw error
  return (data ?? []).map((row) => {
    const meta = (row.connection_metadata ?? {}) as Record<string, unknown>
    const rawStatus = row.status as string | null
    const ativo = row.ativo as boolean | null
    let status: ConnectedAccount['status'] = 'disconnected'
    if (rawStatus === 'error') status = 'error'
    else if (rawStatus === 'active' || ativo === true) status = 'active'
    return {
      id: row.id,
      provider: (row.tipo_servico ?? row.nome_servico ?? 'Integração') as string,
      account_name: (row.nome_servico as string | null) ?? null,
      balance: typeof meta.balance === 'number' ? meta.balance : null,
      currency: typeof meta.currency === 'string' ? meta.currency : 'BRL',
      status,
      last_sync_at: (row.updated_at as string | null) ?? null,
    }
  })
}

export async function fetchReportRuns(clientId: string): Promise<ReportRun[]> {
  const { data, error } = await supabase
    .from('report_runs')
    .select('id, report_type, label, period, status, created_at, file_url')
    .eq('client_id', clientId)
    .order('created_at', { ascending: false })
    .limit(10)

  if (error) throw error
  return (data ?? []).map((row) => ({
    id: row.id,
    report_type: row.report_type ?? 'custom',
    label: row.label ?? 'Relatório',
    period: row.period ?? '',
    status: row.status ?? 'ready',
    created_at: row.created_at,
    file_url: row.file_url ?? null,
  }))
}
