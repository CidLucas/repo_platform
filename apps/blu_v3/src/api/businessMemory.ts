/**
 * Business Memory API — shared_business_memory data fetching
 *
 * T5.1: Frontend page for business memory visualization.
 * Uses mock data initially; toggle USE_MOCK to switch to real API.
 */

import { supabase } from '@blu/auth'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface BusinessMemoryRecord {
  id: string
  entity_type: string
  entity_name: string
  key: string
  value: Record<string, unknown> | null
  metadata: Record<string, unknown> | null
  source: string | null
  confidence: number | null
  version: number | null
  created_at: string | null
  updated_at: string | null
}

export interface BusinessMemoryListResponse {
  client_id: string
  total_records: number
  records: BusinessMemoryRecord[]
}

// ---------------------------------------------------------------------------
// Mock data — toggle USE_MOCK to switch between mock and real API
// ---------------------------------------------------------------------------

export const USE_MOCK = true

function mockRecords(): BusinessMemoryRecord[] {
  const now = new Date().toISOString()
  return [
    {
      id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
      entity_type: 'snapshot',
      entity_name: 'financeiro:semanal',
      key: '2025-06-19T10:00:00Z',
      value: {
        snapshot_id: '550e8400-e29b-41d4-a716-446655440000',
        dimensao: 'financeiro',
        periodo: 'semanal',
        gerado_em: '2025-06-19T10:00:00Z',
        vigencia_inicio: '2025-06-12T00:00:00Z',
        vigencia_fim: '2025-06-19T00:00:00Z',
        indicadores: [
          { nome: 'saldo_atual', valor: 152000, unidade: 'BRL', tendencia: 'estavel' },
          { nome: 'receita_periodo', valor: 48700, unidade: 'BRL', tendencia: 'alta' },
          { nome: 'despesa_periodo', valor: 35200, unidade: 'BRL', tendencia: 'baixa' },
          { nome: 'fluxo_liquido', valor: 13500, unidade: 'BRL', tendencia: 'alta' },
        ],
        alertas: [],
        resumo_executivo:
          'Semana positiva com fluxo líquido de BRL 13.500. Receita em alta e despesas controladas.',
      },
      metadata: {
        tipo: 'snapshot',
        dimensao: 'financeiro',
        periodo: 'semanal',
        gerado_em: '2025-06-19T10:00:00Z',
        gerado_por: 'financeiro_agent',
        versao: 1,
        template_version: 1,
        fontes: ['get_cash_position v2', 'get_recent_transactions v1'],
        confianca: 0.95,
      },
      source: 'specialist',
      confidence: 0.95,
      version: 1,
      created_at: now,
      updated_at: now,
    },
    {
      id: 'b2c3d4e5-f6a7-8901-bcde-f12345678901',
      entity_type: 'snapshot',
      entity_name: 'clientes:mensal',
      key: '2025-06-01T08:00:00Z',
      value: {
        snapshot_id: '660f9511-e39c-52e5-b827-557766551111',
        dimensao: 'clientes',
        periodo: 'mensal',
        gerado_em: '2025-06-01T08:00:00Z',
        vigencia_inicio: '2025-05-01T00:00:00Z',
        vigencia_fim: '2025-06-01T00:00:00Z',
        indicadores: [
          { nome: 'total_clientes_ativos', valor: 1240, unidade: 'count', tendencia: 'alta' },
          { nome: 'novos_clientes_periodo', valor: 87, unidade: 'count', tendencia: 'alta' },
          { nome: 'churn_periodo', valor: 12, unidade: 'count', tendencia: 'baixa' },
        ],
        alertas: [],
        resumo_executivo:
          'Base de clientes cresceu 7% no mês. 87 novos clientes, churn de apenas 1%.',
      },
      metadata: {
        tipo: 'snapshot',
        dimensao: 'clientes',
        periodo: 'mensal',
        gerado_em: '2025-06-01T08:00:00Z',
        gerado_por: 'clientes_agent',
        versao: 1,
        template_version: 1,
        fontes: ['get_active_clients v1', 'get_churn_metrics v1'],
        confianca: 0.92,
      },
      source: 'specialist',
      confidence: 0.92,
      version: 1,
      created_at: '2025-06-01T08:00:00Z',
      updated_at: '2025-06-01T08:00:00Z',
    },
    {
      id: 'c3d4e5f6-a7b8-9012-cdef-123456789012',
      entity_type: 'snapshot',
      entity_name: 'agenda:diario',
      key: '2025-06-19T07:00:00Z',
      value: {
        snapshot_id: '7700a622-f4ad-63f6-c938-668877662222',
        dimensao: 'agenda',
        periodo: 'diario',
        gerado_em: '2025-06-19T07:00:00Z',
        vigencia_inicio: '2025-06-19T00:00:00Z',
        vigencia_fim: '2025-06-19T23:59:59Z',
        indicadores: [
          { nome: 'reunioes_hoje', valor: 5, unidade: 'count', tendencia: 'estavel' },
          { nome: 'reunioes_semana', valor: 23, unidade: 'count', tendencia: 'estavel' },
          { nome: 'followups_pendentes', valor: 3, unidade: 'count', tendencia: 'baixa' },
        ],
        alertas: ['followups_pendentes: 3 aguardando retorno'],
        resumo_executivo:
          'Dia com 5 reuniões agendadas. 3 follow-ups pendentes de retorno do cliente.',
      },
      metadata: {
        tipo: 'snapshot',
        dimensao: 'agenda',
        periodo: 'diario',
        gerado_em: '2025-06-19T07:00:00Z',
        gerado_por: 'agenda_agent',
        versao: 1,
        template_version: 1,
        fontes: ['get_today_meetings v1', 'get_weekly_meetings v1'],
        confianca: 1.0,
      },
      source: 'specialist',
      confidence: 1.0,
      version: 1,
      created_at: '2025-06-19T07:00:00Z',
      updated_at: '2025-06-19T07:00:00Z',
    },
    {
      id: 'd4e5f6a7-b8c9-0123-defa-234567890123',
      entity_type: 'snapshot',
      entity_name: 'compras:semanal',
      key: '2025-06-18T18:00:00Z',
      value: {
        snapshot_id: '8800b733-a5be-74f7-d049-779988773333',
        dimensao: 'compras',
        periodo: 'semanal',
        gerado_em: '2025-06-18T18:00:00Z',
        vigencia_inicio: '2025-06-12T00:00:00Z',
        vigencia_fim: '2025-06-19T00:00:00Z',
        indicadores: [
          { nome: 'total_pos_abertas', valor: 14, unidade: 'count', tendencia: 'alta' },
          { nome: 'estoque_critico', valor: 3, unidade: 'count', tendencia: 'alta' },
          { nome: 'fornecedores_com_pendencia', valor: 2, unidade: 'count', tendencia: 'estavel' },
        ],
        alertas: ['estoque_critico: 3 itens abaixo do mínimo'],
        resumo_executivo:
          '14 pedidos de compra abertos. 3 itens em estoque crítico exigem atenção imediata.',
      },
      metadata: {
        tipo: 'snapshot',
        dimensao: 'compras',
        periodo: 'semanal',
        gerado_em: '2025-06-18T18:00:00Z',
        gerado_por: 'compras_agent',
        versao: 1,
        template_version: 1,
        fontes: ['get_open_purchase_orders v1', 'get_critical_stock v1'],
        confianca: 0.88,
      },
      source: 'specialist',
      confidence: 0.88,
      version: 1,
      created_at: '2025-06-18T18:00:00Z',
      updated_at: '2025-06-18T18:00:00Z',
    },
    {
      id: 'e5f6a7b8-c9d0-1234-efab-345678901234',
      entity_type: 'routine',
      entity_name: 'relatorio_diario',
      key: 'daily-report',
      value: {
        status: 'active',
        schedule: '0 8 * * *',
        last_run: '2025-06-19T08:00:00Z',
        next_run: '2025-06-20T08:00:00Z',
      },
      metadata: {
        tipo: 'routine_result',
        gerado_por: 'report_agent',
        versao: 3,
      },
      source: 'routine',
      confidence: 1.0,
      version: 3,
      created_at: '2025-04-01T00:00:00Z',
      updated_at: '2025-06-19T08:00:00Z',
    },
  ]
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function fetchBusinessMemory(
  entityType?: string,
  entityName?: string,
  limit = 100,
  offset = 0
): Promise<BusinessMemoryListResponse> {
  if (USE_MOCK) {
    // Simulate network delay
    await new Promise((r) => setTimeout(r, 600))

    let records = mockRecords()

    if (entityType) {
      records = records.filter((r) => r.entity_type === entityType)
    }
    if (entityName) {
      const lower = entityName.toLowerCase()
      records = records.filter((r) => r.entity_name.toLowerCase().startsWith(lower))
    }

    const total = records.length
    records = records.slice(offset, offset + limit)

    return {
      client_id: 'mock-client-id',
      total_records: total,
      records,
    }
  }

  // Real API call via Supabase RPC or HTTP endpoint
  const { data, error } = await supabase.functions.invoke('business-memory', {
    body: { entity_type: entityType, entity_name: entityName, limit, offset },
  })

  if (error) throw new Error(`Failed to fetch business memory: ${error.message}`)

  // If the backend returns snake_case keys, map to camelCase
  const payload = (data ?? {}) as {
    client_id?: string
    total_records?: number
    records?: Array<{
      id: string
      entity_type: string
      entity_name: string
      key: string
      value?: Record<string, unknown> | null
      metadata?: Record<string, unknown> | null
      source?: string | null
      confidence?: number | null
      version?: number | null
      created_at?: string | null
      updated_at?: string | null
    }>
  }

  return {
    client_id: payload.client_id ?? '',
    total_records: payload.total_records ?? 0,
    records: (payload.records ?? []).map((r) => ({
      id: r.id,
      entity_type: r.entity_type,
      entity_name: r.entity_name,
      key: r.key,
      value: r.value ?? null,
      metadata: r.metadata ?? null,
      source: r.source ?? null,
      confidence: r.confidence ?? null,
      version: r.version ?? null,
      created_at: r.created_at ?? null,
      updated_at: r.updated_at ?? null,
    })),
  }
}

export async function fetchBusinessMemoryRecord(
  recordId: string
): Promise<BusinessMemoryRecord> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 400))
    const record = mockRecords().find((r) => r.id === recordId)
    if (!record) throw new Error(`Record '${recordId}' not found`)
    return record
  }

  const { data, error } = await supabase.functions.invoke('business-memory-record', {
    body: { record_id: recordId },
  })

  if (error) throw new Error(`Failed to fetch record: ${error.message}`)

  const r = (data ?? {}) as {
    id: string
    entity_type: string
    entity_name: string
    key: string
    value?: Record<string, unknown> | null
    metadata?: Record<string, unknown> | null
    source?: string | null
    confidence?: number | null
    version?: number | null
    created_at?: string | null
    updated_at?: string | null
  }

  return {
    id: r.id,
    entity_type: r.entity_type,
    entity_name: r.entity_name,
    key: r.key,
    value: r.value ?? null,
    metadata: r.metadata ?? null,
    source: r.source ?? null,
    confidence: r.confidence ?? null,
    version: r.version ?? null,
    created_at: r.created_at ?? null,
    updated_at: r.updated_at ?? null,
  }
}
