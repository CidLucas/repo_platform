import { useEffect } from 'react'
import { useQueries, useQueryClient } from '@tanstack/react-query'
import { Calendar, History, Clock, MapPin, Link } from 'lucide-react'
import { DeskLayout } from '@/components/layout/DeskLayout'
import { DeskSurface } from '@/components/desk/DeskSurface'
import { Corkboard } from '@/components/corkboard/Corkboard'
import { UnderDesk } from '@/components/underdesk/UnderDesk'
import { AgentIconBox } from '@/components/primitives/AgentIconBox'
import { SkeletonCard } from '@/components/primitives/SkeletonCard'
import { EmptyDrawer } from '@/components/drawers/EmptyDrawer'
import { Badge } from '@/components/primitives/Badge'
import { Button } from '@/components/primitives/Button'

import { useAuth } from '@/hooks/useAuth'
import { fetchApprovalsByAgent } from '@/api/approvals'
import { fetchInsights } from '@/api/insights'
import {
  fetchTodaySchedule,
  fetchCalendarSettings,
  fetchAgendaHistory,
  connectGoogleCalendar,
} from '@/api/agenda'
import { fetchRoutines } from '@/api/routines'
import { ActiveRoutinesSlot } from '@/components/desk/ActiveRoutinesSlot'
import { relativeTime } from '@/utils/format'
import type { CorkboardInsight } from '@/components/corkboard/Corkboard'
import type { ClientRoutine } from '@/api/routines'

const AGENDA_ORB = {
  shape: 'triangle' as const,
  color: '#a855f7',
  glowColor: 'rgba(168,85,247,0.5)',
}

export function AgendaRoom() {
  const { clientId } = useAuth()
  const qc = useQueryClient()

  // Refresh schedule + settings after calendar OAuth return
  useEffect(() => {
    if (sessionStorage.getItem('cal_oauth_done') !== '1') return
    sessionStorage.removeItem('cal_oauth_done')
    qc.invalidateQueries({ queryKey: ['calendar-settings'] })
    qc.invalidateQueries({ queryKey: ['agenda-schedule'] })
  }, [qc])

  const [approvalsQ, insightsQ, scheduleQ, calSettingsQ, historyQ, routinesQ] = useQueries({
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
        staleTime: 30_000,
      },
      {
        queryKey: ['calendar-settings', clientId ?? ''],
        queryFn: () => fetchCalendarSettings(clientId!),
        enabled: !!clientId,
        staleTime: 300_000,
      },
      {
        queryKey: ['agenda-history', clientId ?? ''],
        queryFn: () => fetchAgendaHistory(clientId!),
        enabled: !!clientId,
        staleTime: 60_000,
      },
      {
        queryKey: ['routines', 'agenda', clientId ?? ''],
        queryFn: () => fetchRoutines(clientId!, 'agenda'),
        enabled: !!clientId,
        staleTime: 120_000,
      },
    ],
  })

  const agendaInsights: CorkboardInsight[] = (insightsQ.data ?? [])
    .filter((i) => !i.dimension || i.dimension === 'agenda')
    .map((i) => ({ id: i.id, title: i.title, body: i.observation, severity: undefined }))

  return (
      <DeskLayout
        title="Agenda"
        subtitle="Reuniões, rotinas e decisões programadas"
        agentSlug="agenda"
        agentIcon={<AgentIconBox icon={Calendar} color={AGENDA_ORB.color} />}
        accentColor={AGENDA_ORB.color}
        // ── Left drawer — Calendar + routines ────────────────
        leftTitle="Calendários"
        leftPillLabel="Calendário"
        leftPillIcon={<Calendar size={16} strokeWidth={1.5} />}
        leftContent={
          <CalendarDrawer
            settings={calSettingsQ.data ?? null}
            loading={calSettingsQ.isLoading}
            routines={routinesQ.data ?? []}
            onConnect={() => connectGoogleCalendar(window.location.href)}
          />
        }
        // ── Right drawer — Past events + decision history ────
        rightTitle="Histórico"
        rightPillLabel="Histórico"
        rightPillIcon={<History size={16} strokeWidth={1.5} />}
        rightContent={
          <AgendaHistoryDrawer
            items={historyQ.data ?? []}
            loading={historyQ.isLoading}
          />
        }
        corkboard={
          <Corkboard
            insights={agendaInsights}
            loading={insightsQ.isLoading}
            initialRows={1}
          />
        }
        underDesk={
          <UnderDesk
            agentSlug="agenda"
            routinePrefix="agenda"
            accentColor={AGENDA_ORB.color}
          />
        }
      >
        {/* ── Today's schedule strip ────────────────────────── */}
        <TodaySchedule
          events={scheduleQ.data ?? []}
          loading={scheduleQ.isLoading}
        />

        {/* ── Desk Surface — Pending approvals ─────────────── */}
        <DeskSurface
          approvals={approvalsQ.data ?? []}
          loading={approvalsQ.isLoading}
          agentName="Agenda"
          agentOrbShape={AGENDA_ORB.shape}
          agentOrbColor={AGENDA_ORB.color}
          agentOrbGlow={AGENDA_ORB.glowColor}
          tasksSlot={<ActiveRoutinesSlot routines={routinesQ.data ?? []} loading={routinesQ.isLoading} accentColor={AGENDA_ORB.color} />}
          historySlot={
            <AgendaHistoryDrawer
              items={historyQ.data ?? []}
              loading={historyQ.isLoading}
            />
          }
        />
    </DeskLayout>
  )
}

// ── Today's schedule ───────────────────────────────────────────
function TodaySchedule({
  events,
  loading,
}: {
  events: import('@/api/agenda').CalendarEvent[]
  loading: boolean
}) {
  const today = new Date().toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })

  if (loading) return <SkeletonCard lines={2} className="mb-3" />

  if (events.length === 0) {
    return (
      <div className="mb-3 bg-surface border border-border rounded-md p-4">
        <p className="text-caption text-gray-500 capitalize mb-1">{today}</p>
        <p className="text-body-sm text-gray-400">Sem eventos programados para hoje.</p>
      </div>
    )
  }

  return (
    <div className="mb-3 bg-surface border border-border rounded-md overflow-hidden shadow">
      <div className="px-4 pt-3 pb-2 border-b border-border">
        <p className="text-caption text-gray-400 capitalize">{today}</p>
        <h3 className="text-heading-sm text-white">Agenda de Hoje</h3>
      </div>
      <ul className="divide-y divide-border">
        {events.map((ev) => {
          const time = new Date(ev.start_at).toLocaleTimeString('pt-BR', {
            hour: '2-digit',
            minute: '2-digit',
          })
          return (
            <li key={ev.id} className="px-4 py-3 flex items-start gap-3 hover:bg-elevated transition-colors duration-normal">
              {/* Time pill */}
              <span className="shrink-0 text-caption-sm font-mono text-blu-400 w-10 pt-0.5">{time}</span>
              <div className="flex-1 min-w-0">
                <p className="text-body-sm text-white truncate">{ev.title}</p>
                {ev.location && (
                  <p className="text-caption-sm text-gray-400 flex items-center gap-1 mt-0.5">
                    <MapPin size={11} strokeWidth={1.5} />
                    {ev.location}
                  </p>
                )}
              </div>
              {ev.agenda_source === 'approval' && (
                <Badge variant="info">Decisão</Badge>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}

// ── Calendar drawer ────────────────────────────────────────────
function CalendarDrawer({
  settings,
  loading,
  routines,
  onConnect,
}: {
  settings: import('@/api/agenda').CalendarSettings | null
  loading: boolean
  routines: ClientRoutine[]
  onConnect: () => void
}) {
  if (loading) {
    return (
      <div className="px-4 py-3 space-y-3">
        <SkeletonCard lines={2} />
      </div>
    )
  }

  const agendaRoutines = routines.filter((r) => r.active)

  return (
    <div className="flex flex-col gap-4 p-4">
      {/* Connected calendar */}
      <div>
        <p className="text-caption-sm text-gray-500 uppercase tracking-wider mb-2">Calendário Conectado</p>
        {settings?.enabled ? (
          <div className="flex items-center gap-2 p-3 bg-elevated rounded border border-border">
            <span className="w-2 h-2 rounded-full bg-ok shrink-0" />
            <div>
              <p className="text-body-sm text-white">{settings.calendar_name ?? settings.provider}</p>
              <p className="text-caption-sm text-gray-400">{settings.provider}</p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-3 p-3 bg-elevated rounded border border-border">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-gray-500 shrink-0" />
              <p className="text-body-sm text-gray-400">Nenhum calendário conectado</p>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={onConnect}
              leftIcon={<Link size={13} strokeWidth={1.5} />}
            >
              Conectar Google Calendar
            </Button>
          </div>
        )}
      </div>

      {/* Active routines */}
      <div>
        <p className="text-caption-sm text-gray-500 uppercase tracking-wider mb-2">Rotinas Ativas</p>
        {agendaRoutines.length === 0 ? (
          <p className="text-body-sm text-gray-500">Nenhuma rotina configurada.</p>
        ) : (
          <ul className="space-y-1">
            {agendaRoutines.map((r) => {
              const label = r.routine_id.split('/').pop()?.split('_').map(
                (w) => w.charAt(0).toUpperCase() + w.slice(1)
              ).join(' ') ?? r.routine_id
              return (
                <li key={r.id} className="flex items-center gap-2 px-2 py-2 rounded hover:bg-elevated transition-colors duration-normal cursor-pointer">
                  <Clock size={13} strokeWidth={1.5} className="text-gray-500 shrink-0" />
                  <span className="text-body-sm text-gray-300">{label}</span>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}

// ── Agenda history drawer ──────────────────────────────────────
function AgendaHistoryDrawer({
  items,
  loading,
}: {
  items: import('@/api/agenda').AgendaHistoryItem[]
  loading: boolean
}) {
  if (loading) {
    return (
      <div className="px-4 py-3 space-y-3">
        {[...Array(4)].map((_, i) => <SkeletonCard key={i} lines={2} />)}
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <EmptyDrawer
        message="Nenhum histórico de decisões."
        icon={<History size={18} strokeWidth={1.5} />}
      />
    )
  }

  return (
    <ul className="divide-y divide-border">
      {items.map((item) => (
        <li key={item.id} className="px-4 py-3 flex items-start gap-3 hover:bg-elevated transition-colors duration-normal">
          <span
            className="w-2 h-2 rounded-full mt-1.5 shrink-0"
            style={{
              backgroundColor:
                item.action === 'approved' ? 'var(--ok)' :
                item.action === 'rejected' ? 'var(--urgent)' : 'var(--attention)',
            }}
          />
          <div className="flex-1 min-w-0">
            <p className="text-body-sm text-gray-200 truncate">{item.title}</p>
            <p className="text-caption-sm text-gray-500 mt-0.5">{relativeTime(item.created_at)}</p>
          </div>
        </li>
      ))}
    </ul>
  )
}

