import { supabase } from './client'

// ─── KPI label formatter ──────────────────────────────────────────────────────

const KPI_LABELS: Record<string, string> = {
  // Finance
  receita_liquida: 'Receita Líquida',
  receita_bruta: 'Receita Bruta',
  margem_bruta: 'Margem Bruta',
  margem_liquida: 'Margem Líquida',
  crescimento_receita_perc: 'Crescimento de Receita',
  lucro_liquido: 'Lucro Líquido',
  ebitda: 'EBITDA',
  cac: 'Custo de Aquisição',
  churn_rate: 'Taxa de Churn',
  inadimplencia: 'Inadimplência',
  fluxo_caixa: 'Fluxo de Caixa',
  ticket_medio: 'Ticket Médio',
  // Supply / Inventory
  stockout_rate_perc: 'Taxa de Ruptura',
  giro_estoque: 'Giro de Estoque',
  prazo_reposicao: 'Prazo de Reposição',
  cobertura_estoque: 'Cobertura de Estoque',
  pedidos_atrasados: 'Pedidos Atrasados',
  nivel_servico: 'Nível de Serviço',
  // Commercial / Clients
  clientes_ativos: 'Clientes Ativos',
  novos_clientes: 'Novos Clientes',
  clientes_inativos: 'Clientes Inativos',
  retencao: 'Retenção',
  nps: 'NPS',
  taxa_conversao: 'Taxa de Conversão',
  // Strategy
  roi: 'ROI',
  payback: 'Payback',
  market_share: 'Market Share',
}

/** Convert a raw KPI slug to a human-readable Portuguese label. */
export function formatKpi(kpi: string | null | undefined): string {
  if (!kpi) return 'Insight'
  if (KPI_LABELS[kpi]) return KPI_LABELS[kpi]
  // Fallback: snake_case → Title Case
  return kpi
    .replace(/_perc$/, ' %')
    .split('_')
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

export type InsightRoom = 'financeiro' | 'clientes' | 'compras' | 'agenda' | 'estrategia' | 'home'

export interface ClientInsight {
  id: string
  room: string | null
  kpi: string | null
  severity: string
  title: string
  observation: string
  recommendation: string | null
  status: string
  createdAt: string
}

export async function fetchInsights(limit = 5, room?: InsightRoom): Promise<ClientInsight[]> {
  const { data, error } = await supabase.rpc('get_my_insights', {
    p_limit: limit,
    p_status: 'active',
    ...(room ? { p_room: room } : {}),
  })

  if (error) {
    if (error.code === '42883') return [] // RPC not deployed yet
    throw error
  }

  return ((data ?? []) as Array<Record<string, unknown>>).map((row) => ({
    id: String(row.id),
    room: (row.room as string) ?? null,
    kpi: (row.kpi as string) ?? null,
    severity: String(row.severity ?? 'low'),
    title: String(row.title),
    observation: String(row.observation),
    recommendation: (row.recommendation as string) ?? null,
    status: String(row.status),
    createdAt: String(row.created_at),
  }))
}

export async function dismissInsight(id: string): Promise<void> {
  const { error } = await supabase.rpc('dismiss_insight', { p_insight_id: id })
  if (error) throw error
}
