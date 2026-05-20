import { useState } from 'react'
import { useQueries, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAppStore } from '../../store/appStore'
import { useAuth } from '../../hooks/useAuth'
import {
  fetchApprovalsByAgent,
  approveRequest,
  rejectRequest,
  snoozeApproval,
  type ApprovalRequest,
} from '../../api/approvals'
import { fetchInsights, type ClientInsight } from '../../api/insights'
import {
  fetchCustomerSegments,
  fetchTopCustomers,
  fetchClientesHistory,
  type CustomerSegment,
  type CustomerRecord,
  type ClientesHistoryItem,
} from '../../api/clientes'
import { getCommercialIndicators, getContextMetrics, type ContextMetricRow } from '../../api/analytics'
import RColResizeHandle from '../../components/shared/RColResizeHandle'
import CollapsiblePanel from '../../components/shared/CollapsiblePanel'
import RoutineConfigSection from '../../components/shared/RoutineConfigSection'
import RoutineStatusWidget from '../../components/shared/RoutineStatusWidget'

type Tab = 'followup' | 'ativos' | 'historico' | 'config'

function snoozeUntil() {
  return new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString()
}

function relativeTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime()
  const d = Math.floor(diff / 86400000)
  if (d === 0) return 'hoje'
  if (d === 1) return 'ontem'
  return `${d}d atrás`
}

function formatBRL(value: number | null) {
  if (value === null) return '—'
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
}

export default function ClientesRoom() {
  const { go, addToast } = useAppStore()
  const { clientId } = useAuth()
  const qc = useQueryClient()
  const [tab, setTab] = useState<Tab>('followup')
  const [analyticsOpen, setAnalyticsOpen] = useState(false)
  const [analyticsPeriod, setAnalyticsPeriod] = useState<'30d' | '90d' | '1y'>('30d')

  const [approvalsQ, insightsQ, segmentsQ, customersQ, historyQ, commercialQ, contextMetricsQ] = useQueries({
    queries: [
      {
        queryKey: ['approvals', 'clientes', clientId ?? ''],
        queryFn: () => fetchApprovalsByAgent('clientes', clientId!),
        enabled: !!clientId,
        staleTime: 30_000,
      },
      {
        queryKey: ['insights'],
        queryFn: () => fetchInsights(),
        enabled: !!clientId,
        staleTime: 60_000,
      },
      {
        queryKey: ['customer-segments', clientId ?? ''],
        queryFn: () => fetchCustomerSegments(clientId!),
        enabled: !!clientId,
        staleTime: 120_000,
      },
      {
        queryKey: ['top-customers', clientId ?? ''],
        queryFn: () => fetchTopCustomers(clientId!),
        enabled: !!clientId,
        staleTime: 60_000,
      },
      {
        queryKey: ['clientes-history', clientId ?? ''],
        queryFn: () => fetchClientesHistory(clientId!),
        enabled: !!clientId,
        staleTime: 60_000,
      },
      {
        queryKey: ['analytics', 'commercialIndicators', analyticsPeriod],
        queryFn: () => getCommercialIndicators(analyticsPeriod),
        enabled: !!clientId,
        staleTime: 120_000,
        refetchOnMount: 'always' as const,
      },
      {
        queryKey: ['analytics', 'contextMetrics', clientId ?? '', analyticsPeriod],
        queryFn: () => getContextMetrics(analyticsPeriod),
        enabled: !!clientId,
        staleTime: 120_000,
      },
    ],
  })

  const approveMut = useMutation({
    mutationFn: (id: string) => approveRequest(id, clientId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['approvals', 'clientes', clientId] })
      qc.invalidateQueries({ queryKey: ['clientes-history', clientId] })
      addToast('ok', 'Aprovado', 'Ação registrada.')
    },
  })

  const rejectMut = useMutation({
    mutationFn: (id: string) => rejectRequest(id, clientId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['approvals', 'clientes', clientId] })
      addToast('no', 'Rejeitado', 'Ação ignorada.')
    },
  })

  const snoozeMut = useMutation({
    mutationFn: (id: string) => snoozeApproval(id, clientId!, snoozeUntil()),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['approvals', 'clientes', clientId] })
      addToast('sn', 'Adiado', 'Lembrete em 2 horas.')
    },
  })

  const approvals: ApprovalRequest[] = approvalsQ.data ?? []
  const segments: CustomerSegment[] = segmentsQ.data ?? []
  const customers: CustomerRecord[] = customersQ.data ?? []
  const history: ClientesHistoryItem[] = historyQ.data ?? []
  const commercial = commercialQ.data
  const insights: ClientInsight[] = (insightsQ.data ?? []).filter(
    (i) => !i.dimension || i.dimension === 'clientes' || i.dimension === 'commercial'
  )
  const clientesContextMetrics: ContextMetricRow[] = (contextMetricsQ.data ?? []).filter(
    (m) => m.dimension === 'commercial'
  )

  // Total all-time from dim_clientes (via segments), distinct from period-active buyers
  const totalCustomers = segments.reduce((s, seg) => s + seg.count, 0)
  const ativosNoPeriodo = commercial?.clientes_unicos ?? null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div className="rh">
        <div className="rav">👥</div>
        <div>
          <div className="rn">Clientes</div>
          <div className="rd">CRM, follow-up e relacionamento</div>
        </div>
        <div className="ra">
          <button className="btn bs" style={{ fontSize: 11 }} onClick={() => go('home', 'Início')}>
            ← Início
          </button>
          <button className="btn bp" style={{ fontSize: 11 }}>
            + Novo contato
          </button>
        </div>
      </div>

      <div className="room-grid">
        {/* MAIN PANEL */}
        <div className="panel" style={{ gridColumn: 1, gridRow: 1 }}>
          <div className="ph">
            <span className="ph-ttl">Mesa de Trabalho</span>
          </div>
          <div className="rtabs">
            {(['followup', 'ativos', 'historico', 'config'] as Tab[]).map((t) => (
              <div
                key={t}
                className={`rtab${tab === t ? ' on' : ''}`}
                onClick={() => setTab(t)}
              >
                {t === 'followup' ? (
                  <>
                    Follow-up{' '}
                    {!approvalsQ.isLoading && approvals.length > 0 && (
                      <span className="tbdg">{approvals.length}</span>
                    )}
                  </>
                ) : t === 'ativos' ? (
                  'Ativos'
                ) : t === 'historico' ? (
                  'Histórico'
                ) : (
                  'Config'
                )}
              </div>
            ))}
          </div>

          <div className="pb">
            {/* FOLLOW-UP */}
            <div className={`tc${tab === 'followup' ? ' on' : ''}`}>
              {approvalsQ.isLoading ? (
                <div className="dc" style={{ opacity: 0.4 }}>Carregando…</div>
              ) : approvals.length === 0 ? (
                <div style={{ fontSize: 12, color: 'var(--mu)', padding: '16px 0', textAlign: 'center' }}>
                  Nenhum follow-up pendente.
                </div>
              ) : (
                <div className="dl">
                  {approvals.map((ap) => (
                    <ApprovalCard
                      key={ap.id}
                      ap={ap}
                      onApprove={() => approveMut.mutate(ap.id)}
                      onReject={() => rejectMut.mutate(ap.id)}
                      onSnooze={() => snoozeMut.mutate(ap.id)}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* ATIVOS */}

            <div className={`tc${tab === 'ativos' ? ' on' : ''}`}>
              {/* Segment KPI strip */}
              {segmentsQ.isLoading ? (
                <div style={{ fontSize: 11, color: 'var(--mu)', marginBottom: 12 }}>Carregando segmentos…</div>
              ) : segments.length > 0 ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 7, marginBottom: 12 }}>
                  {segments.map((seg) => (
                    <div key={seg.cluster} className="kpi-cell">
                      <div className="kpi-lbl">{seg.cluster}</div>
                      <div className="kpi-val">{seg.count}</div>
                      {seg.avg_ticket !== null && (
                        <div className="kpi-d">{formatBRL(seg.avg_ticket)}</div>
                      )}
                    </div>
                  ))}
                </div>
              ) : null}

              {/* Top customers */}
              {customersQ.isLoading ? (
                <div style={{ fontSize: 11, color: 'var(--mu)' }}>Carregando clientes…</div>
              ) : customers.length === 0 ? (
                <div style={{ fontSize: 12, color: 'var(--mu)', padding: '16px 0', textAlign: 'center' }}>
                  Nenhum cliente encontrado.
                </div>
              ) : (
                <>
                  <div style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--mu)', marginBottom: 8 }}>
                    Top clientes por receita
                  </div>
                  {customers.slice(0, 8).map((c) => (
                    <div key={c.id} className="cli-row">
                      <div
                        className="cli-av"
                        style={{
                          background: c.cluster === 'Alto' ? '#818cf822' : c.cluster === 'Médio' ? '#fbbf2422' : '#6b728022',
                          color: c.cluster === 'Alto' ? '#818cf8' : c.cluster === 'Médio' ? '#fbbf24' : '#6b7280',
                        }}
                      >
                        {c.name.slice(0, 2).toUpperCase()}
                      </div>
                      <span className="cli-name">{c.name}</span>
                      {c.avg_ticket !== null && (
                        <span className="cli-val">{formatBRL(c.avg_ticket)}/compra</span>
                      )}
                      <div
                        className="cli-dot"
                        style={{
                          background:
                            c.cluster === 'Alto' ? 'var(--ok)' :
                            c.cluster === 'Médio' ? 'var(--att)' :
                            'var(--urg)',
                        }}
                      />
                    </div>
                  ))}
                </>
              )}
            </div>

            {/* HISTÓRICO */}
            <div className={`tc${tab === 'historico' ? ' on' : ''}`}>
              {historyQ.isLoading ? (
                <div style={{ fontSize: 11, color: 'var(--mu)' }}>Carregando…</div>
              ) : history.length === 0 ? (
                <div style={{ fontSize: 12, color: 'var(--mu)', padding: '16px 0', textAlign: 'center' }}>
                  Nenhuma ação no histórico.
                </div>
              ) : (
                history.map((item) => (
                  <div key={item.id} className="hi">
                    <div className="hi-n">{item.title}</div>
                    <div className="hi-m">
                      <span>{relativeTime(item.created_at)}</span>
                      <span style={{ color: item.action === 'approved' ? 'var(--ok)' : 'var(--urg)' }}>
                        {item.action === 'approved' ? 'Aprovado' : 'Rejeitado'}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* CONFIG */}
            <div className={`tc${tab === 'config' ? ' on' : ''}`}>
              <RoutineConfigSection domain="clientes" />
            </div>
          </div>

          {/* ANALYTICS CARD — pinned at panel bottom */}
          <div className="anl-card">
            <div className="anl-hd" onClick={() => setAnalyticsOpen(o => !o)}>
              <span className="anl-ttl">📊 Analytics Comercial</span>
              <div className="anl-nums">
                <div className="anl-kpi">
                  <span className="anl-v">{totalCustomers > 0 ? totalCustomers : '—'}</span>
                  <span className="anl-l">Total clientes</span>
                </div>
                <div className="anl-kpi">
                  <span className="anl-v">{ativosNoPeriodo != null ? ativosNoPeriodo : '—'}</span>
                  <span className="anl-l">Ativos {analyticsPeriod}</span>
                </div>
                <div className="anl-kpi">
                  <span className="anl-v">{commercial?.clientes_novos != null ? `+${commercial.clientes_novos}` : '—'}</span>
                  <span className="anl-l">Novos {analyticsPeriod}</span>
                </div>
              </div>
              <span className={`anl-chev${analyticsOpen ? ' open' : ''}`}>▶</span>
            </div>
            <div style={{ display: 'flex', gap: 4, padding: '0 12px 8px' }}>
              {(['30d', '90d', '1y'] as const).map(p => (
                <span
                  key={p}
                  className={`pill${analyticsPeriod === p ? ' on' : ''}`}
                  style={{ cursor: 'pointer' }}
                  onClick={() => setAnalyticsPeriod(p)}
                >
                  {p === '30d' ? '30d' : p === '90d' ? '90d' : '1 ano'}
                </span>
              ))}
            </div>
            <div className={`anl-body${analyticsOpen ? ' open' : ''}`}>
              {commercialQ.isLoading ? (
                <div style={{ fontSize: 11, color: 'var(--mu)', textAlign: 'center', padding: '8px 0' }}>Carregando…</div>
              ) : commercialQ.isError ? (
                <div style={{ fontSize: 11, color: 'var(--urg)', textAlign: 'center', padding: '8px 0' }}>
                  Erro ao carregar.{' '}
                  <span style={{ cursor: 'pointer', textDecoration: 'underline' }} onClick={() => void commercialQ.refetch()}>Tentar novamente</span>
                </div>
              ) : null}
              <div className="anl-kpi-grid">
                <div className="anl-kc">
                  <div className="anl-kl">Clientes únicos</div>
                  <div className="anl-kv">{commercial != null ? commercial.clientes_unicos : '—'}</div>
                </div>
                <div className="anl-kc">
                  <div className="anl-kl">Recorrentes</div>
                  <div className="anl-kv">{commercial != null ? commercial.clientes_recorrentes : '—'}</div>
                </div>
                <div className="anl-kc">
                  <div className="anl-kl">Novos</div>
                  <div className="anl-kv">{commercial != null ? commercial.clientes_novos : '—'}</div>
                </div>
                <div className="anl-kc">
                  <div className="anl-kl">Ticket médio</div>
                  <div className="anl-kv">{formatBRL(commercial?.ticket_medio ?? null)}</div>
                </div>
                <div className="anl-kc">
                  <div className="anl-kl">Churn 60d</div>
                  <div className="anl-kv" style={{ color: commercial?.churn_60d_perc != null ? 'var(--urg)' : undefined }}>
                    {commercial?.churn_60d_perc != null ? `${commercial.churn_60d_perc.toFixed(1)}%` : '—'}
                  </div>
                </div>
                <div className="anl-kc">
                  <div className="anl-kl">Receita período</div>
                  <div className="anl-kv">{formatBRL(commercial?.receita_periodo ?? null)}</div>
                </div>
              </div>
              <div style={{ borderTop: '1px solid var(--gb)', marginTop: 10, paddingTop: 8, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                {([
                  { label: 'Win rate', value: commercial?.win_rate_perc ?? null, fmt: 'perc', src: 'Pipeline CRM' },
                  { label: 'Ciclo venda', value: commercial?.ciclo_venda_dias ?? null, fmt: 'days', src: 'CRM' },
                  { label: 'NRR', value: commercial?.nrr_perc ?? null, fmt: 'perc', src: 'Contratos CRM' },
                  { label: 'Conv. checkout', value: commercial?.checkout_conversion_perc ?? null, fmt: 'perc', src: 'E-commerce' },
                  { label: 'NPS', value: commercial?.nps ?? null, fmt: 'num', src: 'Pesquisa NPS' },
                ] as { label: string; value: number | null; fmt: 'perc' | 'days' | 'num'; src: string }[]).map(({ label, value, fmt, src }) => (
                  <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10.5, background: 'color-mix(in srgb,var(--fg) 5%,transparent)', border: '1px solid color-mix(in srgb,var(--fg) 10%,transparent)', borderRadius: 4, padding: '3px 6px', overflow: 'hidden' }}>
                    <span style={{ color: 'var(--mu)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', minWidth: 0, flexShrink: 1 }}>{label}</span>
                    {value != null ? (
                      <span style={{ fontFamily: 'var(--mono)', fontWeight: 600, whiteSpace: 'nowrap', flexShrink: 0 }}>
                        {fmt === 'perc' ? `${value.toFixed(1)}%` : fmt === 'days' ? `${value.toFixed(0)}d` : value.toFixed(0)}
                      </span>
                    ) : (
                      <span style={{ fontSize: 9, color: 'var(--mu)', opacity: .5, fontStyle: 'italic', whiteSpace: 'nowrap', flexShrink: 0 }}>↳ {src}</span>
                    )}
                  </div>
                ))}
              </div>
              {clientesContextMetrics.length > 0 && (
                <div style={{ borderTop: '1px solid var(--gb)', marginTop: 10, paddingTop: 8, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                  {clientesContextMetrics.map((m) => (
                    <div key={m.kpi} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10.5, background: 'color-mix(in srgb,var(--fg) 5%,transparent)', border: '1px solid color-mix(in srgb,var(--fg) 10%,transparent)', borderRadius: 4, padding: '3px 6px', overflow: 'hidden' }}>
                      <span style={{ color: 'var(--mu)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', minWidth: 0, flexShrink: 1 }}>{m.label}</span>
                      {m.current_value != null && (
                        <span style={{ fontFamily: 'var(--mono)', color: 'var(--fg)', fontWeight: 600, whiteSpace: 'nowrap', flexShrink: 0 }}>
                          {m.unit === 'R$' ? formatBRL(m.current_value) : m.unit === '%' ? `${m.current_value.toFixed(1)}%` : m.current_value.toLocaleString('pt-BR')}
                        </span>
                      )}
                      {m.mom_pct != null && (
                        <span style={{ fontSize: 9, fontFamily: 'var(--mono)', color: m.mom_pct >= 0 ? 'var(--ok)' : 'var(--urg)', background: m.mom_pct >= 0 ? 'color-mix(in srgb,var(--ok) 12%,transparent)' : 'color-mix(in srgb,var(--urg) 12%,transparent)', padding: '1px 3px', borderRadius: 3, whiteSpace: 'nowrap', flexShrink: 0 }}>
                          {m.mom_pct >= 0 ? '↑' : '↓'}{Math.abs(m.mom_pct).toFixed(1)}%
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN */}
        <div className="rcol">
          <RColResizeHandle />
          <CollapsiblePanel id="clientes-rotinas" icon="⚙️" title="Rotinas ativas">
            <RoutineStatusWidget domain="clientes" />
          </CollapsiblePanel>
          <CollapsiblePanel id="clientes-segmentos" icon="📊" title="Segmentos">
            <div className="dr-sec">
                {segmentsQ.isLoading ? (
                  <div style={{ fontSize: 11, color: 'var(--mu)' }}>Carregando…</div>
                ) : segments.length === 0 ? (
                  <div style={{ fontSize: 11, color: 'var(--mu)', textAlign: 'center' }}>
                    Sem dados de segmento.
                  </div>
                ) : (
                  segments.map((seg) => {
                    const pct = totalCustomers > 0 ? Math.round((seg.count / totalCustomers) * 100) : 0
                    const color = seg.cluster === 'Alto' ? '#818cf8' : seg.cluster === 'Médio' ? 'var(--ac)' : 'var(--mu)'
                    return (
                      <div key={seg.cluster} style={{ marginBottom: 10 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11.5, color: 'var(--mu2)', marginBottom: 3 }}>
                          <span>{seg.cluster}</span>
                          <span style={{ fontFamily: 'var(--mono)', color: 'var(--mu)' }}>{seg.count} clientes</span>
                        </div>
                        <div style={{ background: 'var(--gb)', borderRadius: 2, height: 4 }}>
                          <div style={{ background: color, width: `${pct}%`, height: '100%', borderRadius: 2 }} />
                        </div>
                      </div>
                    )
                  })
                )}
              </div>
              {segments.length > 0 && (
                <div className="dr-sec">
                  <div className="dr-ttl">Receita por segmento</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 5, fontSize: 11.5 }}>
                    {segments.map((seg) => (
                      <div key={seg.cluster} style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--mu)' }}>{seg.cluster}</span>
                        <span style={{ fontFamily: 'var(--mono)', color: 'var(--mu2)' }}>
                          {seg.revenue_share !== null ? `${seg.revenue_share.toFixed(0)}%` : '—'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
          </CollapsiblePanel>
          <CollapsiblePanel id="clientes-acoes" icon="📅" title="Últimas ações">
            <div className="dr-sec">
                {historyQ.isLoading ? (
                  <div style={{ fontSize: 11, color: 'var(--mu)' }}>…</div>
                ) : history.slice(0, 4).length === 0 ? (
                  <div style={{ fontSize: 11, color: 'var(--mu)', textAlign: 'center' }}>Nenhuma ação recente.</div>
                ) : (
                  history.slice(0, 4).map((item) => (
                    <div key={item.id} className="hi">
                      <div className="hi-n">{item.title}</div>
                      <div className="hi-m">
                        <span>{relativeTime(item.created_at)}</span>
                        <span style={{ color: item.action === 'approved' ? 'var(--ok)' : 'var(--urg)' }}>
                          {item.action === 'approved' ? '✓' : '✗'}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
          </CollapsiblePanel>
        </div>

        {/* BOTTOM STRIP */}
        <div className="bstrip">
          {insights.slice(0, 3).map((ins) => (
            <div key={ins.id} className="ich">
              <span className="ich-em">⚠️</span>
              <div className="ich-body">
                <span className="ich-tag tg-d">Clientes</span>
                <div className="ich-txt">{ins.title}</div>
              </div>
            </div>
          ))}
          <div className="nums-chip" onClick={() => setTab('config')} style={{ cursor: 'pointer' }}>
            <div className="nums-head">⚙️ Rotinas ativas</div>
            <div style={{ fontSize: 11, color: 'var(--mu)' }}>Ver na aba Config →</div>
          </div>
          <div className="nums-chip">
            <div className="nums-head">👥 Carteira</div>
            <div className="nums-row">
              <div className="nkpi">
                <span className="nv" style={{ fontSize: 18 }}>
                  {segmentsQ.isLoading ? '…' : totalCustomers > 0 ? totalCustomers : '—'}
                </span>
                <span className="nl">total</span>
                {commercial?.clientes_novos != null && commercial.clientes_novos > 0 && (
                  <span className="nd up">↑ {commercial.clientes_novos} novos</span>
                )}
              </div>
              <div className="nkpi">
                <span className="nv" style={{ fontSize: 18 }}>
                  {commercialQ.isLoading ? '…' : ativosNoPeriodo != null ? ativosNoPeriodo : '—'}
                </span>
                <span className="nl">ativos {analyticsPeriod}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Approval card ──────────────────────────────────────────────
function ApprovalCard({
  ap,
  onApprove,
  onReject,
  onSnooze,
}: {
  ap: ApprovalRequest
  onApprove: () => void
  onReject: () => void
  onSnooze: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const isUrgent = ap.priority === 'urgent' || ap.priority === 'high'
  const priorityColor = ap.priority === 'urgent' ? '#f87171' : ap.priority === 'high' ? '#818cf8' : '#2dd4bf'
  const badgeLabel = ap.priority === 'urgent' ? 'Risco' : ap.priority === 'high' ? 'Oportunidade' : 'Alerta'

  return (
    <div className={`dc ${isUrgent ? 'urg' : 'warn'}${expanded ? ' expanded' : ''}`}>
      <div className="dc-row" onClick={() => setExpanded(!expanded)}>
        <div className="ag">
          <div className="agd" style={{ background: priorityColor }} />
          Clientes
        </div>
        <span className={`bdg ${isUrgent ? 'bu' : 'bw'}`}>{badgeLabel}</span>
        <span className="dc-row-summary">{ap.title}</span>
        <span className="dt">
          {new Date(ap.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
        </span>
        <span className="dc-chev">{expanded ? '▼' : '▶'}</span>
      </div>
      {expanded && (
        <div className="dc-expand">
          {ap.body && <div className="db">{ap.body}</div>}
          <div className="dc-act">
            <button className="btn bp" onClick={onApprove}>
              {isUrgent ? '📞 Agendar reunião' : '📄 Aprovar'}
            </button>
            <button className="btn bg" onClick={onSnooze}>⏰ Depois</button>
            <button className="btn bs" onClick={onReject}>Ignorar</button>
          </div>
        </div>
      )}
    </div>
  )
}
