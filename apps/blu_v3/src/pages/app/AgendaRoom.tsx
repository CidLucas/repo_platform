import { useState, useEffect } from 'react'
import { useQueries, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAppStore } from '../../store/appStore'
import { useAuth } from '../../hooks/useAuth'
import {
  fetchApprovalsByAgent,
  approveRequest,
  snoozeApproval,
} from '../../api/approvals'
import { fetchInsights } from '../../api/insights'
import {
  fetchTodaySchedule,
  fetchCalendarSettings,
  fetchAgendaHistory,
  connectGoogleCalendar,
} from '../../api/agenda'
import RColResizeHandle from '../../components/shared/RColResizeHandle'
import CollapsiblePanel from '../../components/shared/CollapsiblePanel'
import RoutinesPanel from '../../components/shared/RoutinesPanel'

type Tab = 'gantt' | 'hoje' | 'pendentes' | 'config'

function snoozeUntil() {
  return new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString()
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })
}


const DOT_COLORS: Record<string, string> = {
  approval: '#fb923c',
  calendar: '#818cf8',
}

export default function AgendaRoom() {
  const { go, toggleDc, expandedId, addToast } = useAppStore()
  const { clientId } = useAuth()
  const qc = useQueryClient()
  const [tab, setTab] = useState<Tab>('gantt')

  // Invalidate after Google Calendar OAuth return
  useEffect(() => {
    if (sessionStorage.getItem('cal_oauth_done') !== '1') return
    sessionStorage.removeItem('cal_oauth_done')
    qc.invalidateQueries({ queryKey: ['calendar-settings'] })
    qc.invalidateQueries({ queryKey: ['agenda-schedule'] })
  }, [qc])

  const [approvalsQ, insightsQ, scheduleQ, calSettingsQ, historyQ] = useQueries({
    queries: [
      {
        queryKey: ['approvals', 'agenda', clientId ?? ''],
        queryFn: () => fetchApprovalsByAgent('agenda', clientId!),
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
        queryKey: ['agenda-schedule', clientId ?? ''],
        queryFn: () => fetchTodaySchedule(clientId!),
        enabled: !!clientId,
        staleTime: 60_000,
      },
      {
        queryKey: ['calendar-settings', clientId ?? ''],
        queryFn: () => fetchCalendarSettings(clientId!),
        enabled: !!clientId,
        staleTime: 120_000,
      },
      {
        queryKey: ['agenda-history', clientId ?? ''],
        queryFn: () => fetchAgendaHistory(clientId!),
        enabled: !!clientId,
        staleTime: 60_000,
      },
    ],
  })

  const invalidateApprovals = () => qc.invalidateQueries({ queryKey: ['approvals'] })

  const approveMut = useMutation({
    mutationFn: (id: string) => approveRequest(id, clientId!),
    onSuccess: () => { invalidateApprovals(); addToast('ok', 'Aprovado', 'Blu anotou.') },
  })
  const snoozeMut = useMutation({
    mutationFn: (id: string) => snoozeApproval(id, clientId!, snoozeUntil()),
    onSuccess: () => { invalidateApprovals(); addToast('sn', 'Adiado', 'Lembrete em 2 horas.') },
  })

  const approvals = approvalsQ.data ?? []
  const pendingCount = approvals.length
  const todayEvents = scheduleQ.data ?? []
  const calSettings = calSettingsQ.data ?? null
  const agendaHistory = historyQ.data ?? []
  const agendaInsights = (insightsQ.data ?? []).filter(
    i => !i.dimension || i.dimension === 'agenda'
  )

  return (
    <div>
      <div className="rh">
        <div className="rav">📅</div>
        <div><div className="rn">Agenda</div><div className="rd">Reuniões, rotinas e planejamento semanal</div></div>
        <div className="ra">
          <button className="btn bs" style={{ fontSize: 11 }} onClick={() => go('home', 'Início')}>← Início</button>
          <button className="btn bp" style={{ fontSize: 11 }}>+ Novo evento</button>
        </div>
      </div>
      <div className="room-grid">

        <div className="panel" style={{ gridColumn: 1, gridRow: 1 }}>
          <div className="ph">
            <span className="ph-ttl">Mesa de Trabalho</span>
            <span className="ph-cnt">{todayEvents.length} eventos hoje</span>
          </div>
          <div className="rtabs" id="agTabs">
            {([['gantt', 'Visão Mensal'], ['hoje', 'Hoje'], ['pendentes', 'Pendentes'], ['config', 'Config']] as [Tab, string][]).map(([t, label]) => (
              <div key={t} className={`rtab${tab === t ? ' on' : ''}`} onClick={() => setTab(t)}>
                {t === 'pendentes' && pendingCount > 0
                  ? <>{label} <span className="tbdg">{pendingCount}</span></>
                  : label}
              </div>
            ))}
          </div>
          <div className="pb">

            {/* GANTT — static layout (no backend structure yet) */}
            <div className={`tc${tab === 'gantt' ? ' on' : ''}`} id="ag-gantt">
              <div className="gantt">
                <div className="gantt-header">
                  <div className="gantt-wk">6–12 Mai</div>
                  <div className="gantt-wk">13–19 Mai</div>
                  <div className="gantt-wk">20–26 Mai</div>
                  <div className="gantt-wk">27–5 Jun</div>
                </div>
                {[
                  { label: '🛒 Compras', blocks: [
                    { left: '0%', width: '20%', bg: '#818cf8', text: 'Cotação mensal' },
                    { left: '0%', width: '6%', bg: 'rgba(239,68,68,.7)', text: 'Toner' },
                  ]},
                  { label: '📊 Financeiro', blocks: [
                    { left: '3%', width: '4%', bg: 'var(--att)', text: 'Boleto' },
                    { left: '74%', width: '16%', bg: '#34d399', text: 'Fechamento' },
                  ]},
                  { label: '📅 Agenda', blocks: [
                    { left: '6%', width: '4%', bg: '#fb923c', text: 'NF-e' },
                    { left: '26%', width: '4%', bg: 'rgba(251,146,60,.6)', text: 'Fornec.' },
                    { left: '37%', width: '4%', bg: 'rgba(251,146,60,.6)', text: 'Fech. Qua' },
                  ]},
                  { label: '✍️ Docs', blocks: [
                    { left: '0%', width: '4%', bg: '#f472b6', text: 'Proposta Q2' },
                    { left: '0%', width: '30%', bg: 'rgba(244,114,182,.45)', text: 'Handover Alpha' },
                  ]},
                  { label: '🎯 Estratégia', blocks: [
                    { left: '0%', width: '13%', bg: '#fbbf24', text: 'Análise Y' },
                    { left: '47%', width: '22%', bg: 'rgba(251,191,36,.5)', text: 'Relatório Q2' },
                  ]},
                  { label: '👥 Clientes', blocks: [
                    { left: '0%', width: '6%', bg: '#2dd4bf', text: 'Máq. Pesada' },
                    { left: '6%', width: '4%', bg: 'rgba(45,212,191,.5)', text: 'TechFarm' },
                    { left: '50%', width: '10%', bg: 'rgba(45,212,191,.4)', text: 'Renovações' },
                  ]},
                ].map(row => (
                  <div key={row.label} className="gantt-row">
                    <div className="gantt-label">{row.label}</div>
                    <div className="gantt-track">
                      <div className="gantt-today" style={{ left: '0%' }} />
                      <div className="gantt-divider" style={{ left: '25%' }} />
                      <div className="gantt-divider" style={{ left: '50%' }} />
                      <div className="gantt-divider" style={{ left: '75%' }} />
                      {row.blocks.map((b, i) => (
                        <div key={i} className="gantt-block" style={{ left: b.left, width: b.width, background: b.bg }}>{b.text}</div>
                      ))}
                    </div>
                  </div>
                ))}
                <div style={{ marginTop: 9, display: 'flex', alignItems: 'center', gap: 10, fontSize: 10, color: 'var(--mu)' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 8, height: 2, background: 'var(--ac)', borderRadius: 1, display: 'inline-block' }} />Hoje</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 10, height: 8, background: '#818cf8', borderRadius: 2, display: 'inline-block' }} />Em andamento</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 10, height: 8, background: 'var(--att)', borderRadius: 2, display: 'inline-block' }} />Urgente</span>
                </div>
              </div>
            </div>

            {/* HOJE */}
            <div className={`tc${tab === 'hoje' ? ' on' : ''}`} id="ag-hoje">
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                {scheduleQ.isLoading && (
                  <div style={{ padding: '12px 0', color: 'var(--mu)', fontSize: 12 }}>Carregando…</div>
                )}
                {!scheduleQ.isLoading && todayEvents.length === 0 && (
                  <div style={{ padding: '12px 0', color: 'var(--mu)', fontSize: 12 }}>Nenhum evento hoje ✓</div>
                )}
                {todayEvents.map(ev => (
                  <div key={ev.id} className="ev-row">
                    <span className="ev-time">{formatTime(ev.start_at)}</span>
                    <div className="ev-dot" style={{ background: DOT_COLORS[ev.agenda_source] ?? '#818cf8' }} />
                    <div className="ev-body">
                      <div className="ev-title">{ev.title}</div>
                      {ev.location && <div className="ev-desc">{ev.location}</div>}
                    </div>
                    {ev.agenda_source === 'approval' && (
                      <span className="bdg bw" style={{ marginTop: 2 }}>Pendente</span>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* PENDENTES */}
            <div className={`tc${tab === 'pendentes' ? ' on' : ''}`} id="ag-pendentes">
              {approvalsQ.isLoading && (
                <div style={{ padding: '12px 0', color: 'var(--mu)', fontSize: 12 }}>Carregando…</div>
              )}
              {!approvalsQ.isLoading && approvals.length === 0 && (
                <div style={{ padding: '12px 0', color: 'var(--mu)', fontSize: 12 }}>Nenhuma decisão pendente ✓</div>
              )}
              {approvals.map(approval => {
                const isExpanded = expandedId === approval.id
                const cls = ['dc warn', isExpanded ? 'expanded' : ''].filter(Boolean).join(' ')
                return (
                  <div key={approval.id} className={cls} id={approval.id}>
                    <div className="dc-row" onClick={() => toggleDc(approval.id)}>
                      <div className="ag"><div className="agd" style={{ background: '#fb923c' }} />Agenda</div>
                      <span className="bdg bw">{approval.created_at ? formatTime(approval.created_at) : ''}</span>
                      <span className="dc-row-summary">{approval.title}</span>
                      <span className="dc-chev">▶</span>
                    </div>
                    <div className="dc-expand">
                      <div className="db">{approval.body}</div>
                      <div className="dc-act">
                        <button className="btn bp" onClick={() => approveMut.mutate(approval.id)}>👍 Aprovar</button>
                        <button className="btn bg" onClick={() => snoozeMut.mutate(approval.id)}>⏰ Depois</button>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>

            {/* CONFIG */}
            <div className={`tc${tab === 'config' ? ' on' : ''}`} id="ag-config">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
                <div style={{ background: 'var(--glass)', border: '1px solid var(--gb)', borderRadius: 'var(--r)', padding: '11px 12px' }}>
                  <div style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 3 }}>Planejamento semanal automático</div>
                  <div style={{ fontSize: 11, color: 'var(--mu)', marginBottom: 7 }}>Preparar agenda toda:</div>
                  <div className="pills"><span className="pill on">Segunda 07:00</span><span className="pill">Domingo 20:00</span></div>
                </div>
                <div style={{ background: 'var(--glass)', border: '1px solid var(--gb)', borderRadius: 'var(--r)', padding: '11px 12px' }}>
                  <div style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 3 }}>Lembrete diário</div>
                  <div style={{ fontSize: 11, color: 'var(--mu)', marginBottom: 7 }}>Resumo do dia às:</div>
                  <div className="pills"><span className="pill">06:30</span><span className="pill on">07:30</span><span className="pill">08:00</span></div>
                </div>
                <div style={{ marginTop: 4 }}>
                  <RoutinesPanel domain="agenda" />
                </div>
              </div>
            </div>

          </div>
        </div>

        <div className="rcol">
          <RColResizeHandle />
          <CollapsiblePanel id="agenda-calendarios" icon="📆" title="Calendários" action={<button className="ph-add">＋</button>}>
            <div className="dr-sec">
                <div className="dr-ttl">Hoje</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 3, marginTop: 6 }}>
                  {scheduleQ.isLoading && <div style={{ color: 'var(--mu)', fontSize: 12 }}>Carregando…</div>}
                  {todayEvents.map(ev => (
                    <div key={ev.id} style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '5px 5px', borderRadius: 5 }}>
                      <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--mu)', width: 34, flexShrink: 0 }}>
                        {formatTime(ev.start_at)}
                      </span>
                      <div style={{ width: 6, height: 6, borderRadius: '50%', background: DOT_COLORS[ev.agenda_source] ?? '#818cf8', flexShrink: 0 }} />
                      <span style={{ fontSize: 11, color: 'var(--mu2)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {ev.title}
                      </span>
                    </div>
                  ))}
                  {!scheduleQ.isLoading && todayEvents.length === 0 && (
                    <div style={{ fontSize: 11, color: 'var(--mu)' }}>Sem eventos hoje</div>
                  )}
                </div>
              </div>
              <div className="dr-sec">
                <div className="dr-ttl">Fontes</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2, marginTop: 5 }}>
                  {calSettings?.enabled ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '3px 4px' }}>
                      <div style={{ width: 7, height: 7, borderRadius: 2, background: '#818cf8', flexShrink: 0 }} />
                      <span style={{ fontSize: 11, color: 'var(--mu2)' }}>{calSettings.calendar_name ?? calSettings.provider ?? 'Google Calendar'}</span>
                      <span style={{ marginLeft: 'auto', fontSize: 9, color: 'var(--ok)' }}>●</span>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      <div style={{ fontSize: 11, color: 'var(--mu)' }}>Nenhum calendário conectado.</div>
                      <button
                        className="btn bs"
                        style={{ fontSize: 11 }}
                        onClick={() => connectGoogleCalendar(window.location.href)}
                      >
                        Conectar Google Calendar
                      </button>
                    </div>
                  )}
                </div>
              </div>
          </CollapsiblePanel>
          <CollapsiblePanel id="agenda-historico" icon="🕐" title="Histórico">
            <div className="dr-sec">
                {historyQ.isLoading && <div style={{ color: 'var(--mu)', fontSize: 12 }}>Carregando…</div>}
                {!historyQ.isLoading && agendaHistory.length === 0 && (
                  <div style={{ fontSize: 12, color: 'var(--mu)' }}>Nenhum histórico ainda.</div>
                )}
                {agendaHistory.slice(0, 5).map(h => (
                  <div key={h.id} className="hi">
                    <div className="hi-n">{h.title}</div>
                    <div className="hi-m">
                      <span>{formatDate(h.created_at)}</span>
                      <span style={{ color: h.action === 'approved' ? 'var(--ok)' : 'var(--att)' }}>
                        {h.action === 'approved' ? 'Aprovado' : 'Rejeitado'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
          </CollapsiblePanel>
        </div>

        <div className="bstrip">
          {agendaInsights.length > 0 ? agendaInsights.slice(0, 3).map(ins => (
            <div key={ins.id} className="ich">
              <span className="ich-em">
                {ins.severity === 'error' ? '⚠️' : ins.severity === 'warning' ? '🤝' : '📅'}
              </span>
              <div className="ich-body">
                <span className="ich-tag tg-a">{ins.kpi ?? 'Agenda'}</span>
                <div className="ich-txt">{ins.title}</div>
              </div>
            </div>
          )) : (
            <div className="ich"><span className="ich-em">📅</span><div className="ich-body"><span className="ich-tag tg-a">Agenda</span><div className="ich-txt">Carregando insights da agenda…</div></div></div>
          )}
          <div className="nums-chip" onClick={() => setTab('config')} style={{ cursor: 'pointer' }}>
            <div className="nums-head">⚙️ Rotinas ativas</div>
            <div style={{ fontSize: 11, color: 'var(--mu)' }}>Ver na aba Config →</div>
          </div>
        </div>

      </div>
    </div>
  )
}
