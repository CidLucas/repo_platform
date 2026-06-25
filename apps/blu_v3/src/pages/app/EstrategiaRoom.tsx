import { useState, useEffect } from 'react'
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
  fetchEstrategiaHistory,
  type EstrategiaHistoryItem,
} from '../../api/estrategia'
import { getContextMetrics, type ContextMetricRow } from '../../api/analytics'
import { fetchContextReports, downloadContextReport, type ContextReport } from '../../api/contextReport'
import RColResizeHandle from '../../components/shared/RColResizeHandle'
import CollapsiblePanel from '../../components/shared/CollapsiblePanel'
import RoutineConfigSection from '../../components/shared/RoutineConfigSection'

import { snoozeUntil } from '../../utils/time'

type Tab = 'decisoes' | 'analises' | 'historico' | 'config'

// ── Lightweight markdown renderer (no external dependency) ─────────────────────────────────
function renderMarkdownLine(line: string, key: number): React.ReactNode {
  // Apply inline bold: **text**
  const parts = line.split(/(\*\*[^*]+\*\*)/g)
  const rendered = parts.map((p, i) =>
    p.startsWith('**') && p.endsWith('**')
      ? <strong key={i}>{p.slice(2, -2)}</strong>
      : p
  )
  return <span key={key}>{rendered}</span>
}

function MarkdownReport({ content }: { content: string }) {
  const lines = content.split('\n')
  const nodes: React.ReactNode[] = []
  let tableRows: string[][] = []
  let inTable = false

  const flushTable = () => {
    if (tableRows.length < 2) { tableRows = []; inTable = false; return }
    const headers = tableRows[0]
    const body = tableRows.slice(2) // skip separator row
    nodes.push(
      <div key={nodes.length} style={{ overflowX: 'auto', marginBottom: 12 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11.5 }}>
          <thead>
            <tr>
              {headers.map((h, i) => (
                <th key={i} style={{ textAlign: 'left', padding: '4px 8px', borderBottom: '1px solid var(--gb)', color: 'var(--mu)', fontWeight: 500, whiteSpace: 'nowrap' }}>
                  {h.trim()}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {body.map((row, ri) => (
              <tr key={ri}>
                {row.map((cell, ci) => (
                  <td key={ci} style={{ padding: '3px 8px', borderBottom: '1px solid var(--gb)', color: 'var(--mu2)', fontSize: 11 }}>
                    {renderMarkdownLine(cell.trim(), ci)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
    tableRows = []; inTable = false
  }

  lines.forEach((line, i) => {
    if (line.startsWith('|')) {
      inTable = true
      tableRows.push(line.split('|').slice(1, -1))
      return
    }
    if (inTable) flushTable()

    if (line.startsWith('# ')) {
      nodes.push(<div key={i} style={{ fontSize: 13, fontWeight: 600, color: 'var(--mu2)', marginBottom: 6, marginTop: 4 }}>{line.slice(2)}</div>)
    } else if (line.startsWith('## ')) {
      nodes.push(<div key={i} style={{ fontSize: 12, fontWeight: 600, color: 'var(--ac)', marginTop: 14, marginBottom: 4 }}>{line.slice(3)}</div>)
    } else if (line.startsWith('---')) {
      nodes.push(<hr key={i} style={{ border: 'none', borderTop: '1px solid var(--gb)', margin: '8px 0' }} />)
    } else if (line.startsWith('- ')) {
      nodes.push(
        <div key={i} style={{ display: 'flex', gap: 6, fontSize: 11.5, color: 'var(--mu2)', marginBottom: 4, lineHeight: 1.5 }}>
          <span style={{ color: 'var(--mu)', flexShrink: 0 }}>·</span>
          <span>{renderMarkdownLine(line.slice(2), i)}</span>
        </div>
      )
    } else if (line.startsWith('*') && line.endsWith('*') && line.length > 2) {
      nodes.push(<div key={i} style={{ fontSize: 10.5, color: 'var(--mu)', fontStyle: 'italic', marginBottom: 4 }}>{line.slice(1, -1)}</div>)
    } else if (line.trim()) {
      nodes.push(<div key={i} style={{ fontSize: 11.5, color: 'var(--mu2)', marginBottom: 3 }}>{renderMarkdownLine(line, i)}</div>)
    }
  })
  if (inTable) flushTable()

  return <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>{nodes}</div>
}

function formatCompactBRL(v: number) {
  if (v >= 1_000_000) return `R$ ${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `R$ ${(v / 1_000).toFixed(1)}k`
  return `R$ ${v.toFixed(0)}`
}

function relativeTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime()
  const d = Math.floor(diff / 86400000)
  if (d === 0) return 'hoje'
  if (d === 1) return 'ontem'
  return `${d}d atrás`
}

export default function EstrategiaRoom() {
  const { go, addToast, openChatWith } = useAppStore()
  const { clientId } = useAuth()
  const qc = useQueryClient()
  const [tab, setTab] = useState<Tab>('decisoes')
  const [analyticsOpen, setAnalyticsOpen] = useState(false)
  const [selectedReport, setSelectedReport] = useState<ContextReport | null>(null)
  const [reportContent, setReportContent] = useState<string | null>(null)
  const [loadingReport, setLoadingReport] = useState(false)

  const [approvalsQ, approvalsDocsQ, insightsQ, historyQ, contextReportsQ, contextMetricsQ] = useQueries({
    queries: [
      {
        queryKey: ['approvals', 'estrategia', clientId ?? ''],
        queryFn: () => fetchApprovalsByAgent('estrategia', clientId!),
        enabled: !!clientId,
        staleTime: 30_000,
      },
      {
        queryKey: ['approvals', 'documentos', clientId ?? ''],
        queryFn: () => fetchApprovalsByAgent('documentos', clientId!),
        enabled: !!clientId,
        staleTime: 30_000,
      },
      {
        queryKey: ['insights'],
        queryFn: () => fetchInsights(10, 'estrategia'),
        enabled: !!clientId,
        staleTime: 60_000,
      },
      {
        queryKey: ['estrategia-history', clientId ?? ''],
        queryFn: () => fetchEstrategiaHistory(clientId!),
        enabled: !!clientId,
        staleTime: 60_000,
      },
      {
        queryKey: ['contextReports'],
        queryFn: () => fetchContextReports(),
        enabled: !!clientId,
        staleTime: 5 * 60_000,
      },
      {
        queryKey: ['analytics', 'contextMetrics', clientId ?? ''],
        queryFn: () => getContextMetrics(),
        enabled: !!clientId,
        staleTime: 5 * 60_000,
      },
    ],
  })

  const approveMut = useMutation({
    mutationFn: (id: string) => approveRequest(id, clientId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['approvals', 'estrategia', clientId] })
      qc.invalidateQueries({ queryKey: ['approvals', 'documentos', clientId] })
      qc.invalidateQueries({ queryKey: ['estrategia-history', clientId] })
      addToast('ok', 'Aprovado', 'Análise aprovada.')
    },
  })

  const rejectMut = useMutation({
    mutationFn: (id: string) => rejectRequest(id, clientId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['approvals', 'estrategia', clientId] })
      qc.invalidateQueries({ queryKey: ['approvals', 'documentos', clientId] })
      addToast('no', 'Rejeitado', 'Análise rejeitada.')
    },
  })

  const snoozeMut = useMutation({
    mutationFn: (id: string) => snoozeApproval(id, clientId!, snoozeUntil()),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['approvals', 'estrategia', clientId] })
      qc.invalidateQueries({ queryKey: ['approvals', 'documentos', clientId] })
      addToast('sn', 'Adiado', 'Lembrete em 2 horas.')
    },
  })

  const approvals: ApprovalRequest[] = approvalsQ.data ?? []
  const allApprovals: ApprovalRequest[] = [...(approvalsDocsQ.data ?? []), ...(approvalsQ.data ?? [])]
  const history: EstrategiaHistoryItem[] = historyQ.data ?? []
  const insights: ClientInsight[] = (insightsQ.data ?? []).filter(
    () => true  // room filter is server-side via p_room='estrategia'
  )
  const contextReports: ContextReport[] = contextReportsQ.data ?? []
  const contextMetrics: ContextMetricRow[] = contextMetricsQ.data ?? []

  // Load report markdown when selection changes
  useEffect(() => {
    if (!selectedReport) return
    setLoadingReport(true)
    setReportContent(null)
    downloadContextReport(selectedReport.storage_path)
      .then(md => { setReportContent(md); setLoadingReport(false) })
      .catch(() => { setReportContent(null); setLoadingReport(false) })
  }, [selectedReport?.id])

  // Group context metrics by dimension for sidebar
  const estrategiaMetrics = contextMetrics.filter((m) => m.dimension === 'estrategia')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div className="rh">
        <div className="rav">🎯</div>
        <div>
          <div className="rn">Estratégia</div>
          <div className="rd">Análises, KPIs e planejamento</div>
        </div>
        <div className="ra">
          <button className="btn bs" style={{ fontSize: 11 }} onClick={() => go('home', 'Início')}>
            ← Início
          </button>
          <button className="btn bp" style={{ fontSize: 11 }} onClick={() => openChatWith('Quero criar uma nova análise estratégica')}>
            + Nova Análise
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
            {(['decisoes', 'analises', 'historico', 'config'] as Tab[]).map((t) => (
              <div
                key={t}
                className={`rtab${tab === t ? ' on' : ''}`}
                onClick={() => setTab(t)}
              >
                {t === 'decisoes' ? (
                  <>
                    Decisões{' '}
                    {!approvalsQ.isLoading && !approvalsDocsQ.isLoading && allApprovals.length > 0 && (
                      <span className="tbdg">{allApprovals.length}</span>
                    )}
                  </>
                ) : t === 'analises' ? (
                  'Análises'
                ) : t === 'historico' ? (
                  'Histórico'
                ) : (
                  'Config'
                )}
              </div>
            ))}
          </div>

          <div className="pb">
            {/* DECISÕES */}
            <div className={`tc${tab === 'decisoes' ? ' on' : ''}`}>
              {approvalsQ.isLoading || approvalsDocsQ.isLoading ? (
                <div className="dc" style={{ opacity: 0.4 }}>Carregando…</div>
              ) : allApprovals.length === 0 ? (
                <div style={{ fontSize: 12, color: 'var(--mu)', padding: '16px 0', textAlign: 'center' }}>
                  Nenhuma decisão pendente.
                </div>
              ) : (
                <div className="dl">
                  {allApprovals.map((ap) => (
                    ap.agent_slug === 'documentos' ? (
                      <ApprovalCardDocs key={ap.id} ap={ap} onSign={() => approveMut.mutate(ap.id)} onSnooze={() => snoozeMut.mutate(ap.id)} />
                    ) : (
                      <ApprovalCard
                        key={ap.id}
                        ap={ap}
                        onApprove={() => approveMut.mutate(ap.id)}
                        onReject={() => rejectMut.mutate(ap.id)}
                        onSnooze={() => snoozeMut.mutate(ap.id)}
                      />
                    )
                  ))}
                </div>
              )}
            </div>

            {/* ANÁLISES — context report viewer */}
            <div className={`tc${tab === 'analises' ? ' on' : ''}`}>
              {!selectedReport ? (
                <div style={{ fontSize: 12, color: 'var(--mu)', padding: '16px 0', textAlign: 'center' }}>
                  Selecione um relatório na coluna direita para visualizá-lo.
                </div>
              ) : loadingReport ? (
                <div style={{ fontSize: 11, color: 'var(--mu)', padding: '16px 0' }}>Carregando relatório…</div>
              ) : reportContent ? (
                <div style={{ overflowY: 'auto', maxHeight: 'calc(100% - 8px)', paddingRight: 4 }}>
                  <MarkdownReport content={reportContent} />
                </div>
              ) : (
                <div style={{ fontSize: 12, color: 'var(--urg)', padding: '16px 0', textAlign: 'center' }}>
                  Não foi possível carregar o relatório.
                </div>
              )}
            </div>

            {/* HISTÓRICO */}
            <div className={`tc${tab === 'historico' ? ' on' : ''}`}>
              {historyQ.isLoading ? (
                <div style={{ fontSize: 11, color: 'var(--mu)' }}>Carregando…</div>
              ) : history.length === 0 ? (
                <div style={{ fontSize: 12, color: 'var(--mu)', padding: '16px 0', textAlign: 'center' }}>
                  Nenhuma análise no histórico.
                </div>
              ) : (
                history.map((item) => (
                  <div key={item.id} className="hi">
                    <div className="hi-n">{item.title}</div>
                    <div className="hi-m">
                      <span>{relativeTime(item.created_at)}</span>
                      <span style={{ color: item.action === 'approved' ? 'var(--ok)' : 'var(--urg)' }}>
                        {item.action === 'approved' ? 'Aprovada' : 'Rejeitada'}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* CONFIG */}
            <div className={`tc${tab === 'config' ? ' on' : ''}`}>
              <RoutineConfigSection domain="estrategia" />
              <RoutineConfigSection domain="documentos" />
            </div>
          </div>

          {/* ANALYTICS CARD — pinned at panel bottom */}
          <div className="anl-card">
            <div className="anl-hd" onClick={() => setAnalyticsOpen(o => !o)}>
              <span className="anl-ttl">📊 Analytics Estratégia</span>
              <div className="anl-nums">
                <div className="anl-kpi">
                  <span className="anl-v">{approvalsQ.isLoading ? '…' : approvals.length}</span>
                  <span className="anl-l">Pendentes</span>
                </div>
                <div className="anl-kpi">
                  <span className="anl-v" style={{ color: 'var(--ok)' }}>{historyQ.isLoading ? '…' : history.filter((h) => h.action === 'approved').length}</span>
                  <span className="anl-l">Aprovadas</span>
                </div>
              </div>
              <span className={`anl-chev${analyticsOpen ? ' open' : ''}`}>▶</span>
            </div>
            <div className={`anl-body${analyticsOpen ? ' open' : ''}`}>
              {estrategiaMetrics.length > 0 ? (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                  {estrategiaMetrics.map((m) => (
                    <div key={m.kpi} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10.5, background: 'color-mix(in srgb,var(--fg) 5%,transparent)', border: '1px solid color-mix(in srgb,var(--fg) 10%,transparent)', borderRadius: 4, padding: '3px 6px', overflow: 'hidden' }}>
                      <span style={{ color: 'var(--mu)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', minWidth: 0, flexShrink: 1 }}>{m.label}</span>
                      {m.current_value != null && (
                        <span style={{ fontFamily: 'var(--mono)', color: 'var(--fg)', fontWeight: 600, whiteSpace: 'nowrap', flexShrink: 0 }}>
                          {m.unit === 'R$'
                            ? formatCompactBRL(m.current_value)
                            : m.unit === '%'
                            ? `${m.current_value.toFixed(1)}%`
                            : m.current_value.toLocaleString('pt-BR')}
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
              ) : (
                <div style={{ fontSize: 11, color: 'var(--mu)' }}>Disponível após a primeira sincronização.</div>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN */}
        <div className="rcol">
          <RColResizeHandle />

          <CollapsiblePanel id="est-analises" icon="📊" title="Análises" badge={contextReports.length > 0 ? <span className="ph-cnt">{contextReports.length}</span> : null}>
              {contextReportsQ.isLoading ? (
                <div style={{ fontSize: 11, color: 'var(--mu)' }}>…</div>
              ) : contextReports.length === 0 ? (
                <div style={{ fontSize: 11, color: 'var(--mu)', padding: '8px 0', textAlign: 'center', lineHeight: 1.5 }}>
                  Nenhum relatório gerado ainda.<br />
                  <span style={{ fontSize: 10 }}>Disponível após a primeira sincronização.</span>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {contextReports.map((report) => {
                    const isSelected = selectedReport?.id === report.id
                    const date = new Date(report.created_at).toLocaleDateString('pt-BR', { month: 'short', year: 'numeric' })
                    return (
                      <div
                        key={report.id}
                        onClick={() => {
                          setSelectedReport(report)
                          setTab('analises')
                        }}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 8,
                          padding: '6px 8px',
                          borderRadius: 6,
                          cursor: 'pointer',
                          background: isSelected ? 'var(--gb)' : 'transparent',
                          borderLeft: isSelected ? '2px solid var(--ac)' : '2px solid transparent',
                          transition: 'background 0.1s',
                        }}
                      >
                        <span style={{ fontSize: 14, flexShrink: 0 }}>📄</span>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 11.5, fontWeight: isSelected ? 500 : 400, color: isSelected ? 'var(--fg)' : 'var(--mu2)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {report.title}
                          </div>
                          <div style={{ fontSize: 10, color: 'var(--mu)' }}>{date}</div>
                        </div>
                        {report.status === 'pending' && (
                          <span style={{ fontSize: 9, color: 'var(--mu)', background: 'var(--gb)', padding: '1px 4px', borderRadius: 3 }}>indexando</span>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
          </CollapsiblePanel>
        </div>

        {/* BOTTOM STRIP */}
        <div className="bstrip">
          {insights.slice(0, 3).map((ins) => (
            <div key={ins.id} className="ich">
              <span className="ich-em">📈</span>
              <div className="ich-body">
                <span className="ich-tag tg-e">Estratégia</span>
                <div className="ich-txt">{ins.title}</div>
              </div>
            </div>
          ))}
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
  const priorityColor = ap.priority === 'urgent' ? '#f87171' : ap.priority === 'high' ? '#fb923c' : '#fbbf24'

  return (
    <div className={`dc warn${expanded ? ' expanded' : ''}`}>
      <div className="dc-row" onClick={() => setExpanded(!expanded)}>
        <div className="ag">
          <div className="agd" style={{ background: priorityColor }} />
          Estratégia
        </div>
        <span className="bdg bw">
          {ap.priority === 'urgent' ? 'Urgente' : ap.priority === 'high' ? 'Atenção' : 'Alerta'}
        </span>
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
            <button className="btn bp" onClick={onApprove}>👍 Aprovar</button>
            <button className="btn bs" onClick={onSnooze}>⏰ Depois</button>
            <button className="btn bg" onClick={onReject}>Ignorar</button>
          </div>
        </div>
      )}
    </div>
  )
}

function ApprovalCardDocs({ ap, onSign, onSnooze }: { ap: ApprovalRequest; onSign: () => void; onSnooze: () => void }) {
  const [expanded, setExpanded] = useState(false)
  const priorityColor = ap.priority === 'urgent' ? '#f87171' : ap.priority === 'high' ? '#fb923c' : '#fbbf24'
  return (
    <div className={`dc warn${expanded ? ' expanded' : ''}`}>
      <div className="dc-row" onClick={() => setExpanded(!expanded)}>
        <div className="ag"><div className="agd" style={{ background: priorityColor }} />Documentos</div>
        <span className="bdg bw">{ap.priority === 'urgent' ? 'Urgente' : ap.priority === 'high' ? 'Atencao' : 'Alerta'}</span>
        <span className="dc-row-summary">{ap.title}</span>
        <span className="dt">{new Date(ap.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</span>
        <span className="dc-chev">{expanded ? 'v' : '>'}</span>
      </div>
      {expanded && (
        <div className="dc-expand">
          {ap.body && <div className="db">{ap.body}</div>}
          <div className="dc-act">
            <button className="btn bp" onClick={onSign}>Assinar</button>
            <button className="btn bs" onClick={onSnooze}>Depois</button>
          </div>
        </div>
      )}
    </div>
  )
}
