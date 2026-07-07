import { useState, useRef, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { useQueries, useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAppStore, type Screen } from '../../store/appStore'
import { useAuth } from '../../hooks/useAuth'
import {
  fetchPendingApprovals,
  approveRequest,
  rejectRequest,
  snoozeApproval,
} from '../../api/approvals'
import { getFinanceIndicators, getAgendaEvents, getInsights, getCommercialIndicators, type InsightItem } from '../../api/analytics'
import { connectGoogleCalendar, fetchExternalAgendaEvents } from '../../api/agenda'
import { fetchRoutines, activateRoutine, type ClientRoutine } from '../../api/routines'
import { useTracking } from '../../hooks/useTracking'
import DecisionCard from '../../components/shared/DecisionCard'
import { useApprovalStats } from '../../hooks/useApprovalStats'
import { snoozeUntil } from '../../utils/time'
import { AGENT_COLORS } from '../../utils/constants'
import RColResizeHandle from '../../components/shared/RColResizeHandle'
import CollapsiblePanel from '../../components/shared/CollapsiblePanel'

const DAY_ABBR = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']

const DOMAIN_SCREEN: Record<string, { screen: Screen; label: string }> = {
  compras: { screen: 'compras', label: 'Compras' },
  financeiro: { screen: 'financeiro', label: 'Financeiro' },
  clientes: { screen: 'clientes', label: 'Clientes' },
  documentos: { screen: 'biblioteca', label: 'Documentos' },
  estrategia: { screen: 'estrategia', label: 'Estratégia' },
  agenda: { screen: 'agenda', label: 'Agenda' },
}

function getNextWorkDays(count = 5): Date[] {
  const today = new Date()
  const days: Date[] = []
  for (let i = 0; i < count; i++) {
    const d = new Date(today)
    d.setDate(today.getDate() + i)
    days.push(d)
  }
  return days
}

function agentColor(slug: string) {
  return AGENT_COLORS[slug] ?? 'var(--mu)'
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

function routineStatusColor(status: ClientRoutine['status']): string {
  switch (status) {
    case 'active': return 'var(--teal)'
    case 'pending_approval': return 'var(--yellow)'
    default: return '#475569'
  }
}

function insightPrompts(ins: InsightItem): [string, string, string] {
  const ctx = `Insight de ${ins.room} — "${ins.title}".\n\n${ins.observation}`
  return [
    `${ctx}\n\nExplique em detalhes o que está acontecendo e o impacto no negócio.`,
    `${ctx}\n\n${ins.recommendation ? `Recomendação: ${ins.recommendation}\n\n` : ''}Quais ações concretas devo tomar agora?`,
    `${ctx}\n\nAnalise a tendência de ${ins.kpi} e projete os próximos 30 dias.`,
  ]
}

// ── Insight popover (portal, position:fixed to avoid overflow clip) ────────────
interface InsightPopoverProps {
  ins: InsightItem
  anchorRect: DOMRect
  onClose: () => void
  onPrompt: (ctx: string) => void
}

function InsightPopover({ ins, anchorRect, onClose, onPrompt }: InsightPopoverProps) {
  const prompts = insightPrompts(ins)
  const labels = ['Explique este insight', 'Como agir?', 'Analisar tendência']
  const ref = useRef<HTMLDivElement>(null)

  // position above the anchor; fall back to below if too close to top
  const popW = 240
  const popH = 130
  const spaceAbove = anchorRect.top
  const above = spaceAbove > popH + 12
  const top = above ? anchorRect.top - popH - 8 : anchorRect.bottom + 8
  const left = Math.min(
    Math.max(8, anchorRect.left + anchorRect.width / 2 - popW / 2),
    window.innerWidth - popW - 8
  )

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose()
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [onClose])

  return createPortal(
    <div
      ref={ref}
      style={{
        position: 'fixed',
        top,
        left,
        width: popW,
        zIndex: 300,
        background: 'rgba(8,13,32,0.97)',
        border: '1px solid rgba(140,95,219,0.35)',
        borderRadius: 10,
        boxShadow: 'var(--shadow-3), 0 0 0 0.5px var(--adim)',
        backdropFilter: 'blur(24px)',
        padding: '10px 10px 8px',
        animation: 'fi .12s ease-out',
      }}
    >
      <div style={{ fontSize: 10, fontWeight: 700, color: 'rgba(140,95,219,0.85)', letterSpacing: '.06em', textTransform: 'uppercase', marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>Falar com Blu sobre</span>
        <button onClick={onClose} style={{ fontSize: 13, color: 'var(--mu)', lineHeight: 1, padding: '0 2px' }}>×</button>
      </div>
      <div style={{ fontSize: 11, color: 'var(--mu2)', marginBottom: 8, lineHeight: 1.4 }}>{ins.title}</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {labels.map((label, i) => (
          <button
            key={i}
            onClick={() => { onPrompt(prompts[i]); onClose() }}
            style={{
              textAlign: 'left',
              padding: '6px 9px',
              borderRadius: 6,
              fontSize: 11,
              color: 'var(--fg)',
              background: 'rgba(140,95,219,0.10)',
              border: '1px solid rgba(140,95,219,0.20)',
              cursor: 'pointer',
              transition: 'background .1s, border-color .1s',
            }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(140,95,219,0.22)' }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(140,95,219,0.10)' }}
          >
            {label}
          </button>
        ))}
      </div>
    </div>,
    document.body
  )
}

// ── Routines bstrip chip ───────────────────────────────────────────────────────
function RoutinesHomeChip({ clientId }: { clientId: string }) {
  const { goWithTab } = useAppStore()

  const routinesQ = useQuery({
    queryKey: ['routines', 'home', clientId],
    queryFn: () => fetchRoutines(clientId),
    staleTime: 300_000,
    enabled: !!clientId,
  })

  const routines = (routinesQ.data ?? []).filter(r => r.status === 'active').slice(0, 4)

  function handleRoutineClick(r: ClientRoutine) {
    const domain = r.cross_agent_routines?.room ?? ''
    const dst = DOMAIN_SCREEN[domain] ?? { screen: 'compras' as Screen, label: 'Compras' }
    goWithTab(dst.screen, dst.label, 'config')
  }

  return (
    <div className="routines-chip">
      <div className="routines-head">⚙ Rotinas</div>
      {routinesQ.isLoading && (
        <div style={{ fontSize: 10.5, color: 'var(--mu)' }}>Carregando…</div>
      )}
      {!routinesQ.isLoading && routines.length === 0 && (
        <div style={{ fontSize: 10.5, color: 'var(--mu)' }}>Nenhuma rotina ativa</div>
      )}
      {routines.map(r => (
        <div key={r.id} className="routine-item" onClick={() => handleRoutineClick(r)}>
          <div className="routine-dot" style={{ background: routineStatusColor(r.status) }} />
          <span className="routine-name">{r.cross_agent_routines?.name ?? r.routine_id}</span>
          <span className="routine-time">{r.cross_agent_routines?.room ?? ''}</span>
        </div>
      ))}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function HomePage() {
  const { go, openChatWith, addToast } = useAppStore()
  const { clientId } = useAuth()
  const qc = useQueryClient()
  const { track } = useTracking()

  // Prefetch agenda events (Monday + Notion + Google) na Home para que
  // o AgendaRoom carregue instantaneamente do cache quando o usuário navegar.
  useEffect(() => {
    if (!clientId) return
    qc.prefetchQuery({
      queryKey: ['external-agenda-events'],
      queryFn: () => fetchExternalAgendaEvents(84),
      staleTime: 5 * 60_000, // não re-prefetch se já carregado há menos de 5min
    })
  }, [clientId, qc])

  // expand state
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null)
  const [expandedDayIdx, setExpandedDayIdx] = useState<number | null>(null)

  // insight portal state
  const [openInsightId, setOpenInsightId] = useState<string | null>(null)
  const [insightAnchor, setInsightAnchor] = useState<DOMRect | null>(null)

  const [approvalsQ, insightsQ, kpiQ, agendaQ, commercialQ, weekAgendaQ] = useQueries({
    queries: [
      {
        queryKey: ['approvals', 'all', clientId ?? ''],
        queryFn: () => fetchPendingApprovals(clientId!),
        enabled: !!clientId,
        staleTime: 30_000,
      },
      {
        queryKey: ['analytics', 'insights', 3],
        queryFn: () => getInsights(3),
        enabled: !!clientId,
        staleTime: 120_000,
      },
      {
        queryKey: ['analytics', 'financeIndicators', '30d'],
        queryFn: () => getFinanceIndicators('30d'),
        enabled: !!clientId,
        staleTime: 120_000,
      },
      {
        queryKey: ['analytics', 'agendaEvents', 1],
        queryFn: () => getAgendaEvents(1),
        enabled: !!clientId,
        staleTime: 300_000,
      },
      {
        queryKey: ['analytics', 'commercialIndicators', '30d'],
        queryFn: () => getCommercialIndicators('30d'),
        enabled: !!clientId,
        staleTime: 120_000,
      },
      {
        queryKey: ['analytics', 'agendaEvents', 7],
        queryFn: () => getAgendaEvents(7),
        enabled: !!clientId,
        staleTime: 300_000,
      },
    ],
  })

  const approvalStatsQ = useApprovalStats()

  const invalidateApprovals = () => qc.invalidateQueries({ queryKey: ['approvals'] })

  const approveMut = useMutation({
    mutationFn: (id: string) => approveRequest(id, clientId!),
    onSuccess: invalidateApprovals,
    onError: () => addToast('no', 'Erro', 'Não foi possível aprovar. Tente novamente.'),
  })
  const approveRoutineMut = useMutation({
    mutationFn: async ({ approvalId, routineId }: { approvalId: string; routineId: string }) => {
      await approveRequest(approvalId, clientId!)
      await activateRoutine(routineId, clientId!)
    },
    onSuccess: () => {
      invalidateApprovals()
      qc.invalidateQueries({ queryKey: ['active-routines'] })
    },
    onError: () => addToast('no', 'Erro', 'Não foi possível ativar a rotina.'),
  })
  const rejectMut = useMutation({
    mutationFn: (id: string) => rejectRequest(id, clientId!),
    onSuccess: invalidateApprovals,
    onError: () => addToast('no', 'Erro', 'Não foi possível rejeitar. Tente novamente.'),
  })
  const snoozeMut = useMutation({
    mutationFn: (id: string) => snoozeApproval(id, clientId!, snoozeUntil()),
    onSuccess: invalidateApprovals,
    onError: () => addToast('no', 'Erro', 'Não foi possível adiar. Tente novamente.'),
  })

  const approvals = approvalsQ.data ?? []
  const pendingCount = approvals.length
  const cntText = pendingCount === 0 ? 'Tudo resolvido ✓' : `${pendingCount} pendentes`

  const approvalStats = approvalStatsQ.data
  const trustLabel = approvalStats
    ? { manual: 'Todas manual', similar_toggle: 'Auto similar', rules: 'Regras ativas', full_config: 'Auto completo' }[approvalStats.trust_level]
    : null

  const insights = insightsQ.data ?? []
  const fin = kpiQ.data
  const commercial = commercialQ.data
  const calendarDisabled = agendaQ.data?.disabled ?? false
  const agendaEvents = calendarDisabled ? [] : (agendaQ.data?.events ?? [])
  const weekEvents = weekAgendaQ.data?.disabled ? [] : (weekAgendaQ.data?.events ?? [])
  const workDays = getNextWorkDays(5)

  const openInsight = insights.find(i => i.id === openInsightId) ?? null

  function handleIchClick(e: React.MouseEvent<HTMLDivElement>, ins: InsightItem) {
    track('insight_click', { id: ins.id, room: ins.room })
    if (openInsightId === ins.id) {
      setOpenInsightId(null)
      setInsightAnchor(null)
      return
    }
    setInsightAnchor(e.currentTarget.getBoundingClientRect())
    setOpenInsightId(ins.id)
  }

  function closeInsightPopover() {
    setOpenInsightId(null)
    setInsightAnchor(null)
  }

  return (
    <div>
      <div className="rh">
        <div className="rav">🏠</div>
        <div><div className="rn">Home</div><div className="rd">Visão geral do Blu</div></div>
        <div className="ra">
          <button className="btn bs" style={{ fontSize: 11 }} onClick={() => go('home', 'Início')}>← Início</button>
          <button className="btn bp" style={{ fontSize: 11 }} onClick={() => openChatWith('Quero criar uma nova missão')}>+ Nova Missão</button>
        </div>
      </div>
      <div className="home-grid">

      <div className="panel" style={{ gridColumn: 1, gridRow: 1 }} data-spotlight-target="decisions">
        <div className="ph">
          <span className="ph-ico">⚡</span>
          <span className="ph-ttl">Decidir Agora</span>
          <span className="ph-cnt" id="cnt">{cntText}</span>
          {trustLabel && <span className="ph-cnt" style={{ marginLeft: 6, opacity: 0.7, fontSize: 10 }}>· {trustLabel}</span>}
          <span className="ph-lnk" onClick={() => go('compras', 'Compras')}>Ver todas →</span>
        </div>
        <div className="pb">
          <div className={`dl${approvals.length === 0 ? '' : approvals.length <= 3 ? ' dl-few' : ' dl-many'}`}>
            {approvalsQ.isLoading && (
              <div style={{ padding: '12px 0', color: 'var(--mu)', fontSize: 12 }}>Carregando…</div>
            )}
            {!approvalsQ.isLoading && approvals.length === 0 && (
              <div className="empty">
                <div className="ei">✓</div>
                <div className="et">Tudo em dia</div>
                <div className="eb">Nenhuma decisão pendente no momento. O Blu irá notificá-lo quando precisar de sua atenção.</div>
              </div>
            )}
            {approvals.map(approval => (
              <DecisionCard
                key={approval.id}
                approval={approval}
                onApprove={() => {
                  const routineId = approval.payload?.client_routine_id as string | undefined
                  if (approval.action_type === 'routine_activation' && routineId) {
                    approveRoutineMut.mutate({ approvalId: approval.id, routineId })
                  } else {
                    approveMut.mutate(approval.id)
                  }
                }}
                onReject={() => rejectMut.mutate(approval.id)}
                onSnooze={() => snoozeMut.mutate(approval.id)}
              />
            ))}
          </div>
        </div>
      </div>

      <div className="rcol">
        <RColResizeHandle />
        <CollapsiblePanel id="home-plano" icon="📋" title="Plano de Hoje" badge={<span className="ph-lnk" onClick={(e) => { e.stopPropagation(); go('agenda', 'Agenda') }}>Agenda →</span>}>
            <div className="plano-list">
              {agendaQ.isLoading && (
                <div style={{ color: 'var(--mu)', fontSize: 12 }}>Carregando agenda…</div>
              )}
              {!agendaQ.isLoading && calendarDisabled && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: '4px 0' }}>
                  <div style={{ fontSize: 11.5, color: 'var(--mu)' }}>Conecte o Google Calendar para ver seus compromissos de hoje.</div>
                  <button
                    className="btn bp"
                    style={{ fontSize: 11, padding: '5px 12px', alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: 5 }}
                    onClick={() => connectGoogleCalendar()}
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>
                    Conectar Google Calendar
                  </button>
                </div>
              )}
              {agendaEvents.map(ev => {
                const isOpen = expandedEventId === ev.id
                return (
                  <div key={ev.id} className="pl-wrap">
                    <div
                      className={`pl-item${isOpen ? ' evt-open' : ''}`}
                      onClick={() => setExpandedEventId(isOpen ? null : ev.id)}
                    >
                      <span className="pl-t">
                        {formatTime(ev.startsAt)}
                      </span>
                      <div className="pl-d" style={{ background: agentColor(ev.type) }} />
                      <span className="pl-txt">{ev.title}</span>
                      <span className="pl-chev">▶</span>
                    </div>
                    <div className={`pl-detail${isOpen ? ' open' : ''}`}>
                      <div className="pl-d-title">{ev.title}</div>
                      <div className="pl-d-meta">
                        <span>🕐 {formatTime(ev.startsAt)} – {formatTime(ev.endsAt)}</span>
                        {ev.location && <span>📍 {ev.location}</span>}
                      </div>
                      {ev.attendeesCount > 0 && (
                        <div className="pl-d-participants">
                          {Array.from({ length: Math.min(ev.attendeesCount, 4) }).map((_, i) => (
                            <div key={i} className="pl-d-av">{String.fromCharCode(65 + i)}</div>
                          ))}
                          {ev.attendeesCount > 4 && (
                            <span style={{ fontSize: 10, color: 'var(--mu)', marginLeft: 2 }}>+{ev.attendeesCount - 4}</span>
                          )}
                        </div>
                      )}
                      <div className="pl-d-acts">
                        {ev.hangoutLink && (
                          <a href={ev.hangoutLink} target="_blank" rel="noopener noreferrer" className="btn bp" style={{ fontSize: 10.5, padding: '4px 9px', textDecoration: 'none' }}>
                            📹 Entrar
                          </a>
                        )}
                        <button className="btn bg" style={{ fontSize: 10.5, padding: '4px 9px' }}
                          onClick={() => openChatWith(`Reunião: ${ev.title} às ${formatTime(ev.startsAt)}. Me ajude a preparar uma pauta.`)}>
                          💬 Preparar pauta
                        </button>
                      </div>
                    </div>
                  </div>
                )
              })}
              {!agendaQ.isLoading && !calendarDisabled && agendaEvents.length === 0 && (
                <div style={{ color: 'var(--mu)', fontSize: 12 }}>Nenhum evento hoje ✓</div>
              )}
            </div>
        </CollapsiblePanel>
        <CollapsiblePanel id="home-semana" icon="🔮" title="Visão da Semana" badge={!calendarDisabled ? <span className="ph-lnk" onClick={(e) => { e.stopPropagation(); go('agenda', 'Agenda') }}>Agenda →</span> : null}>
            <div className="semana-list">
              {!calendarDisabled ? (
                workDays.map((day, i) => {
                  const isToday = i === 0
                  const isOpen = expandedDayIdx === i
                  const dayEvents = weekEvents.filter(ev => {
                    const evDate = new Date(ev.startsAt)
                    return (
                      evDate.getFullYear() === day.getFullYear() &&
                      evDate.getMonth() === day.getMonth() &&
                      evDate.getDate() === day.getDate()
                    )
                  })
                  const desc = isToday
                    ? `Hoje — ${dayEvents.length > 0 ? dayEvents.length === 1 ? dayEvents[0].title : `${dayEvents.length} eventos` : 'Sem eventos'}`
                    : dayEvents.length > 0
                      ? dayEvents.length === 1 ? dayEvents[0].title : `${dayEvents.length} eventos`
                      : 'Sem eventos'
                  const cnt = dayEvents.length > 0 ? dayEvents.length : null
                  return (
                    <div key={day.toISOString()} className="sw-wrap">
                      <div
                        className={`sw-item${isOpen ? ' sw-open' : ''}`}
                        onClick={() => setExpandedDayIdx(isOpen ? null : i)}
                        style={{ cursor: dayEvents.length > 0 ? 'pointer' : 'default' }}
                      >
                        <span className={`sw-day${isToday ? ' today' : ''}`}>{DAY_ABBR[day.getDay()]}</span>
                        <span className="sw-desc">{isToday && pendingCount > 0 ? `Hoje — ${pendingCount} pendentes` : desc}</span>
                        <span className={`sw-cnt${cnt ? ' sw-h' : ' sw-ok'}`}>
                          {isToday && pendingCount > 0 ? pendingCount : cnt ?? '—'}
                        </span>
                        {dayEvents.length > 0 && <span className="sw-chev">▶</span>}
                      </div>
                      {isOpen && dayEvents.length > 0 && (
                        <div className="sw-detail open">
                          {dayEvents.map(ev => (
                            <div key={ev.id} className="sw-ev-row">
                              <span className="sw-ev-t">{formatTime(ev.startsAt)}</span>
                              <div className="sw-ev-d" style={{ background: agentColor(ev.type) }} />
                              <span className="sw-ev-txt">{ev.title}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })
              ) : (
                <>
                  {workDays.map((day, i) => (
                    <div key={day.toISOString()} className="sw-item" style={{ opacity: 0.4 }}>
                      <span className={`sw-day${i === 0 ? ' today' : ''}`}>{DAY_ABBR[day.getDay()]}</span>
                      <span className="sw-desc">{i === 0 ? 'Hoje' : '—'}</span>
                      <span className="sw-cnt sw-ok">—</span>
                    </div>
                  ))}
                  <button
                    className="btn bp"
                    style={{ fontSize: 10.5, padding: '4px 10px', marginTop: 6, alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: 5 }}
                    onClick={() => connectGoogleCalendar()}
                  >
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>
                    Conectar Google Calendar
                  </button>
                </>
              )}
            </div>
        </CollapsiblePanel>
      </div>

      <div className="bstrip">
        {insightsQ.isLoading ? (
          [0,1,2].map(i => (
            <div key={i} className="ich" style={{ opacity: 0.4 }}>
              <span className="ich-em" style={{ background: 'var(--gb)', borderRadius: 4, color: 'transparent' }}>📈</span>
              <div className="ich-body">
                <span className="ich-tag tg-c" style={{ background: 'var(--gb)', color: 'transparent', borderRadius: 4 }}>──────</span>
                <div className="ich-txt" style={{ background: 'var(--gb)', color: 'transparent', borderRadius: 3, height: 13 }} />
              </div>
            </div>
          ))
        ) : insights.length > 0 ? insights.map(ins => (
          <div
            key={ins.id}
            className={`ich${openInsightId === ins.id ? ' ich-open' : ''}`}
            onClick={(e) => handleIchClick(e, ins)}
          >
            <span className="ich-em">
              {ins.severity === 'error' ? '⚠️' : ins.severity === 'warning' ? '💡' : '📈'}
            </span>
            <div className="ich-body">
              <span className={`ich-tag ${ins.room === 'financeiro' ? 'tg-f' : ins.room === 'compras' ? 'tg-s' : 'tg-c'}`}>
                {ins.room ?? 'Insight'}
              </span>
              <div className="ich-txt">{ins.title}</div>
            </div>
          </div>
        )) : null}
        <div className="nums-chip" onClick={() => go('financeiro', 'Financeiro')}>
          <div className="nums-head">📊 Números <span style={{ marginLeft: 'auto', opacity: 0.45 }}>→</span></div>
          <div className="nums-row">
            <div className="nkpi">
              <span className="nv">
                {fin ? `${(fin.receita_liquida / 1000).toFixed(1)}K` : '—'}
              </span>
              <span className="nl">Faturamento</span>
              {fin?.receita_yoy_perc != null && (
                <span className={`nd ${fin.receita_yoy_perc >= 0 ? 'up' : 'dn'}`}>
                  {fin.receita_yoy_perc >= 0 ? '↑' : '↓'} {Math.abs(fin.receita_yoy_perc).toFixed(1)}%
                </span>
              )}
            </div>
            <div className="nkpi">
              <span className="nv">
                {fin?.margem_bruta_perc != null ? `${fin.margem_bruta_perc.toFixed(1)}%` : '—'}
              </span>
              <span className="nl">Margem</span>
            </div>
            <div className="nkpi">
              <span className="nv">
                {commercial ? commercial.clientes_unicos : '—'}
              </span>
              <span className="nl">Clientes</span>
              {commercial && commercial.clientes_novos > 0 && (
                <span className="nd up">↑ {commercial.clientes_novos}</span>
              )}
            </div>
          </div>
        </div>
        {clientId && <RoutinesHomeChip clientId={clientId} />}
      </div>

      {openInsight && insightAnchor && (
        <InsightPopover
          ins={openInsight}
          anchorRect={insightAnchor}
          onClose={closeInsightPopover}
          onPrompt={ctx => { openChatWith(ctx); track('insight_prompt', { id: openInsight.id }) }}
        />
      )}

      </div>
    </div>
  )
}
