import { useState, useEffect } from 'react'
import { useQueries, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAppStore } from '../../store/appStore'
import { useAuth } from '../../hooks/useAuth'
import { useIntegrations } from '../../hooks/useAdmin'
import {
  fetchApprovalsByAgent,
  approveRequest,
  snoozeApproval,
} from '../../api/approvals'
import { fetchInsights, formatKpi } from '../../api/insights'
import {
  fetchTodaySchedule,
  fetchCalendarSettings,
  fetchAgendaHistory,
  fetchUnifiedTasks,
  fetchExternalAgendaEvents,
  connectGoogleCalendar,
  type UnifiedTask,
  type AgendaExternalEvent,
} from '../../api/agenda'
import MonthlyGantt from '../../components/agenda/MonthlyGantt'
import RColResizeHandle from '../../components/shared/RColResizeHandle'
import CollapsiblePanel from '../../components/shared/CollapsiblePanel'
import RoutineConfigSection from '../../components/shared/RoutineConfigSection'

import EmptyState from '../../components/shared/EmptyState'
import LoadingState from '../../components/shared/LoadingState'
import { snoozeUntil } from '../../utils/time'

type Tab = 'decisoes' | 'gantt' | 'hoje' | 'pendentes' | 'historico' | 'config'

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
  const { go, goWithTab, toggleDc, expandedId, addToast, openChatWith } = useAppStore()
  const { clientId } = useAuth()
  const qc = useQueryClient()
  const { data: integrations = [] } = useIntegrations()
  const [tab, setTab] = useState<Tab>('gantt')
  const [hojeExpandedId, setHojeExpandedId] = useState<string | null>(null)
  const toggleHojeDc = (id: string) => setHojeExpandedId(prev => prev === id ? null : id)

  // Invalidate after Google Calendar OAuth return
  useEffect(() => {
    if (sessionStorage.getItem('cal_oauth_done') !== '1') return
    sessionStorage.removeItem('cal_oauth_done')
    qc.invalidateQueries({ queryKey: ['calendar-settings'] })
    qc.invalidateQueries({ queryKey: ['agenda-schedule'] })
    qc.invalidateQueries({ queryKey: ['external-agenda-events'] })
  }, [qc])

  const results = useQueries({
    queries: [
      {
        queryKey: ['approvals', 'agenda', clientId ?? ''],
        queryFn: () => fetchApprovalsByAgent('agenda', clientId!),
        enabled: !!clientId,
        staleTime: 30_000,
      },
      {
        queryKey: ['insights'],
        queryFn: () => fetchInsights(10, 'agenda'),
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
      {
        queryKey: ['unified-tasks', clientId],
        queryFn: () => clientId ? fetchUnifiedTasks(clientId) : Promise.resolve([]),
        enabled: !!clientId,
        staleTime: Infinity,   // fetch once on mount, never re-fetch automatically
        gcTime: 10 * 60 * 1000,
      },
      {
        queryKey: ['external-agenda-events'],
        queryFn: () => fetchExternalAgendaEvents(84),
        enabled: !!clientId,
        staleTime: Infinity,   // fetch once on mount, never re-fetch automatically
        gcTime: 10 * 60 * 1000,
      },
    ],
  })

  const [approvalsQ, insightsQ, scheduleQ, , historyQ] = results
  const [,,,,,{ data: unifiedTasks = [] }, { data: externalEvents = [] }] = results

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
  // calSettings was removed — calendar sources now come from integrations list
  const agendaHistory = historyQ.data ?? []
  const agendaInsights = (insightsQ.data ?? []).filter(
    () => true  // room filter is server-side via p_room='agenda'
  )

  return (
    <div>
      <div className="rh">
        <div className="rav">📅</div>
        <div><div className="rn">Agenda</div><div className="rd">Reuniões, rotinas e planejamento semanal</div></div>
        <div className="ra">
          <button className="btn bs" style={{ fontSize: 11 }} onClick={() => go('home', 'Início')}>← Início</button>
          <button className="btn bp" style={{ fontSize: 11 }} onClick={() => openChatWith('Quero agendar um novo evento')}>+ Novo evento</button>
        </div>
      </div>
      <div className="room-grid">

        <div className="panel" style={{ gridColumn: 1, gridRow: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <div className="ph">
            <span className="ph-ttl">Mesa de Trabalho</span>
            <span className="ph-cnt">{todayEvents.length} eventos hoje</span>
          </div>
          <div className="rtabs" id="agTabs">
            {([['decisoes', 'Decisões'], ['gantt', 'Visão Mensal'], ['hoje', 'Hoje'], ['pendentes', 'Pendentes'], ['historico', 'Histórico'], ['config', 'Config']] as [Tab, string][]).map(([t, label]) => (
              <div key={t} className={`rtab${tab === t ? ' on' : ''}`} onClick={() => setTab(t)}>
                {t === 'decisoes' && pendingCount > 0
                  ? <>{label} <span className="tbdg">{pendingCount}</span></>
                  : t === 'pendentes' && pendingCount > 0
                  ? <>{label} <span className="tbdg">{pendingCount}</span></>
                  : label}
              </div>
            ))}
          </div>
          <div className="pb" style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>

            {/* GANTT — Visão Mensal (MonthlyGantt component) */}
            <div className={`tc${tab === 'gantt' ? ' on' : ''}`} id="ag-gantt">
              <MonthlyGantt
                tasks={unifiedTasks as UnifiedTask[]}
                externalEvents={externalEvents as AgendaExternalEvent[]}
                loading={results[5].isLoading || results[6].isLoading}
              />
            </div>

            {/* HOJE */}
            <div className={`tc${tab === 'hoje' ? ' on' : ''}`} id="ag-hoje">
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                {scheduleQ.isLoading && (
                  <LoadingState message="Carregando agenda de hoje…" />
                )}
                {!scheduleQ.isLoading && todayEvents.length === 0 && (
                  <EmptyState
                    icon="✓"
                    title="Nenhum evento hoje"
                    description="Sua agenda está livre. O Blu avisará quando houver compromissos marcados."
                  />
                )}
                {todayEvents.map(ev => {
                  const isExpanded = hojeExpandedId === ev.id
                  return (
                    <div key={ev.id} className={['dc', isExpanded ? 'expanded' : ''].filter(Boolean).join(' ')} id={ev.id}>
                      <dc-row className="dc-row" onClick={() => toggleHojeDc(ev.id)}>
                        <span className="ev-time">{formatTime(ev.start_at)}</span>
                        <div className="ev-dot" style={{ background: DOT_COLORS[ev.agenda_source] ?? '#818cf8' }} />
                        <span className="dc-row-summary">{ev.title}</span>
                        {ev.agenda_source === 'approval' && (
                          <span className="bdg bw">Pendente</span>
                        )}
                        <span className="dc-chev">▶</span>
                      </dc-row>
                      <div className="dc-expand">
                        {ev.location && <div className="db">📍 {ev.location}</div>}
                        {ev.contact && <div className="db">👤 {ev.contact}</div>}
                        {ev.observation && <div className="db">📝 {ev.observation}</div>}
                        <div className="dc-act">
                          <button className="btn bp" onClick={() => openChatWith(`Confirmar presença em ${ev.title}`)}>✓ Confirmar</button>
                          <button className="btn bg" onClick={() => openChatWith(`Remarcar reunião ${ev.title}`)}>↻ Remarcar</button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* PENDENTES */}
            <div className={`tc${tab === 'pendentes' ? ' on' : ''}`} id="ag-pendentes">
              {approvalsQ.isLoading && (
                <LoadingState message="Carregando decisões pendentes…" />
              )}
              {!approvalsQ.isLoading && approvals.length === 0 && (
                <EmptyState
                  icon="✓"
                  title="Nenhuma decisão pendente"
                  description="Tudo em dia na agenda. O Blu avisará quando houver decisões a tomar."
                />
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

            {/* HISTÓRICO */}
            <div className={`tc${tab === 'historico' ? ' on' : ''}`} id="ag-historico">
              {historyQ.isLoading && (
                <div style={{ padding: '12px 0', color: 'var(--mu)', fontSize: 12 }}>Carregando…</div>
              )}
              {!historyQ.isLoading && agendaHistory.length === 0 && (
                <div style={{ padding: '12px 0', color: 'var(--mu)', fontSize: 12 }}>Nenhuma ação no histórico.</div>
              )}
              {agendaHistory.map(h => (
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

            {/* CONFIG */}
            <div className={`tc${tab === 'config' ? ' on' : ''}`} id="ag-config">
              <RoutineConfigSection domain="agenda" />
            </div>

          </div>
        </div>

        <div className="rcol">
          <RColResizeHandle />

          <div style={{ position: "sticky", top: 0, zIndex: 10, padding: "8px 0" }}>
            <button className="btn bs" style={{ fontSize: 10, width: "100%" }} onClick={() => goWithTab("admin", "Admin", "integracoes")}>
              ＋ Adicionar integração
            </button>
          </div>

          <CollapsiblePanel id="agenda-calendarios" icon="📆" title="Calendários" action={<button className="ph-add">＋</button>}>
            <div className="dr-sec">
                <div className="dr-ttl">Hoje</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 3, marginTop: 6 }}>
                  {scheduleQ.isLoading && <LoadingState message="Carregando agenda…" />}
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
                    <EmptyState
                      icon="📆"
                      title="Sem eventos hoje"
                      description="Aproveite o dia — não há compromissos marcados."
                    />
                  )}
                </div>
              </div>
              <div className="dr-sec">
                <div className="dr-ttl">Fontes</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2, marginTop: 5 }}>
                  {(() => {
                    const CAL_PROVIDERS = new Set(['google_calendar', 'outlook_calendar', 'microsoft_calendar', 'apple_calendar'])
                    const PM_PROVIDERS  = new Set(['monday', 'notion', 'asana', 'clickup', 'linear', 'slack'])

                    // Logo SVGs
                    const ProviderLogo = ({ provider }: { provider: string }) => {
                      if (provider === 'google_calendar') return (
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                          <rect width="24" height="24" rx="3" fill="#fff"/>
                          <rect x="3" y="3" width="18" height="18" rx="2" fill="#fff" stroke="#e0e0e0" strokeWidth="1"/>
                          <rect x="3" y="3" width="18" height="5" rx="2" fill="#4285F4"/>
                          <rect x="3" y="6" width="18" height="2" fill="#4285F4"/>
                          <rect x="7" y="1.5" width="2" height="4" rx="1" fill="#4285F4"/>
                          <rect x="15" y="1.5" width="2" height="4" rx="1" fill="#4285F4"/>
                          <text x="12" y="18" textAnchor="middle" fontSize="8" fontWeight="700" fill="#4285F4">G</text>
                        </svg>
                      )
                      if (provider === 'monday') return (
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                          <circle cx="4"  cy="12" r="4" fill="#FF3D57"/>
                          <circle cx="12" cy="12" r="4" fill="#FFCB00"/>
                          <circle cx="20" cy="12" r="4" fill="#00CA72"/>
                        </svg>
                      )
                      if (provider === 'notion') return (
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                          <rect width="24" height="24" rx="3" fill="#fff" stroke="#e0e0e0"/>
                          <text x="5" y="18" fontSize="14" fontWeight="900" fill="#000">N</text>
                        </svg>
                      )
                      if (provider === 'slack') return (
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                          <path d="M6 15a2 2 0 0 1-2 2 2 2 0 0 1-2-2 2 2 0 0 1 2-2h2v2Z" fill="#E01E5A"/>
                          <path d="M7 15a2 2 0 0 1 2-2 2 2 0 0 1 2 2v5a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-5Z" fill="#E01E5A"/>
                          <path d="M9 7a2 2 0 0 1-2-2 2 2 0 0 1 2-2 2 2 0 0 1 2 2v2H9Z" fill="#36C5F0"/>
                          <path d="M9 8a2 2 0 0 1 2 2 2 2 0 0 1-2 2H4a2 2 0 0 1-2-2 2 2 0 0 1 2-2h5Z" fill="#36C5F0"/>
                          <path d="M17 10a2 2 0 0 1 2-2 2 2 0 0 1 2 2 2 2 0 0 1-2 2h-2v-2Z" fill="#2EB67D"/>
                          <path d="M16 10a2 2 0 0 1-2 2 2 2 0 0 1-2-2V5a2 2 0 0 1 2-2 2 2 0 0 1 2 2v5Z" fill="#2EB67D"/>
                          <path d="M14 18a2 2 0 0 1 2 2 2 2 0 0 1-2 2 2 2 0 0 1-2-2v-2h2Z" fill="#ECB22E"/>
                          <path d="M14 17a2 2 0 0 1-2-2 2 2 0 0 1 2-2h5a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-5Z" fill="#ECB22E"/>
                        </svg>
                      )
                      // Generic dot for others
                      const colors: Record<string, string> = { asana: '#F06A6A', clickup: '#7B68EE', linear: '#5E6AD2' }
                      return <div style={{ width: 13, height: 13, borderRadius: '50%', background: colors[provider] ?? '#818cf8', flexShrink: 0 }} />
                    }

                    const friendlyName = (i: { provider: string; name: string | null; connection_detail: string | null }) => {
                      const detail = i.connection_detail && i.connection_detail !== 'account' && i.connection_detail !== 'workspace' ? i.connection_detail : null
                      const name   = i.name && i.name !== 'account' && i.name !== 'workspace' ? i.name : null
                      if (detail) return detail
                      if (name)   return name
                      const labels: Record<string, string> = {
                        google_calendar: 'Google Calendar', google_drive: 'Google Drive',
                        monday: 'Monday.com', notion: 'Notion', asana: 'Asana',
                        clickup: 'ClickUp', linear: 'Linear', slack: 'Slack',
                        outlook_calendar: 'Outlook', microsoft_calendar: 'Microsoft Calendar',
                      }
                      return labels[i.provider] ?? i.provider
                    }

                    const allSources = integrations.filter(i =>
                      (CAL_PROVIDERS.has(i.provider) || PM_PROVIDERS.has(i.provider)) && i.status === 'connected'
                    )

                    if (allSources.length === 0) {
                      return (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                          <EmptyState
                            icon="🔌"
                            title="Nenhuma fonte conectada"
                            description="Conecte um calendário (Google, Outlook, etc.) para sincronizar seus compromissos."
                          />
                          <button className="btn bs" style={{ fontSize: 11 }} onClick={() => connectGoogleCalendar()}>
                            Conectar Google Calendar
                          </button>
                        </div>
                      )
                    }

                    return allSources.map(i => (
                      <div key={i.id} style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '3px 4px' }}>
                        <ProviderLogo provider={i.provider} />
                        <span style={{ fontSize: 11, color: 'var(--mu2)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {friendlyName(i)}
                        </span>
                        <span style={{ marginLeft: 'auto', fontSize: 9, color: 'var(--ok)' }}>●</span>
                      </div>
                    ))
                  })()}
                </div>
              </div>
          </CollapsiblePanel>
          <CollapsiblePanel id="agenda-historico" icon="🕐" title="Histórico">
            <div className="dr-sec">
                {historyQ.isLoading && <LoadingState message="Carregando histórico…" />}
                {!historyQ.isLoading && agendaHistory.length === 0 && (
                  <EmptyState
                    icon="🕐"
                    title="Nenhum histórico ainda"
                    description="Quando houver aprovações ou rejeições de agenda, elas aparecerão aqui."
                  />
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
                <span className="ich-tag tg-a">{formatKpi(ins.kpi)}</span>
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
