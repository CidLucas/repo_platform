export type KpiPeriod = '7d' | '30d' | '90d' | '1y'

export interface KpiMetrics {
  faturamento?: number
  despesas?: number
  margem?: number
  pedidos?: number
  clientes_ativos?: number
  ticket_medio?: number
  fornecedores?: number
  produtos?: number
  faturamento_trend?: number
  despesas_trend?: number
  margem_trend?: number
  pedidos_delta?: number
  clientes_delta?: number
  [key: string]: number | undefined
}

export interface ClientKpiSnapshot {
  id: string
  client_id: string
  period: KpiPeriod
  metrics: KpiMetrics
  generated_at: string
}

export interface ApprovalStats {
  client_id: string
  total_approved: number
  total_rejected: number
  total_snoozed: number
  trust_level: 'basic' | 'similar_toggle' | 'rules' | 'full_config'
  updated_at: string
}

/** One point in a time series (from analytics_v2.v_series_temporal) */
export interface TimeSeriesPoint {
  date: string
  receita?: number
  despesas?: number
  entrada?: number
  saida?: number
  [key: string]: string | number | undefined
}

/** Activity entry from public.get_recent_activity RPC */
export interface ActivityEntry {
  id: string
  kind: string
  title: string
  subtitle: string | null
  occurredAt: string
  severity: string
}
