import { useQueries, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAppStore } from '../../store/appStore'
import { useAuth } from '../../hooks/useAuth'
import {
  fetchPendingApprovals,
  approveRequest,
  rejectRequest,
  snoozeApproval,
  type ApprovalRequest,
} from '../../api/approvals'
import { getFinanceIndicators, getAgendaEvents, getInsights, getCommercialIndicators } from '../../api/analytics'
import { connectGoogleCalendar } from '../../api/agenda'
import { useTracking } from '../../hooks/useTracking'
import RColResizeHandle from '../../components/shared/RColResizeHandle'
import CollapsiblePanel from '../../components/shared/CollapsiblePanel'

const AGENT_COLORS: Record<string, string> = {
  compras: '#818cf8',
  financeiro: '#34d399',
  clientes: '#f472b6',
  estoque: '#fbbf24',
  documentos: '#2dd4bf',
}

const DAY_ABBR = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']

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
  return AGENT_COLORS[slug] ?? '#94a3b8'
}

function agentLabel(slug: string) {
  return slug.charAt(0).toUpperCase() + slug.slice(1)
}

function priorityBadge(priority: ApprovalRequest['priority']): { cls: string; label: string } {
  switch (priority) {
    case 'urgent': return { cls: 'bdg bu', label: 'Urgente' }
    case 'high':   return { cls: 'bdg bu', label: 'Alto' }
    case 'medium': return { cls: 'bdg bw', label: 'Médio' }
    default:       return { cls: 'bdg bw', label: 'Normal' }
  }
}

function dcClass(priority: ApprovalRequest['priority']) {
  return priority === 'urgent' || priority === 'high' ? 'urg' : 'warn'
}

function snoozeUntil() {
  return new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString()
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

function DecisionCard({
  approval,
  onApprove,
  onReject,
  onSnooze,
}: {
  approval: ApprovalRequest
  onApprove: () => void
  onReject: () => void
  onSnooze: () => void
}) {
  const { expandedId, toggleDc, addToast } = useAppStore()
  const isExpanded = expandedId === approval.id
  const badge = priorityBadge(approval.priority)
  const cls = ['dc', dcClass(approval.priority), isExpanded ? 'expanded' : ''].filter(Boolean).join(' ')

  function handleApprove() {
    onApprove()
    addToast('ok', 'Aprovado', approval.title)
  }
  function handleReject() {
    onReject()
    addToast('no', 'Rejeitado', 'Blu anotou. Não vou sugerir novamente.')
  }
  function handleSnooze() {
    onSnooze()
    addToast('sn', 'Adiado', 'Lembrete em 2 horas.')
  }

  return (
    <div className={cls} id={approval.id}>
      <div className="dc-row" onClick={() => toggleDc(approval.id)}>
        <div className="ag">
          <div className="agd" style={{ background: agentColor(approval.agent_slug) }} />
          {agentLabel(approval.agent_slug)}
        </div>
        <span className={badge.cls}>{badge.label}</span>
        <span className="dc-row-summary">{approval.title}</span>
        <span className="dt">{formatTime(approval.created_at)}</span>
        <span className="dc-chev">▶</span>
      </div>
      <div className="dc-expand">
        <div className="db">{approval.body}</div>
        <div className="dc-act">
          <button className="btn bp" onClick={handleApprove}>👍 Aprovar</button>
          <button className="btn bg" onClick={handleSnooze}>⏰ Depois</button>
          <button className="btn bs" onClick={handleReject}>✗ Rejeitar</button>
        </div>
      </div>
    </div>
  )
}

export default function HomePage() {
  const { go } = useAppStore()
  const { clientId } = useAuth()
  const qc = useQueryClient()
  const { track } = useTracking()

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

  const invalidateApprovals = () => qc.invalidateQueries({ queryKey: ['approvals'] })

  const approveMut = useMutation({
    mutationFn: (id: string) => approveRequest(id, clientId!),
    onSuccess: invalidateApprovals,
  })
  const rejectMut = useMutation({
    mutationFn: (id: string) => rejectRequest(id, clientId!),
    onSuccess: invalidateApprovals,
  })
  const snoozeMut = useMutation({
    mutationFn: (id: string) => snoozeApproval(id, clientId!, snoozeUntil()),
    onSuccess: invalidateApprovals,
  })

  const approvals = approvalsQ.data ?? []
  const pendingCount = approvals.length
  const cntText = pendingCount === 0 ? 'Tudo resolvido ✓' : `${pendingCount} pendentes`

  const insights = insightsQ.data ?? []
  const fin = kpiQ.data
  const commercial = commercialQ.data
  const calendarDisabled = agendaQ.data?.disabled ?? false
  const agendaEvents = calendarDisabled ? [] : (agendaQ.data?.events ?? [])
  const weekEvents = weekAgendaQ.data?.disabled ? [] : (weekAgendaQ.data?.events ?? [])
  const workDays = getNextWorkDays(5)

  return (
    <div className="home-grid">

      <div className="panel" style={{ gridColumn: 1, gridRow: 1 }}>
        <div className="ph">
          <span className="ph-ico">⚡</span>
          <span className="ph-ttl">Decidir Agora</span>
          <span className="ph-cnt" id="cnt">{cntText}</span>
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
                onApprove={() => approveMut.mutate(approval.id)}
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
                    onClick={() => connectGoogleCalendar(window.location.href)}
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>
                    Conectar Google Calendar
                  </button>
                </div>
              )}
              {agendaEvents.map(ev => (
                <div key={ev.id} className="pl-item">
                  <span className="pl-t">
                    {new Date(ev.startsAt).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                  </span>
                  <div className="pl-d" style={{ background: agentColor(ev.type) }} />
                  <span className="pl-txt">{ev.title}</span>
                </div>
              ))}
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
                    <div key={day.toISOString()} className="sw-item">
                      <span className={`sw-day${isToday ? ' today' : ''}`}>{DAY_ABBR[day.getDay()]}</span>
                      <span className="sw-desc">{isToday && pendingCount > 0 ? `Hoje — ${pendingCount} pendentes` : desc}</span>
                      <span className={`sw-cnt${cnt ? ' sw-h' : ' sw-ok'}`}>
                        {isToday && pendingCount > 0 ? pendingCount : cnt ?? '—'}
                      </span>
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
                    onClick={() => connectGoogleCalendar(window.location.href)}
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
        {insights.length > 0 ? insights.map(ins => (
          <div key={ins.id} className="ich" onClick={() => track('insight_click', { id: ins.id, dimension: ins.dimension })}>
            <span className="ich-em">
              {ins.severity === 'error' ? '⚠️' : ins.severity === 'warning' ? '💡' : '📈'}
            </span>
            <div className="ich-body">
              <span className={`ich-tag ${ins.dimension === 'finance' ? 'tg-f' : ins.dimension === 'supply' ? 'tg-s' : 'tg-c'}`}>
                {ins.dimension ?? 'Insight'}
              </span>
              <div className="ich-txt">{ins.title}</div>
            </div>
          </div>
        )) : (
          <>
            <div className="ich"><span className="ich-em">📈</span><div className="ich-body"><span className="ich-tag tg-c">Clientes</span><div className="ich-txt">Carregando insights…</div></div></div>
          </>
        )}
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
      </div>

    </div>
  )
}
