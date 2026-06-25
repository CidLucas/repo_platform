import { useState, useEffect } from 'react'
import { useQueries, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAppStore } from '../../store/appStore'
import { useAuth } from '../../hooks/useAuth'
import {
  fetchApprovalsByAgent,
  approveRequest,
  rejectRequest,
  snoozeApproval,
} from '../../api/approvals'
import { fetchInsights, formatKpi } from '../../api/insights'
import { fetchSuppliers, fetchComprasHistory } from '../../api/suppliers'
import { getSupplyIndicators, getContextMetrics, type ContextMetricRow } from '../../api/analytics'
import { useApprovalStats } from '../../hooks/useApprovalStats'
import RoutineConfigSection from '../../components/shared/RoutineConfigSection'

import RoutineExecutionFeed from '../../components/shared/RoutineExecutionFeed'
import RColResizeHandle from '../../components/shared/RColResizeHandle'
import CollapsiblePanel from '../../components/shared/CollapsiblePanel'
import DecisionCard from '../../components/shared/DecisionCard'
import EmptyState from '../../components/shared/EmptyState'
import LoadingState from '../../components/shared/LoadingState'
import { snoozeUntil } from '../../utils/time'
import { formatBRL } from '../../utils/formatters'

type Tab = 'decisoes' | 'tarefas' | 'historico' | 'config'

const LOADING_TIMEOUT = 15_000

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })
}

function ratingStars(rating: number | null) {
  const r = Math.round(rating ?? 0)
  return '★'.repeat(r) + '☆'.repeat(5 - r)
}

export default function ComprasRoom() {
  const { go, addToast, initialTab, clearInitialTab, openChatWith } = useAppStore()
  const { clientId } = useAuth()
  const qc = useQueryClient()
  const [tab, setTab] = useState<Tab>('decisoes')
  const [analyticsOpen, setAnalyticsOpen] = useState(false)
  const [analyticsPeriod, setAnalyticsPeriod] = useState<'30d' | '90d' | '1y'>('30d')

  // Navigate to the tab requested via goWithTab() from another screen
  useEffect(() => {
    if (!initialTab) return
    const validTabs: Tab[] = ['decisoes', 'tarefas', 'historico', 'config']
    if (validTabs.includes(initialTab as Tab)) setTab(initialTab as Tab)
    clearInitialTab()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const { data: approvalStats } = useApprovalStats()

  const [approvalsQ, insightsQ, suppliersQ, historyQ, supplyQ, contextMetricsQ] = useQueries({
    queries: [
      {
        queryKey: ['approvals', 'compras', clientId ?? ''],
        queryFn: () => fetchApprovalsByAgent('compras', clientId!),
        enabled: !!clientId,
        staleTime: 30_000,
      },
      {
        queryKey: ['insights'],
        queryFn: () => fetchInsights(10, 'compras'),
        enabled: !!clientId,
        staleTime: 60_000,
      },
      {
        queryKey: ['suppliers', clientId ?? ''],
        queryFn: () => fetchSuppliers(clientId!),
        enabled: !!clientId,
        staleTime: 120_000,
      },
      {
        queryKey: ['compras-history', clientId ?? ''],
        queryFn: () => fetchComprasHistory(clientId!),
        enabled: !!clientId,
        staleTime: 60_000,
      },
      {
        queryKey: ['analytics', 'supplyIndicators', analyticsPeriod],
        queryFn: () => getSupplyIndicators(analyticsPeriod),
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

  const invalidateApprovals = () => qc.invalidateQueries({ queryKey: ['approvals'] })

  useEffect(() => {
    if (!supplyQ.isLoading) return
    const t = setTimeout(() => {
      if (supplyQ.isLoading) {
        console.warn('[ComprasRoom] supply indicators loading timeout after', LOADING_TIMEOUT, 'ms')
      }
    }, LOADING_TIMEOUT)
    return () => clearTimeout(t)
  }, [supplyQ.isLoading])

  const approveMut = useMutation({
    mutationFn: (id: string) => approveRequest(id, clientId!),
    onSuccess: () => { invalidateApprovals(); addToast('ok', 'Aprovado', 'Compra autorizada.') },
  })
  const rejectMut = useMutation({
    mutationFn: (id: string) => rejectRequest(id, clientId!),
    onSuccess: () => { invalidateApprovals(); addToast('no', 'Rejeitado', 'Blu anotou.') },
  })
  const snoozeMut = useMutation({
    mutationFn: (id: string) => snoozeApproval(id, clientId!, snoozeUntil()),
    onSuccess: () => { invalidateApprovals(); addToast('sn', 'Adiado', 'Lembrete em 2 horas.') },
  })
  const approvals = approvalsQ.data ?? []
  const pendingCount = approvals.length
  const suppliers = suppliersQ.data ?? []
  const history = historyQ.data ?? []
  const supply = supplyQ.data
  const comprasInsights = (insightsQ.data ?? []).filter(
    () => true  // room filter is server-side via p_room='compras'
  )
  const comprasContextMetrics: ContextMetricRow[] = (contextMetricsQ.data ?? []).filter(
    (m) => m.dimension === 'supply' || m.dimension === 'inventory'
  )

  // Compute monthly stats from history
  const approvedItems = history.filter(h => h.status === 'approved')
  const totalGasto = approvedItems.reduce((sum, h) => sum + (h.amount ?? 0), 0)
  const totalDecisions = (approvalStats?.total_approved ?? 0) + (approvalStats?.total_rejected ?? 0)

  return (
    <div>
      <div className="rh">
        <div className="rav">🛒</div>
        <div><div className="rn">Compras</div><div className="rd">Cotações, fornecedores e estoque</div></div>
        <div className="ra">
          <button className="btn bs" style={{ fontSize: 11 }} onClick={() => go('home', 'Início')}>← Início</button>
          <button className="btn bp" style={{ fontSize: 11 }} onClick={() => openChatWith('Quero criar uma nova missão de compras')}>+ Nova Missão</button>
        </div>
      </div>
      <div className="room-grid">

        <div className="panel" style={{ gridColumn: 1, gridRow: 1 }}>
          <div className="ph">
            <span className="ph-ttl">Mesa de Trabalho</span>
            <span className="ph-cnt" id="cCnt">{pendingCount} pendente{pendingCount !== 1 ? 's' : ''}</span>
          </div>
          <div className="rtabs" id="cTabs">
            {(['decisoes', 'tarefas', 'historico', 'config'] as Tab[]).map(t => (
              <div key={t} className={`rtab${tab === t ? ' on' : ''}`} onClick={() => setTab(t)}>
                {t === 'decisoes'
                  ? <>Decisões {pendingCount > 0 && <span className="tbdg">{pendingCount}</span>}</>
                  : t.charAt(0).toUpperCase() + t.slice(1)}
              </div>
            ))}
          </div>
          <div className="pb">

            {/* DECISÕES */}
            <div className={`tc${tab === 'decisoes' ? ' on' : ''}`} id="c-decisoes">
              <div className={`dl${approvals.length === 0 ? '' : approvals.length <= 3 ? ' dl-few' : ' dl-many'}`}>
                {approvalsQ.isLoading && (
                  <LoadingState message="Carregando decisões de compras…" />
                )}
                {!approvalsQ.isLoading && approvals.length === 0 && (
                  <EmptyState
                    icon="✓"
                    title="Tudo em dia"
                    description="Nenhuma decisão pendente em Compras. O Blu irá notificá-lo quando houver algo para resolver."
                  />
                )}
                {approvals.map(approval => (
                  <DecisionCard
                    key={approval.id}
                    approval={approval}
                    onApprove={() => approveMut.mutate(approval.id)}
                    onReject={() => rejectMut.mutate(approval.id)}
                    onSnooze={() => snoozeMut.mutate(approval.id)}
                  />
                ))}
              </div>

            </div>

            {/* TAREFAS */}
            <div className={`tc${tab === 'tarefas' ? ' on' : ''}`} id="c-tarefas">
              <RoutineExecutionFeed domain="compras" />
            </div>

            {/* HISTÓRICO */}
            <div className={`tc${tab === 'historico' ? ' on' : ''}`} id="c-historico">
              {historyQ.isLoading && <LoadingState message="Carregando histórico de compras…" />}
              {!historyQ.isLoading && history.length === 0 && (
                <EmptyState
                  icon="🛒"
                  title="Nenhuma compra registrada"
                  description="Quando você aprovar uma compra, ela aparecerá aqui."
                />
              )}
              {history.map(h => (
                <div key={h.id} className="hi">
                  <div className="hi-n">{h.title}</div>
                  <div className="hi-m">
                    <span>{formatDate(h.created_at)}</span>
                    {h.amount != null && <span className="hi-a">{formatBRL(h.amount)}</span>}
                    <span style={{ color: h.status === 'approved' ? 'var(--ok)' : 'var(--urg)' }}>
                      {h.status === 'approved' ? '✓' : '✗'}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {/* CONFIG */}
            <div className={`tc${tab === 'config' ? ' on' : ''}`} id="c-config">
              <RoutineConfigSection domain="compras" />
            </div>

          </div>

          {/* ANALYTICS CARD — pinned at panel bottom */}
          <div className="anl-card">
            <div className="anl-hd" onClick={() => setAnalyticsOpen(o => !o)}>
              <span className="anl-ttl">📊 Analytics de Compras</span>
              <div className="anl-nums">
                <div className="anl-kpi">
                  <span className="anl-v">{supply ? supply.rfqs_abertas : '—'}</span>
                  <span className="anl-l">RFQs abertas</span>
                </div>
                <div className="anl-kpi">
                  <span className="anl-v">{supply ? supply.fornecedores_ativos : '—'}</span>
                  <span className="anl-l">Fornecedores</span>
                </div>
                <div className="anl-kpi">
                  <span className="anl-v">{supply?.taxa_resposta_perc != null ? `${supply.taxa_resposta_perc.toFixed(0)}%` : '—'}</span>
                  <span className="anl-l">Taxa resposta</span>
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
              {supplyQ.isLoading ? (
                <LoadingState message="Carregando indicadores de suprimentos…" />
              ) : supplyQ.isError ? (
                <div style={{ fontSize: 11, color: 'var(--urg)', textAlign: 'center', padding: '8px 0' }}>
                  Erro ao carregar.{' '}
                  <span style={{ cursor: 'pointer', textDecoration: 'underline' }} onClick={() => void supplyQ.refetch()}>Tentar novamente</span>
                </div>
              ) : null}
              <div className="anl-kpi-grid">
                <div className="anl-kc">
                  <div className="anl-kl">Spend no período</div>
                  <div className="anl-kv">{supply ? formatBRL(supply.spend_periodo) : '—'}</div>
                </div>
                <div className="anl-kc">
                  <div className="anl-kl">POs aprovadas</div>
                  <div className="anl-kv">{supply?.pos_aprovadas ?? '—'}</div>
                </div>
                <div className="anl-kc">
                  <div className="anl-kl">POs pendentes</div>
                  <div className="anl-kv">{supply?.pos_pendentes_aprovacao ?? '—'}</div>
                </div>
                <div className="anl-kc">
                  <div className="anl-kl">Lead time médio</div>
                  <div className="anl-kv">{supply?.lead_time_medio_dias != null ? `${supply.lead_time_medio_dias.toFixed(1)}d` : '—'}</div>
                </div>
                <div className="anl-kc">
                  <div className="anl-kl">OTIF</div>
                  <div className="anl-kv" style={{ color: 'var(--ok)' }}>{supply?.otif_perc != null ? `${supply.otif_perc.toFixed(1)}%` : '—'}</div>
                </div>
                <div className="anl-kc">
                  <div className="anl-kl">Decisões (total)</div>
                  <div className="anl-kv">{totalDecisions > 0 ? totalDecisions : '—'}</div>
                </div>
                <div className="anl-kc">
                  <div className="anl-kl">Concentração top forn.</div>
                  <div className="anl-kv" style={{ color: supply?.concentracao_top_perc != null && supply.concentracao_top_perc > 50 ? 'var(--att)' : undefined }}>
                    {supply?.concentracao_top_perc != null ? `${supply.concentracao_top_perc.toFixed(0)}%` : '—'}
                  </div>
                </div>
              </div>
              <div style={{ borderTop: '1px solid var(--gb)', marginTop: 10, paddingTop: 8, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                {([
                  { label: 'Cost savings', value: supply?.cost_savings_perc ?? null, fmt: 'perc', src: 'Catálogo preços ref.' },
                  { label: 'PPV', value: supply?.ppv ?? null, fmt: 'brl', src: 'Catálogo preços ref.' },
                  { label: 'Maverick spend', value: supply?.maverick_spend_perc ?? null, fmt: 'perc', src: 'Fornecedores aprovados' },
                  { label: 'Spend gerido', value: supply?.spend_under_management_perc ?? null, fmt: 'perc', src: 'Cobertura contratual' },
                ] as { label: string; value: number | null; fmt: 'perc' | 'brl'; src: string }[]).map(({ label, value, fmt, src }) => (
                  <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10.5, background: 'color-mix(in srgb,var(--fg) 5%,transparent)', border: '1px solid color-mix(in srgb,var(--fg) 10%,transparent)', borderRadius: 4, padding: '3px 6px', overflow: 'hidden' }}>
                    <span style={{ color: 'var(--mu)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', minWidth: 0, flexShrink: 1 }}>{label}</span>
                    {value != null ? (
                      <span style={{ fontFamily: 'var(--mono)', fontWeight: 600, whiteSpace: 'nowrap', flexShrink: 0 }}>
                        {fmt === 'perc' ? `${value.toFixed(1)}%` : formatBRL(value)}
                      </span>
                    ) : (
                      <span style={{ fontSize: 9, color: 'var(--mu)', opacity: .5, fontStyle: 'italic', whiteSpace: 'nowrap', flexShrink: 0 }}>↳ {src}</span>
                    )}
                  </div>
                ))}
              </div>
              {comprasContextMetrics.length > 0 && (
                <div style={{ borderTop: '1px solid var(--gb)', marginTop: 10, paddingTop: 8, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                  {comprasContextMetrics.map((m) => (
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

        <div className="rcol">
          <RColResizeHandle />

          <CollapsiblePanel id="compras-fornecedores" icon="📁" title="Fornecedores" action={<button className="ph-add" onClick={() => openChatWith('Quero cadastrar um novo fornecedor')}>＋</button>}>
            <div className="dr-sec">
                <div className="pills"><span className="pill on">Todos</span><span className="pill">Escritório</span><span className="pill">Insumos</span></div>
                {suppliersQ.isLoading && <LoadingState message="Carregando fornecedores…" />}
                {!suppliersQ.isLoading && suppliers.length === 0 && (
                  <EmptyState
                    icon="📁"
                    title="Nenhum fornecedor cadastrado"
                    description="Cadastre fornecedores para que os agentes possam cotar preços e gerenciar relacionamentos."
                  />
                )}
                {suppliers.map(s => (
                  <div key={s.id} className="sup-row">
                    <span>🏪</span>
                    <div>
                      <div className="sup-n">{s.name}</div>
                      <div className="sup-c" style={s.nivel_cluster === 'risco' ? { color: 'var(--urg)' } : undefined}>
                        {s.nivel_cluster === 'risco' ? `⚠ ${s.category ?? ''}` : (s.category ?? '')}
                      </div>
                    </div>
                    <span className="stars">{ratingStars(s.rating)}</span>
                  </div>
                ))}
              </div>
              <div className="dr-sec">
                <div className="dr-ttl">Este mês</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 5, fontSize: 11.5 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--mu)' }}>Total gasto</span>
                    <span style={{ fontFamily: 'var(--mono)' }}>{formatBRL(totalGasto || null)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--mu)' }}>Aprovadas</span>
                    <span style={{ fontFamily: 'var(--mono)', color: 'var(--ok)' }}>{approvedItems.length}</span>
                  </div>
                </div>
              </div>
          </CollapsiblePanel>
          <CollapsiblePanel id="compras-historico" icon="🕐" title="Histórico recente">
            <div className="dr-sec">
                {historyQ.isLoading && <LoadingState message="Carregando histórico…" />}
                {history.slice(0, 3).map(h => (
                  <div key={h.id} className="hi">
                    <div className="hi-n">{h.title}</div>
                    <div className="hi-m">
                      <span>{formatDate(h.created_at)}</span>
                      {h.amount != null && <span className="hi-a">{formatBRL(h.amount)}</span>}
                    </div>
                  </div>
                ))}
              </div>
          </CollapsiblePanel>
        </div>

        <div className="bstrip">
          {comprasInsights.length > 0 ? comprasInsights.slice(0, 3).map(ins => (
            <div key={ins.id} className="ich">
              <span className="ich-em">
                {ins.severity === 'error' ? '⚠️' : ins.severity === 'warning' ? '💡' : '🔍'}
              </span>
              <div className="ich-body">
                <span className="ich-tag tg-s">{formatKpi(ins.kpi)}</span>
                <div className="ich-txt">{ins.title}</div>
              </div>
            </div>
          )) : (
            <div className="ich"><span className="ich-em">🔍</span><div className="ich-body"><span className="ich-tag tg-s">Insight</span><div className="ich-txt">Carregando insights de compras…</div></div></div>
          )}
          <div className="nums-chip" onClick={() => setTab('tarefas')} style={{ cursor: 'pointer' }}>
            <div className="nums-head">⚙️ Rotinas ativas</div>
            <div style={{ fontSize: 11, color: 'var(--mu)' }}>Ver na aba Tarefas →</div>
          </div>
        </div>

      </div>
    </div>
  )
}
