import { useState } from 'react'
import { useQueries, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAppStore } from '../../store/appStore'
import { useAuth } from '../../hooks/useAuth'
import {
  fetchApprovalsByAgent,
  approveRequest,
  rejectRequest,
  snoozeApproval,
} from '../../api/approvals'
import { fetchInsights } from '../../api/insights'
import { fetchConnectedAccounts, fetchReportRuns } from '../../api/financeiro'
import { fetchRoutineConfig, upsertRoutineConfig } from '../../api/routines'
import { getFinanceIndicators, getContextMetrics, type ContextMetricRow } from '../../api/analytics'
import RColResizeHandle from '../../components/shared/RColResizeHandle'
import CollapsiblePanel from '../../components/shared/CollapsiblePanel'
import RoutinesPanel from '../../components/shared/RoutinesPanel'

type Tab = 'decisoes' | 'tarefas' | 'relatorios' | 'config'

function snoozeUntil() {
  return new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString()
}

function formatBRL(value: number | null) {
  if (value === null) return '—'
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
}

function fmtCompact(value: number | null): string {
  if (value === null) return '—'
  const abs = Math.abs(value)
  if (abs >= 1_000_000) return `R$ ${(value / 1_000_000).toFixed(1)}M`
  if (abs >= 1_000) return `R$ ${(value / 1_000).toFixed(0)}K`
  return formatBRL(value)
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
}

function relativeTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime()
  const d = Math.floor(diff / 86400000)
  if (d === 0) return 'hoje'
  if (d === 1) return 'ontem'
  return `${d} dias atrás`
}

const REPORT_LABELS: Record<string, string> = {
  dre: 'DRE',
  cash_flow: 'Fluxo de Caixa',
  margin: 'Análise de Margem',
  custom: 'Personalizado',
}

export default function FinanceiroRoom() {
  const { go, toggleDc, expandedId, addToast } = useAppStore()
  const { clientId } = useAuth()
  const qc = useQueryClient()
  const [tab, setTab] = useState<Tab>('decisoes')
  const [analyticsOpen, setAnalyticsOpen] = useState(false)
  const [analyticsPeriod, setAnalyticsPeriod] = useState<'30d' | '90d' | '1y'>('30d')

  const [approvalsQ, insightsQ, kpiQ, accountsQ, reportsQ, configQ, contextMetricsQ] = useQueries({
    queries: [
      {
        queryKey: ['approvals', 'financeiro', clientId ?? ''],
        queryFn: () => fetchApprovalsByAgent('financeiro', clientId!),
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
        queryKey: ['finance-indicators', analyticsPeriod],
        queryFn: () => getFinanceIndicators(analyticsPeriod),
        enabled: !!clientId,
        staleTime: 120_000,
        refetchOnMount: 'always' as const,
      },
      {
        queryKey: ['financeiro-accounts', clientId ?? ''],
        queryFn: () => fetchConnectedAccounts(clientId!),
        enabled: !!clientId,
        staleTime: 60_000,
      },
      {
        queryKey: ['financeiro-reports', clientId ?? ''],
        queryFn: () => fetchReportRuns(clientId!),
        enabled: !!clientId,
        staleTime: 60_000,
      },
      {
        queryKey: ['config', 'financeiro', clientId ?? ''],
        queryFn: () => fetchRoutineConfig(clientId!, 'financeiro'),
        enabled: !!clientId,
        staleTime: 60_000,
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

  const approveMut = useMutation({
    mutationFn: (id: string) => approveRequest(id, clientId!),
    onSuccess: () => { invalidateApprovals(); addToast('ok', 'Aprovado', 'Pagamento agendado.') },
  })
  const rejectMut = useMutation({
    mutationFn: (id: string) => rejectRequest(id, clientId!),
    onSuccess: () => { invalidateApprovals(); addToast('no', 'Rejeitado', 'Blu anotou.') },
  })
  const snoozeMut = useMutation({
    mutationFn: (id: string) => snoozeApproval(id, clientId!, snoozeUntil()),
    onSuccess: () => { invalidateApprovals(); addToast('sn', 'Adiado', 'Lembrete em 2 horas.') },
  })
  const configMut = useMutation({
    mutationFn: (cfg: Record<string, unknown>) => upsertRoutineConfig(clientId!, 'financeiro', cfg),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['config', 'financeiro', clientId ?? ''] }),
  })

  const approvals = approvalsQ.data ?? []
  const pendingCount = approvals.length

  const finInsights = (insightsQ.data ?? []).filter(
    i => !i.dimension || i.dimension === 'financeiro'
  )
  const financeiroContextMetrics: ContextMetricRow[] = (contextMetricsQ.data ?? []).filter(
    (m) => m.dimension === 'finance'
  )

  const fin = kpiQ.data

  const accounts = accountsQ.data ?? []
  const consolidatedBalance = accounts.reduce((sum, a) => sum + (a.balance ?? 0), 0)

  const reports = reportsQ.data ?? []
  const cfg = configQ.data ?? {}
  const costVariancePct = typeof cfg.cost_variance_pct === 'number' ? cfg.cost_variance_pct : 10
  const dreDay = typeof cfg.dre_day === 'number' ? cfg.dre_day : 2

  return (
    <div>
      <div className="rh">
        <div className="rav">📊</div>
        <div><div className="rn">Financeiro</div><div className="rd">Fluxo de caixa, pagamentos e relatórios</div></div>
        <div className="ra">
          <button className="btn bs" style={{ fontSize: 11 }} onClick={() => go('home', 'Início')}>← Início</button>
          <button className="btn bp" style={{ fontSize: 11 }}>+ Nova Missão</button>
        </div>
      </div>
      <div className="room-grid">

        <div className="panel" style={{ gridColumn: 1, gridRow: 1 }}>
          <div className="ph">
            <span className="ph-ttl">Mesa de Trabalho</span>
            <span className="ph-cnt">{pendingCount} pendente{pendingCount !== 1 ? 's' : ''}</span>
          </div>
          <div className="rtabs" id="fTabs">
            {(['decisoes', 'tarefas', 'relatorios', 'config'] as Tab[]).map(t => (
              <div key={t} className={`rtab${tab === t ? ' on' : ''}`} onClick={() => setTab(t)}>
                {t === 'decisoes' ? <>Decisões {pendingCount > 0 && <span className="tbdg">{pendingCount}</span>}</> : t === 'relatorios' ? 'Relatórios' : t.charAt(0).toUpperCase() + t.slice(1)}
              </div>
            ))}
          </div>
          <div className="pb">

            {/* DECISÕES */}
            <div className={`tc${tab === 'decisoes' ? ' on' : ''}`} id="f-decisoes">
              <div className="dl">
                {approvalsQ.isLoading && (
                  <div style={{ padding: '12px 0', color: 'var(--mu)', fontSize: 12 }}>Carregando…</div>
                )}
                {!approvalsQ.isLoading && approvals.length === 0 && (
                  <div style={{ padding: '12px 0', color: 'var(--mu)', fontSize: 12 }}>Nenhuma decisão pendente ✓</div>
                )}
                {approvals.map(approval => {
                  const isExpanded = expandedId === approval.id
                  const isUrgent = approval.priority === 'urgent' || approval.priority === 'high'
                  const cls = ['dc', isUrgent ? 'urg' : 'warn', isExpanded ? 'expanded' : ''].filter(Boolean).join(' ')
                  return (
                    <div key={approval.id} className={cls} id={approval.id}>
                      <div className="dc-row" onClick={() => toggleDc(approval.id)}>
                        <div className="ag">
                          <div className="agd" style={{ background: '#34d399' }} />Boleto
                        </div>
                        <span className={isUrgent ? 'bdg bu' : 'bdg bw'}>{isUrgent ? 'Urgente' : 'Amanhã'}</span>
                        <span className="dc-row-summary">{approval.title}</span>
                        <span className="dt">{formatTime(approval.created_at)}</span>
                        <span className="dc-chev">▶</span>
                      </div>
                      <div className="dc-expand">
                        <div className="db">{approval.body}</div>
                        <div className="dc-act">
                          <button className="btn bp" onClick={() => approveMut.mutate(approval.id)}>👍 Agendar</button>
                          <button className="btn bg" onClick={() => snoozeMut.mutate(approval.id)}>⏰ Depois</button>
                          <button className="btn bs" onClick={() => rejectMut.mutate(approval.id)}>✗ Rejeitar</button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* TAREFAS */}
            <div className={`tc${tab === 'tarefas' ? ' on' : ''}`} id="f-tarefas">
              <RoutinesPanel domain="financeiro" />
            </div>

            {/* RELATÓRIOS */}
            <div className={`tc${tab === 'relatorios' ? ' on' : ''}`} id="f-relatorios">
              {reportsQ.isLoading && <div style={{ color: 'var(--mu)', fontSize: 12, padding: '12px 0' }}>Carregando…</div>}
              {!reportsQ.isLoading && reports.length === 0 && (
                <div style={{ color: 'var(--mu)', fontSize: 12, padding: '12px 0' }}>Nenhum relatório gerado.</div>
              )}
              {reports.map(r => (
                <div key={r.id} className="hi">
                  <div className="hi-n">{REPORT_LABELS[r.report_type] ?? 'Relatório'} — {r.period}</div>
                  <div className="hi-m">
                    <span>{relativeTime(r.created_at)}</span>
                    {r.file_url && r.status === 'ready' ? (
                      <a
                        className="hi-a"
                        href={r.file_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ color: 'var(--ok)' }}
                      >
                        ✓ Baixar
                      </a>
                    ) : (
                      <span className="hi-a" style={{ color: r.status === 'error' ? 'var(--urg)' : 'var(--att)' }}>
                        {r.status === 'generating' ? 'Gerando…' : r.status === 'error' ? 'Erro' : 'PDF'}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* CONFIG */}
            <div className={`tc${tab === 'config' ? ' on' : ''}`} id="f-config">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
                <div style={{ background: 'var(--glass)', border: '1px solid var(--gb)', borderRadius: 'var(--r)', padding: '11px 12px' }}>
                  <div style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 3 }}>Alerta de variação de custos</div>
                  <div style={{ fontSize: 11, color: 'var(--mu)', marginBottom: 7 }}>Notificar quando uma categoria variar mais que:</div>
                  <div className="pills">
                    {[10, 15, 20].map(pct => (
                      <span
                        key={pct}
                        className={`pill${costVariancePct === pct ? ' on' : ''}`}
                        style={{ cursor: 'pointer' }}
                        onClick={() => configMut.mutate({ ...cfg, cost_variance_pct: pct })}
                      >
                        {pct}%
                      </span>
                    ))}
                  </div>
                </div>
                <div style={{ background: 'var(--glass)', border: '1px solid var(--gb)', borderRadius: 'var(--r)', padding: '11px 12px' }}>
                  <div style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 3 }}>Geração automática de DRE</div>
                  <div style={{ fontSize: 11, color: 'var(--mu)', marginBottom: 7 }}>Gerar e enviar ao contador no dia:</div>
                  <div className="pills">
                    {[1, 2, 5, 10].map(d => (
                      <span
                        key={d}
                        className={`pill${dreDay === d ? ' on' : ''}`}
                        style={{ cursor: 'pointer' }}
                        onClick={() => configMut.mutate({ ...cfg, dre_day: d })}
                      >
                        {d}
                      </span>
                    ))}
                  </div>
                </div>
                <div style={{ marginTop: 4 }}>
                  <RoutinesPanel domain="financeiro" />
                </div>
              </div>
            </div>
            <div className="anl-hd" onClick={() => setAnalyticsOpen(o => !o)}>
              <span className="anl-ttl">📊 Analytics</span>
              <div className="anl-nums">
                <div className="anl-kpi">
                  <span className="anl-l">Faturamento</span>
                  <span className="anl-v">{fmtCompact(fin?.receita_liquida ?? null)}</span>
                </div>
                <div className="anl-kpi">
                  <span className="anl-l">Margem</span>
                  <span className="anl-v" style={{ color: 'var(--ok)' }}>
                    {fin?.margem_bruta_perc != null ? `${fin.margem_bruta_perc.toFixed(1)}%` : '—'}
                  </span>
                </div>
                <div className="anl-kpi">
                  <span className="anl-l">Caixa</span>
                  <span className="anl-v">{formatBRL(consolidatedBalance)}</span>
                </div>
              </div>
              <span className={`anl-chev${analyticsOpen ? ' open' : ''}`} id="anlChev">▶</span>
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
            <div className={`anl-body${analyticsOpen ? ' open' : ''}`} id="anlBody">
              {kpiQ.isLoading ? (
                <div style={{ fontSize: 11, color: 'var(--mu)', textAlign: 'center', padding: '8px 0' }}>Carregando…</div>
              ) : kpiQ.isError ? (
                <div style={{ fontSize: 11, color: 'var(--urg)', textAlign: 'center', padding: '8px 0' }}>
                  Erro ao carregar.{' '}
                  <span style={{ cursor: 'pointer', textDecoration: 'underline' }} onClick={() => void kpiQ.refetch()}>Tentar novamente</span>
                </div>
              ) : null}
              <div className="anl-kpi-grid">
                <div className="anl-kc">
                  <div className="anl-kl">Faturamento</div>
                  <div className="anl-kv">{fmtCompact(fin?.receita_liquida ?? null)}</div>
                  {fin?.receita_yoy_perc != null && (
                    <div className={`anl-kd ${fin.receita_yoy_perc >= 0 ? 'up' : 'dn'}`}>
                      {fin.receita_yoy_perc >= 0 ? '↑' : '↓'} {Math.abs(fin.receita_yoy_perc).toFixed(1)}% vs. período anterior
                    </div>
                  )}
                </div>
                <div className="anl-kc">
                  <div className="anl-kl">Despesas</div>
                  <div className="anl-kv">{fmtCompact(fin?.custo_total ?? null)}</div>
                </div>
                <div className="anl-kc">
                  <div className="anl-kl">Margem bruta</div>
                  <div className="anl-kv" style={{ color: 'var(--ok)' }}>
                    {fin?.margem_bruta_perc != null ? `${fin.margem_bruta_perc.toFixed(1)}%` : '—'}
                  </div>
                </div>
                <div className="anl-kc">
                  <div className="anl-kl">Caixa consolidado</div>
                  <div className="anl-kv">{formatBRL(consolidatedBalance)}</div>
                </div>
                <div className="anl-kc">
                  <div className="anl-kl">Ticket médio</div>
                  <div className="anl-kv">{formatBRL(fin?.ticket_medio ?? null)}</div>
                </div>
                <div className="anl-kc">
                  <div className="anl-kl">Pedidos</div>
                  <div className="anl-kv">{fin?.total_pedidos ?? '—'}</div>
                </div>
              </div>
              <div style={{ borderTop: '1px solid var(--gb)', marginTop: 10, paddingTop: 8, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                {([
                  { label: 'Margem operacional', value: fin?.margem_operacional_perc ?? null, fmt: 'perc', src: 'ERP / Contabilidade' },
                  { label: 'Burn rate mensal', value: fin?.burn_rate_mensal ?? null, fmt: 'brl', src: 'Integração contábil' },
                  { label: 'Runway', value: fin?.runway_meses ?? null, fmt: 'months', src: 'Contábil + caixa' },
                  { label: 'DSO', value: fin?.dso_dias ?? null, fmt: 'days', src: 'Sistema de cobrança' },
                  { label: 'DPO', value: fin?.dpo_dias ?? null, fmt: 'days', src: 'ERP / AP' },
                  { label: 'CCC', value: fin?.ccc_dias ?? null, fmt: 'days', src: 'DSO + DPO + estoque' },
                  { label: 'Fluxo 30d', value: fin?.cash_flow_30d ?? null, fmt: 'brl', src: 'Saldos diários' },
                ] as { label: string; value: number | null; fmt: 'perc' | 'brl' | 'days' | 'months'; src: string }[]).map(({ label, value, fmt, src }) => (
                  <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10.5, background: 'color-mix(in srgb,var(--fg) 5%,transparent)', border: '1px solid color-mix(in srgb,var(--fg) 10%,transparent)', borderRadius: 4, padding: '3px 6px', overflow: 'hidden' }}>
                    <span style={{ color: 'var(--mu)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', minWidth: 0, flexShrink: 1 }}>{label}</span>
                    {value != null ? (
                      <span style={{ fontFamily: 'var(--mono)', fontWeight: 600, whiteSpace: 'nowrap', flexShrink: 0 }}>
                        {fmt === 'perc' ? `${value.toFixed(1)}%`
                          : fmt === 'brl' ? formatBRL(value)
                          : fmt === 'months' ? `${value.toFixed(1)}m`
                          : `${value.toFixed(0)}d`}
                      </span>
                    ) : (
                      <span style={{ fontSize: 9, color: 'var(--mu)', opacity: .5, fontStyle: 'italic', whiteSpace: 'nowrap', flexShrink: 0 }}>↳ {src}</span>
                    )}
                  </div>
                ))}
              </div>
              {financeiroContextMetrics.length > 0 && (
                <div style={{ borderTop: '1px solid var(--gb)', marginTop: 10, paddingTop: 8, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                  {financeiroContextMetrics.map((m) => (
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

        {/* SIDEBAR */}
        <div className="rcol">
          <RColResizeHandle />
          <CollapsiblePanel id="fin-contas" icon="🏦" title="Contas" action={<button className="ph-add">＋</button>}>
            <div className="dr-sec">
                {accountsQ.isLoading && <div style={{ color: 'var(--mu)', fontSize: 12 }}>Carregando…</div>}
                {accounts.map(acc => (
                  <div key={acc.id} className="acc-row">
                    <span style={{ fontSize: 13 }}>{acc.provider.includes('cartão') || acc.provider.includes('card') ? '💳' : '🏦'}</span>
                    <div className="acc-name">
                      <div style={{ fontSize: 12, fontWeight: 500 }}>{acc.account_name ?? acc.provider}</div>
                      <div style={{ fontSize: 10, color: 'var(--mu)' }}>{acc.provider}</div>
                    </div>
                    <div>
                      <div className="acc-val" style={acc.balance !== null && acc.balance < 0 ? { color: 'var(--urg)' } : undefined}>
                        {formatBRL(acc.balance)}
                      </div>
                      <div style={{ fontSize: 9.5, color: acc.status === 'active' ? 'var(--ok)' : 'var(--att)', fontFamily: 'var(--mono)' }}>
                        {acc.status === 'active' ? '↑ sincronizado' : acc.status === 'error' ? '⚠ erro' : 'desconectado'}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              {accounts.length > 0 && (
                <div className="dr-sec">
                  <div className="dr-ttl">Saldo consolidado</div>
                  <div style={{ fontSize: 18, fontWeight: 700, fontFamily: 'var(--mono)', fontVariantNumeric: 'tabular-nums', color: 'var(--fg)' }}>
                    {formatBRL(consolidatedBalance)}
                  </div>
                </div>
              )}
          </CollapsiblePanel>
          <CollapsiblePanel id="fin-pagamentos" icon="📄" title="Próximos pagamentos">
            <div className="dr-sec">
                {approvals.length === 0 && !approvalsQ.isLoading && (
                  <div style={{ color: 'var(--mu)', fontSize: 12 }}>Nenhum pagamento pendente.</div>
                )}
                {approvals.map(a => (
                  <div key={a.id} className="hi">
                    <div className="hi-n">{a.title}</div>
                    <div className="hi-m">
                      <span>{formatDate(a.created_at)}</span>
                      {(a.metadata as Record<string, unknown> | null)?.amount != null && (
                        <span className="hi-a" style={{ color: 'var(--att)' }}>
                          {formatBRL(Number((a.metadata as Record<string, unknown>).amount))}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
          </CollapsiblePanel>
        </div>

        {/* BOTTOM STRIP */}
        <div className="bstrip">
          {finInsights.length > 0 ? finInsights.slice(0, 3).map(ins => (
            <div key={ins.id} className="ich">
              <span className="ich-em">
                {ins.severity === 'error' ? '⚠️' : ins.severity === 'warning' ? '💡' : '📈'}
              </span>
              <div className="ich-body">
                <span className="ich-tag tg-f">{ins.kpi ?? 'Insight'}</span>
                <div className="ich-txt">{ins.title}</div>
              </div>
            </div>
          )) : (
            <>
              <div className="ich"><span className="ich-em">📈</span><div className="ich-body"><span className="ich-tag tg-f">Tendência</span><div className="ich-txt">Carregando insights financeiros…</div></div></div>
            </>
          )}
          <div className="nums-chip" onClick={() => setTab('tarefas')} style={{ cursor: 'pointer' }}>
            <div className="nums-head">⚙️ Rotinas ativas</div>
            <div style={{ fontSize: 11, color: 'var(--mu)' }}>Ver na aba Tarefas →</div>
          </div>
          <div className="nums-chip" onClick={() => setTab('relatorios')}>
            <div className="nums-head">📊 KPIs do mês</div>
            <div className="nums-row">
              <div className="nkpi">
                <span className="nv">{fin ? `${(fin.receita_liquida / 1000).toFixed(1)}K` : '—'}</span>
                <span className="nl">Faturamento</span>
                {fin?.receita_yoy_perc != null && (
                  <span className={`nd ${fin.receita_yoy_perc >= 0 ? 'up' : 'dn'}`}>
                    {fin.receita_yoy_perc >= 0 ? '↑' : '↓'} {Math.abs(fin.receita_yoy_perc).toFixed(1)}%
                  </span>
                )}
              </div>
              <div className="nkpi">
                <span className="nv">{fin?.margem_bruta_perc != null ? `${fin.margem_bruta_perc.toFixed(1)}%` : '—'}</span>
                <span className="nl">Margem</span>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
