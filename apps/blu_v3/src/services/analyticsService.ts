import { supabase } from '../api/client'

const ANALYTICS_SCHEMA = 'analytics_v2'

export type StandardPeriod = '7d' | '30d' | '90d' | 'mtd' | 'ytd' | 'custom'

export interface AgendaEvent {
  id: string
  title: string
  startsAt: string
  endsAt: string
  type: 'meeting' | 'call' | 'deadline'
  location: string | null
  attendeesCount: number
  hangoutLink: string | null
}

export interface AgendaResponse {
  events: AgendaEvent[]
  disabled: boolean
  reason?: string
  fetchedAt: string | null
  rangeDays: number
}

export interface FinanceIndicators {
  receita_liquida: number
  custo_total: number
  margem_bruta_perc: number | null
  margem_operacional_perc: number | null
  ticket_medio: number
  receita_yoy_perc: number | null
  crescimento_receita_perc: number | null
  total_pedidos: number
  dso_dias: number | null
  dpo_dias: number | null
  ccc_dias: number | null
  working_capital_ratio: number | null
  burn_rate_mensal: number | null
  runway_meses: number | null
  cash_flow_30d: number | null
  period: string
}

const num = (v: unknown): number => {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}
const numOrNull = (v: unknown): number | null => {
  if (v === null || v === undefined) return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

async function callDimensionRpc<T>(rpc: string, period: string): Promise<T> {
  const { data, error } = await supabase.schema(ANALYTICS_SCHEMA).rpc(rpc, { p_period: period })
  if (error) throw new Error(`${rpc}: ${error.message}`)
  return (Array.isArray(data) ? data[0] : data) as T
}

export const getFinanceIndicators = async (
  period: StandardPeriod | string = '30d'
): Promise<FinanceIndicators> => {
  const r = await callDimensionRpc<Record<string, unknown>>('get_finance_indicators', period)
  return {
    receita_liquida:          num(r?.receita_liquida),
    custo_total:              num(r?.custo_total),
    margem_bruta_perc:        numOrNull(r?.margem_bruta_perc),
    margem_operacional_perc:  numOrNull(r?.margem_operacional_perc),
    ticket_medio:             num(r?.ticket_medio),
    receita_yoy_perc:         numOrNull(r?.receita_yoy_perc),
    crescimento_receita_perc: numOrNull(r?.crescimento_receita_perc),
    total_pedidos:            num(r?.total_pedidos),
    dso_dias:                 numOrNull(r?.dso_dias),
    dpo_dias:                 numOrNull(r?.dpo_dias),
    ccc_dias:                 numOrNull(r?.ccc_dias),
    working_capital_ratio:    numOrNull(r?.working_capital_ratio),
    burn_rate_mensal:         numOrNull(r?.burn_rate_mensal),
    runway_meses:             numOrNull(r?.runway_meses),
    cash_flow_30d:            numOrNull(r?.cash_flow_30d),
    period:                   String(r?.period ?? period),
  }
}

export interface CustomerMetrics {
  total_clientes: number
  crescimento_clientes: number // net-new clients this year
}

export const getCustomerMetrics = async (clientId: string): Promise<CustomerMetrics> => {
  const { data, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .rpc('get_annual_metrics_for_client', { p_client_id: clientId })
  if (error) throw new Error(`get_annual_metrics_for_client: ${error.message}`)

  const rows = (Array.isArray(data) ? data : []) as Array<{
    ano: number
    clientes_unicos: number
    clientes_novos: number
  }>
  const currentYear = new Date().getFullYear()
  const current = rows.find(r => r.ano === currentYear)
  return {
    total_clientes: num(current?.clientes_unicos),
    crescimento_clientes: num(current?.clientes_novos),
  }
}

export const getAgendaEvents = async (rangeDays = 7): Promise<AgendaResponse> => {
  const { data, error } = await supabase.functions.invoke('google-calendar-events', {
    body: { rangeDays },
  })

  if (error) {
    return { events: [], disabled: true, reason: 'function_error', fetchedAt: null, rangeDays }
  }

  const payload = (data ?? {}) as {
    events?: Array<{
      id: string
      title: string
      starts_at: string
      ends_at: string
      type: string
      location: string | null
      attendees_count: number
      hangout_link: string | null
    }>
    disabled?: boolean
    reason?: string
    fetched_at?: string
    range_days?: number
  }

  return {
    events: (payload.events ?? []).map((ev) => ({
      id: ev.id,
      title: ev.title,
      startsAt: ev.starts_at,
      endsAt: ev.ends_at,
      type: (ev.type as AgendaEvent['type']) ?? 'meeting',
      location: ev.location,
      attendeesCount: Number(ev.attendees_count) || 0,
      hangoutLink: ev.hangout_link,
    })),
    disabled: Boolean(payload.disabled),
    reason: payload.reason,
    fetchedAt: payload.fetched_at ?? null,
    rangeDays: Number(payload.range_days ?? rangeDays),
  }
}
