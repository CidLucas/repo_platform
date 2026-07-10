/**
 * MonthlyGantt — Visão Mensal da Agenda
 *
 * 3 lanes:
 *   🔄 Rotinas   — client_routines configuradas pelo usuário (exclui infra interna)
 *   📋 Projetos  — eventos externos Monday/Notion com hierarquia expansível
 *   📅 Calendário — Google Calendar, apenas eventos de dia inteiro ou ≥ 4h
 *
 * Zoom: Semana (7d) | Mês (28d) | Trimestre (84d)
 * Navegação: anterior / próximo / hoje
 */

import { useState, useRef, useCallback } from 'react'
import type { UnifiedTask, AgendaExternalEvent } from '../../api/agenda'
import { fetchMondaySubitems } from '../../api/agenda'
import { BRAND } from '../../theme/brands'

// ─── Types ────────────────────────────────────────────────────────────────────

type ZoomMode = 'week' | 'month' | 'quarter'

interface GanttProps {
  tasks: UnifiedTask[]
  externalEvents: AgendaExternalEvent[]
  loading?: boolean
}

interface TooltipState {
  visible: boolean
  x: number
  y: number
  content: TooltipContent
}

interface TooltipContent {
  title: string
  meta: Array<{ label: string; value: string }>
}

// ─── Constants ────────────────────────────────────────────────────────────────

// IDs de rotinas internas — filtro futuro quando o shape incluir routine_id:
// morning_sync, context_report, daily_insights, end_of_day_digest,
// onboarding_complete, weekly_reengagement, morning_brief, context_sync


const ZOOM_DAYS: Record<ZoomMode, number> = {
  week: 7,
  month: 28,
  quarter: 84,
}

const ZOOM_LABELS: Record<ZoomMode, string> = {
  week: 'Semana',
  month: 'Mês',
  quarter: 'Trimestre',
}

const ROUTINE_COLORS: Record<string, string> = {
  Financeiro:  'var(--violet)',
  Compras:     'var(--violet)',
  Clientes:    'var(--violet)',
  Agenda:      'var(--violet)',
  Documentos:  'var(--violet)',
  'Estratégia':'var(--violet)',
  Geral:       'var(--violet)',
}

const SOURCE_COLORS: Record<string, string> = {
  monday: 'var(--blue2)',
  notion: 'var(--blue2)',
  asana:  BRAND.asana,
  linear: BRAND.linear,
  google: BRAND.google,
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getMondayOf(d: Date): Date {
  const day = d.getDay() || 7
  const m = new Date(d)
  m.setDate(d.getDate() - day + 1)
  m.setHours(0, 0, 0, 0)
  return m
}

function addDays(d: Date, n: number): Date {
  const r = new Date(d)
  r.setDate(r.getDate() + n)
  return r
}

function toPct(d: Date, windowStart: Date, windowDays: number): number {
  const ms = d.getTime() - windowStart.getTime()
  return Math.max(0, Math.min(100, (ms / (windowDays * 86_400_000)) * 100))
}

function fmtDay(d: Date): string {
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })
}

function fmtMonthYear(d: Date): string {
  return d.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })
}

function columnCount(zoom: ZoomMode): number {
  if (zoom === 'week')    return 7
  if (zoom === 'quarter') return 12
  return 4 // month → 4 weeks
}

function columnLabelsFn(windowStart: Date, zoom: ZoomMode): string[] {
  if (zoom === 'month') {
    return Array.from({ length: 4 }, (_, i) => {
      const s = addDays(windowStart, i * 7)
      const e = addDays(s, 6)
      return `${s.getDate()}–${e.getDate()} ${e.toLocaleString('pt-BR', { month: 'short' })}`
    })
  }
  if (zoom === 'week') {
    const days = ['Dom','Seg','Ter','Qua','Qui','Sex','Sáb']
    return Array.from({ length: 7 }, (_, i) => {
      const d = addDays(windowStart, i)
      return `${days[d.getDay()]} ${d.getDate()}`
    })
  }
  // quarter → 12 weeks
  return Array.from({ length: 12 }, (_, i) => {
    const s = addDays(windowStart, i * 7)
    return `S${i + 1} (${s.getDate()}/${s.getMonth() + 1})`
  })
}

function sourceLabel(src: string): string {
  const m: Record<string, string> = {
    monday: 'Monday',
    notion: 'Notion',
    asana: 'Asana',
    linear: 'Linear',
    google: 'Google Cal',
  }
  return m[src] ?? src
}

// ─── Bug 1: Expande rotinas cron em ocorrências periódicas dentro da janela ────
// Rotinas cron são pins pontuais (sem barra), repetidos pela frequência do cron.
// Suporta: "0 6 * * *" (diário), "0 10 * * 1" (semanal seg), "0 3 1 * *" (mensal).
function getRoutineOccurrences(routine: UnifiedTask, windowStart: Date, windowEnd: Date): Date[] {
  const anchor = new Date(routine.start_date)
  anchor.setHours(0, 0, 0, 0)

  if (!routine.schedule_cron) {
    // Sem cron: pin único na start_date se estiver na janela
    return anchor >= windowStart && anchor <= windowEnd ? [anchor] : []
  }

  // Parse simplificado de cron: "min hora dom mes dow"
  // Suportamos: dom=* (repetição por hora/dia/semana)
  const parts = routine.schedule_cron.trim().split(/\s+/)
  if (parts.length < 5) return [anchor]

  const [, , dom, , dow] = parts

  let stepDays: number
  if (dom !== '*' && dom === '1') {
    stepDays = 30  // mensal (1 * *)
  } else if (dow !== '*') {
    stepDays = 7   // semanal (específico dia da semana)
  } else {
    stepDays = 1   // diário (* * *)
  }

  const dates: Date[] = []
  // Começa pelo início da janela e avança por stepDays
  const cur = new Date(windowStart)
  cur.setHours(0, 0, 0, 0)
  // Alinha com o dia da semana se semanal
  if (stepDays === 7 && dow !== '*') {
    const targetDow = parseInt(dow, 10)
    while (cur.getDay() !== targetDow) cur.setDate(cur.getDate() + 1)
  }
  // Alinha com dia do mês se mensal
  if (stepDays === 30 && dom !== '*') {
    const targetDom = parseInt(dom, 10)
    while (cur.getDate() !== targetDom) cur.setDate(cur.getDate() + 1)
  }

  while (cur <= windowEnd) {
    if (cur >= windowStart) dates.push(new Date(cur))
    cur.setDate(cur.getDate() + stepDays)
    if (dates.length > 60) break // safety
  }
  return dates
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function LaneHeader({ title, collapsed, onToggle }: { title: string; collapsed: boolean; onToggle: () => void }) {
  return (
    <div
      onClick={onToggle}
      style={{
        display: 'flex', alignItems: 'center', gap: 6,
        padding: '8px 0 4px',
        borderTop: '1px solid var(--b)',
        marginTop: 4,
        cursor: 'pointer',
        userSelect: 'none',
      }}
    >
      <span style={{ fontSize: 9, color: 'var(--fg3)', lineHeight: 1 }}>{collapsed ? '▶' : '▼'}</span>
      <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--fg2)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        {title}
      </span>
    </div>
  )
}

function GanttRow({
  label,
  labelColor,
  indent = 0,
  barLeft,
  barWidth,
  barColor,
  barOpacity = 0.85,
  isMilestone = false,
  isEmpty = false,
  onMouseEnter,
  onMouseLeave,
}: {
  label: string
  labelColor?: string
  indent?: number
  barLeft: number
  barWidth: number
  barColor: string
  barOpacity?: number
  isMilestone?: boolean
  isEmpty?: boolean
  onMouseEnter?: (e: React.MouseEvent) => void
  onMouseLeave?: () => void
}) {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '140px 1fr',
      gap: 4,
      marginBottom: 3,
      alignItems: 'center',
    }}>
      {/* Label */}
      <div style={{
        fontSize: 11,
        color: labelColor ?? 'var(--fg2)',
        paddingLeft: 8 + indent * 10,
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
      }} title={label}>
        {label}
      </div>

      {/* Bar track */}
      <div style={{
        position: 'relative',
        height: isMilestone ? 16 : 18,
        background: 'var(--gb)',
        borderRadius: 4,
        overflow: 'visible',
      }}>
        {isEmpty ? (
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 9, color: 'var(--fg3)',
          }}>
            —
          </div>
        ) : isMilestone ? (
          // Milestone: diamond marker
          <div
            onMouseEnter={onMouseEnter}
            onMouseLeave={onMouseLeave}
            style={{
              position: 'absolute',
              left: `${barLeft}%`,
              top: '50%',
              transform: 'translate(-50%, -50%) rotate(45deg)',
              width: 10, height: 10,
              background: barColor,
              opacity: barOpacity,
              cursor: 'default',
            }}
          />
        ) : (
          <div
            onMouseEnter={onMouseEnter}
            onMouseLeave={onMouseLeave}
            style={{
              position: 'absolute',
              left: `${barLeft}%`,
              width: `${Math.max(1.5, barWidth)}%`,
              top: 2, bottom: 2,
              background: barColor,
              borderRadius: 3,
              opacity: barOpacity,
              cursor: 'default',
              overflow: 'hidden',
              fontSize: 9, color: '#fff',
              paddingLeft: 4,
              display: 'flex', alignItems: 'center',
            }}
          >
            {barWidth > 6 ? label.slice(0, 22) : ''}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── CalendarGrid — grade 2D compartilhando o mesmo timespan do Gantt ─────────
// X = mesmo toPct() do Gantt (windowStart → windowEnd)
// Y = 4 bandas: manhã-cedo (7-10), manhã (10-12), tarde (12-17), tarde-noite (17-22)
// Eventos posicionados proporcionalmente dentro das bandas pelo horário exato
// Sem labels de hora — detalhes só no hover/tooltip

const CAL_BANDS = [
  { label: 'Manhã', start: 7,  end: 12 },
  { label: 'Tarde', start: 12, end: 18 },
  { label: 'Noite', start: 18, end: 23 },
] as const

const BAND_H   = 18  // px por banda
const TOTAL_H  = CAL_BANDS.length * BAND_H  // 72px total — compacto
const ALLDAY_H = 14
const LABEL_W  = 140  // matches GanttRow label column width

function CalendarGrid({
  events,
  windowStart,
  windowEnd,
  windowDays,
  cols,
  today,
  todayPct,
  onShowTooltip,
  onHideTooltip,
}: {
  events: AgendaExternalEvent[]
  windowStart: Date
  windowEnd: Date
  windowDays: number
  cols: number
  today: Date
  todayPct: number
  onShowTooltip: (e: React.MouseEvent, c: TooltipContent) => void
  onHideTooltip: () => void
}) {
  // Separa eventos all-day de eventos com hora
  const allDayEvs = events.filter(ev => !ev.start_date.includes('T'))
  const timedEvs  = events.filter(ev =>  ev.start_date.includes('T'))

  // X: mesmo toPct do Gantt
  function widthPct(startIso: string, endIso: string | null) {
    const s = new Date(startIso)
    const e = endIso ? new Date(endIso) : new Date(s.getTime() + 60 * 60 * 1000)
    const l = toPct(s, windowStart, windowDays)
    const r = toPct(e, windowStart, windowDays)
    return { left: l, width: Math.max(0.5, r - l) }
  }

  // Y: hora → % dentro dos 72px (mapeado linearmente de 7h a 22h)
  function yAndH(startIso: string, endIso: string | null) {
    const s = new Date(startIso)
    const e = endIso ? new Date(endIso) : new Date(s.getTime() + 60 * 60 * 1000)
    const sh = s.getHours() + s.getMinutes() / 60
    const eh = e.getHours() + e.getMinutes() / 60
    const daySpan = CAL_BANDS[CAL_BANDS.length - 1].end - CAL_BANDS[0].start
    const top    = Math.max(0, Math.min(100, ((sh - CAL_BANDS[0].start) / daySpan) * 100))
    const bottom = Math.max(0, Math.min(100, ((eh - CAL_BANDS[0].start) / daySpan) * 100))
    return { top, height: Math.max(1.5, bottom - top) }
  }

  function inView(ev: AgendaExternalEvent) {
    const s = new Date(ev.start_date)
    const e = ev.due_date ? new Date(ev.due_date) : new Date(s.getTime() + 3_600_000)
    return e >= windowStart && s <= windowEnd
  }

  const fmtTime = (iso: string) =>
    new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })

  return (
    <div style={{ marginBottom: 8 }}>
      {/* All-day strip */}
      {allDayEvs.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 3 }}>
          <div style={{ width: LABEL_W, flexShrink: 0, fontSize: 9, color: 'var(--fg3)', textAlign: 'right', paddingRight: 6 }}>
            dia int.
          </div>
          <div style={{ flex: 1, position: 'relative', height: ALLDAY_H, background: 'var(--gb)', borderRadius: 3 }}>
            {Array.from({ length: cols - 1 }, (_, i) => (
              <div key={i} style={{ position: 'absolute', left: `${((i + 1) / cols) * 100}%`, top: 0, bottom: 0, width: 1, background: 'var(--b)', opacity: 0.4 }} />
            ))}
            <div style={{ position: 'absolute', left: `${todayPct}%`, top: 0, bottom: 0, width: 1, background: 'var(--att)', zIndex: 3 }} />
            {allDayEvs.filter(inView).map(ev => {
              const { left, width } = widthPct(ev.start_date, ev.due_date)
              const tip: TooltipContent = { title: ev.title, meta: [{ label: 'Dia inteiro', value: fmtDay(new Date(ev.start_date)) }] }
              return (
                <div key={ev.id} onMouseEnter={e => onShowTooltip(e, tip)} onMouseLeave={onHideTooltip}
                  style={{ position: 'absolute', left: `${left}%`, width: `${width}%`, top: 2, bottom: 2, background: BRAND.google, borderRadius: 3, opacity: 0.75, cursor: 'default', overflow: 'hidden' }}>

                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* 4-band grid */}
      <div style={{ display: 'flex' }}>
        {/* Band labels */}
        <div style={{ width: LABEL_W, flexShrink: 0, position: 'relative', height: TOTAL_H }}>
          {CAL_BANDS.map((band, i) => (
            <div key={band.label} style={{
              position: 'absolute', top: i * BAND_H, height: BAND_H,
              left: 0, right: 0, display: 'flex', alignItems: 'center', justifyContent: 'flex-start', paddingLeft: 8,
              fontSize: 11, color: 'var(--fg)', fontWeight: 700, userSelect: 'none', lineHeight: 1,
            }}>
              {band.label}
            </div>
          ))}
        </div>

        {/* Grid body */}
        <div style={{ flex: 1, position: 'relative', height: TOTAL_H, background: 'var(--gb)', borderRadius: 4, overflow: 'hidden' }}>
          {/* Horizontal band dividers */}
          {CAL_BANDS.map((_, i) => i > 0 && (
            <div key={i} style={{ position: 'absolute', top: i * BAND_H, left: 0, right: 0, height: 1, background: 'var(--b)', opacity: 0.6 }} />
          ))}
          {/* Vertical day dividers */}
          {Array.from({ length: cols - 1 }, (_, i) => (
            <div key={i} style={{ position: 'absolute', left: `${((i + 1) / cols) * 100}%`, top: 0, bottom: 0, width: 1, background: 'var(--b)', opacity: 0.4 }} />
          ))}
          {/* Today column highlight */}
          {today >= windowStart && today < windowEnd && (() => {
            const dayIdx = Math.floor((today.getTime() - windowStart.getTime()) / 86_400_000)
            const colW = 100 / windowDays
            return <div style={{ position: 'absolute', left: `${dayIdx * colW}%`, width: `${colW}%`, top: 0, bottom: 0, background: 'var(--att)', opacity: 0.05 }} />
          })()}
          {/* Today vertical line */}
          <div style={{ position: 'absolute', left: `${todayPct}%`, top: 0, bottom: 0, width: 1, background: 'var(--att)', opacity: 0.8, zIndex: 3 }} />

          {/* Timed events */}
          {timedEvs.filter(inView).map(ev => {
            const { left, width } = widthPct(ev.start_date, ev.due_date)
            const { top, height } = yAndH(ev.start_date, ev.due_date)
            const tip: TooltipContent = {
              title: ev.title,
              meta: [
                { label: 'Início', value: fmtTime(ev.start_date) },
                ...(ev.due_date ? [{ label: 'Fim', value: fmtTime(ev.due_date) }] : []),
                ...(ev.location ? [{ label: 'Local', value: ev.location }] : []),
              ],
            }
            return (
              <div key={ev.id} onMouseEnter={e => onShowTooltip(e, tip)} onMouseLeave={onHideTooltip}
                style={{
                  position: 'absolute',
                  left: `${left}%`, width: `${Math.max(0.8, width - 0.2)}%`,
                  top: `${top}%`, height: `${height}%`,
                  background: BRAND.google, borderRadius: 3, opacity: 0.8,
                  cursor: 'default', overflow: 'hidden', zIndex: 2,
                  borderLeft: '2px solid rgba(66,133,244,1)',
                  minHeight: 6,
                }}>

              </div>
            )
          })}
        </div>
      </div>

      {events.length === 0 && (
        <div style={{ fontSize: 11, color: 'var(--fg3)', paddingLeft: LABEL_W + 8, paddingTop: 4 }}>
          Sem eventos Google neste período.
        </div>
      )}
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function MonthlyGantt({ tasks, externalEvents, loading }: GanttProps) {
  const today = new Date()
  const [zoom, setZoom] = useState<ZoomMode>('month')
  const [windowStart, setWindowStart] = useState<Date>(() => getMondayOf(today))
  // Bug 2: projetos expandidos por padrão (facilita visualização em boards pequenos)
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set())
  const [laneCollapsed, setLaneCollapsed] = useState({ projetos: true, calendario: true, rotinas: true })
  const toggleLane = (lane: keyof typeof laneCollapsed) =>
    setLaneCollapsed(prev => ({ ...prev, [lane]: !prev[lane] }))
  const [tooltip, setTooltip] = useState<TooltipState>({ visible: false, x: 0, y: 0, content: { title: '', meta: [] } })
  const containerRef = useRef<HTMLDivElement>(null)

  // ── Lazy subitems state ──────────────────────────────────────────────────────
  // Map: monday_item_* → loaded subitems (or 'loading' sentinel)
  const [lazySubitems, setLazySubitems] = useState<Map<string, AgendaExternalEvent[] | 'loading'>>(new Map())

  const toggleTask = useCallback(async (taskId: string) => {
    // Toggle expand state
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(taskId)) { next.delete(taskId); return next }
      next.add(taskId); return next
    })
    // If Monday task and subitems not yet fetched, load them
    if (taskId.startsWith('monday_item_') && !lazySubitems.has(taskId)) {
      setLazySubitems(prev => new Map(prev).set(taskId, 'loading'))
      try {
        const subs = await fetchMondaySubitems(taskId)
        setLazySubitems(prev => new Map(prev).set(taskId, subs))
      } catch (err) {
        console.error('get-monday-subitems error:', err)
        setLazySubitems(prev => new Map(prev).set(taskId, []))
      }
    }
  }, [lazySubitems])

  const windowDays = ZOOM_DAYS[zoom]
  const windowEnd = addDays(windowStart, windowDays)
  const cols = columnCount(zoom)
  const colLabels = columnLabelsFn(windowStart, zoom)
  const todayPct = toPct(today, windowStart, windowDays)

  // Navigation
  function navigate(dir: -1 | 1) {
    setWindowStart(prev => addDays(prev, dir * windowDays))
  }
  function goToday() {
    setWindowStart(getMondayOf(today))
  }
  function changeZoom(z: ZoomMode) {
    setZoom(z)
    setWindowStart(getMondayOf(today))
  }

  // Tooltip helpers
  function showTooltip(e: React.MouseEvent, content: TooltipContent) {
    const rect = containerRef.current?.getBoundingClientRect()
    if (!rect) return
    setTooltip({ visible: true, x: e.clientX - rect.left + 10, y: e.clientY - rect.top - 10, content })
  }
  function hideTooltip() {
    setTooltip(prev => ({ ...prev, visible: false }))
  }

  function toggleExpand(id: string) {
    setExpanded(prev => {
      const n = new Set(prev)
      if (n.has(id)) n.delete(id)
      else n.add(id)
      return n
    })
  }

  // Compute bar position
  function bar(startIso: string, endIso: string | null) {
    const s = new Date(startIso)
    const e = endIso ? new Date(endIso) : addDays(s, 3)
    const left = toPct(s, windowStart, windowDays)
    const right = toPct(e, windowStart, windowDays)
    const width = right - left
    const inView = new Date(endIso ?? s) >= windowStart && s <= windowEnd
    return { left, width, inView }
  }

  // ── Lane 1: Rotinas (user-configured only) ─────────────────────────────────
  const routineTasks = tasks.filter(t => {
    if (t.source !== 'routine') return false
    // Extract routine_id from task_id (format: 'rtn_<uuid>' — we check by title heuristics
    // or by checking against a known internal list embedded in title patterns)
    // Best we can do without routine_id in the shape: exclude known internal titles
    const titleLower = t.title.toLowerCase()
    const internalTitles = [
      'insights diários', 'relatório de contexto', 'sincronização da manhã',
      'resumo do fim do dia', 'morning sync', 'context report', 'daily insights',
      'onboarding', 'reengajamento', 'morning brief', 'sincronização de contexto',
    ]
    return !internalTitles.some(it => titleLower.includes(it))
  })

  // ── Lane 2: Projetos — usa hierarquia real (project→phase→task) ──────────────

  // Projetos (top-level boards Monday + páginas Notion)
  const projectRoots = externalEvents.filter(
    (e) => e.source !== 'google' && (e.type === 'project' || e.type === 'page')
  )

  // Índice de filhos: parent_id → eventos filhos
  const childrenOf = new Map<string, AgendaExternalEvent[]>()
  for (const ev of externalEvents) {
    if (!ev.parent_id) continue
    if (!childrenOf.has(ev.parent_id)) childrenOf.set(ev.parent_id, [])
    childrenOf.get(ev.parent_id)!.push(ev)
  }

  // Estado de expansão: 'project' expande para mostrar phases,
  // 'phase' expande para mostrar tasks. Chave = event.id
  // (já usa o Set<string> `expanded` existente)

  // ── Lane 3: Calendário (Google Calendar only, filtered) ────────────────────
  const calEvents = externalEvents
    .filter(e => e.source === 'google')
    // Basic noise filter: skip very short title or known system events
    .filter(e => e.title.length > 2 && !e.title.toLowerCase().startsWith('busy'))
    // Limit to 8 most relevant in view
    .filter(e => {
      const s = new Date(e.start_date)
      const end = e.due_date ? new Date(e.due_date) : addDays(s, 1)
      return end >= windowStart && s <= windowEnd
    })
    .slice(0, 8)

  // ── Approval tasks (show in routines lane as approvals) ────────────────────
  const approvalTasks = tasks.filter(t => t.source === 'approval')

  // ── Capacity indicator (simple heuristic) ─────────────────────────────────
  const capacityByCol = Array.from({ length: cols }, (_, i) => {
    const colStart = addDays(windowStart, i * Math.floor(windowDays / cols))
    const colEnd = addDays(colStart, Math.floor(windowDays / cols))
    const count = [
      ...routineTasks.filter(t => {
        const s = new Date(t.start_date)
        const e = t.due_date ? new Date(t.due_date) : addDays(s, 3)
        return e >= colStart && s <= colEnd
      }),
      ...externalEvents.filter((e: AgendaExternalEvent) => {
        const s = new Date(e.start_date)
        const end = e.due_date ? new Date(e.due_date) : addDays(s, 3)
        return end >= colStart && s <= colEnd
      }),
    ].length
    return Math.min(100, (count / 5) * 100)
  })

  // ─── Render ────────────────────────────────────────────────────────────────

  return (
    <div ref={containerRef} style={{ position: 'relative', userSelect: 'none' }}>

      {/* Tooltip */}
      {tooltip.visible && (
        <div style={{
          position: 'absolute',
          left: tooltip.x, top: tooltip.y,
          background: 'var(--surface)',
          border: '1px solid var(--b)',
          borderRadius: 6,
          padding: '7px 10px',
          zIndex: 999,
          pointerEvents: 'none',
          minWidth: 160,
          maxWidth: 240,
          boxShadow: '0 4px 16px rgba(0,0,0,.35)',
        }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--fg)', marginBottom: 5 }}>
            {tooltip.content.title}
          </div>
          {tooltip.content.meta.map(m => (
            <div key={m.label} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: 10, color: 'var(--fg2)', marginBottom: 2 }}>
              <span style={{ color: 'var(--fg3)' }}>{m.label}</span>
              <span>{m.value}</span>
            </div>
          ))}
        </div>
      )}

      {/* ── Header: nav + zoom ─────────────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <button
            className="btn bs"
            style={{ fontSize: 11, padding: '2px 7px' }}
            onClick={() => navigate(-1)}
          >←</button>
          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--fg)', minWidth: 120, textAlign: 'center' }}>
            {fmtMonthYear(windowStart)}
          </span>
          <button
            className="btn bs"
            style={{ fontSize: 11, padding: '2px 7px' }}
            onClick={() => navigate(1)}
          >→</button>
          <button
            className="btn bs"
            style={{ fontSize: 10, padding: '2px 6px', marginLeft: 4, opacity: 0.7 }}
            onClick={goToday}
          >Hoje</button>
        </div>

        {/* Zoom selector */}
        <div style={{ display: 'flex', gap: 2 }}>
          {(['week', 'month', 'quarter'] as ZoomMode[]).map(z => (
            <button
              key={z}
              className="btn bs"
              style={{
                fontSize: 10,
                padding: '2px 8px',
                opacity: zoom === z ? 1 : 0.5,
                background: zoom === z ? 'var(--ac)' : undefined,
                color: zoom === z ? '#fff' : undefined,
                border: zoom === z ? '1px solid var(--ac)' : undefined,
              }}
              onClick={() => changeZoom(z)}
            >{ZOOM_LABELS[z]}</button>
          ))}
        </div>
      </div>

      {/* ── Timeline grid header ────────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '140px 1fr', gap: 4, marginBottom: 2 }}>
        <div />
        <div style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${cols}, 1fr)`,
          fontSize: 9.5, color: 'var(--fg3)',
          textAlign: 'center',
        }}>
          {colLabels.map(l => <div key={l}>{l}</div>)}
        </div>
      </div>

      {/* ── Capacity bar ─────────────────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '140px 1fr', gap: 4, marginBottom: 8 }}>
        <div style={{ fontSize: 9, color: 'var(--fg3)', textAlign: 'right', paddingRight: 8, lineHeight: '14px' }}>
          capacidade
        </div>
        <div style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${cols}, 1fr)`,
          gap: 2,
          height: 5,
        }}>
          {capacityByCol.map((pct, i) => (
            <div key={i} style={{ background: 'var(--gb)', borderRadius: 3, overflow: 'hidden' }}>
              <div style={{
                width: `${pct}%`,
                height: '100%',
                background: pct > 80 ? 'var(--urg)' : pct > 50 ? 'var(--att)' : 'var(--ok)',
                borderRadius: 3,
                transition: 'width 0.3s',
              }} />
            </div>
          ))}
        </div>
      </div>

      {loading && (
        <div style={{ fontSize: 11, color: 'var(--mu)', padding: '8px 0' }}>Carregando…</div>
      )}

      {/* ════════════════════════════════════════════════════════════════════ */}
      {/* LANE 1: PROJETOS                                                     */}
      {/* ════════════════════════════════════════════════════════════════════ */}
      <LaneHeader title="Projetos" collapsed={laneCollapsed.projetos} onToggle={() => toggleLane('projetos')} />

      {!laneCollapsed.projetos && (<>
      {projectRoots.length === 0 ? (
        <div style={{ fontSize: 11, color: 'var(--fg3)', paddingLeft: 8, paddingTop: 6, paddingBottom: 6 }}>
          Nenhum projeto conectado. Adicione Monday ou Notion nas integrações.
        </div>
      ) : null}

      {projectRoots.map(project => {
        const isProjectExpanded = expanded.has(project.id)
        const phases = childrenOf.get(project.id) ?? []
        const srcColor = SOURCE_COLORS[project.source] ?? 'var(--mu2)'

        const { left: pLeft, width: pWidth, inView: pInView } = bar(project.start_date, project.due_date)

        const projTooltip: TooltipContent = {
          title: project.title,
          meta: [
            { label: 'Fonte', value: sourceLabel(project.source) },
            { label: 'Fases', value: `${phases.length}` },
            { label: 'Início', value: fmtDay(new Date(project.start_date)) },
            ...(project.due_date ? [{ label: 'Fim', value: fmtDay(new Date(project.due_date)) }] : []),
          ],
        }

        return (
          <div key={project.id}>

            {/* ── Project row ─── */}
            <div style={{ display: 'grid', gridTemplateColumns: '140px 1fr', gap: 4, marginBottom: 3, alignItems: 'center' }}>
              <div
                onClick={() => toggleExpand(project.id)}
                style={{
                  fontSize: 11, fontWeight: 700, color: 'var(--fg)',
                  paddingLeft: 8,
                  whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                  cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
                }}
                title={project.title}
              >
                {project.title}
              </div>
              <div style={{ position: 'relative', height: 18, background: 'var(--gb)', borderRadius: 4, overflow: 'hidden' }}>
                <div style={{ position: 'absolute', left: `${todayPct}%`, top: 0, bottom: 0, width: 1, background: 'var(--att)', zIndex: 2 }} />
                {!pInView ? (
                  <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 9, color: 'var(--fg3)' }}>fora do período</div>
                ) : (
                  <div
                    onMouseEnter={e => showTooltip(e, projTooltip)}
                    onMouseLeave={hideTooltip}
                    onClick={() => toggleExpand(project.id)}
                    style={{
                      position: 'absolute',
                      left: `${pLeft}%`, width: `${Math.max(2, pWidth)}%`,
                      top: 2, bottom: 2,
                      background: srcColor, borderRadius: 3, opacity: 0.8,
                      cursor: 'pointer',
                    }}
                  >
                    {''}
                  </div>
                )}
              </div>
            </div>

            {/* ── Phases (grupos Monday) ─── */}
            {isProjectExpanded && phases.map(phase => {
              const isPhaseExpanded = expanded.has(phase.id)
              const tasks = childrenOf.get(phase.id) ?? []
              const { left: phLeft, width: phWidth, inView: phInView } = bar(phase.start_date, phase.due_date)

              const phaseTooltip: TooltipContent = {
                title: phase.title,
                meta: [
                  { label: 'Projeto', value: project.title },
                  { label: 'Tarefas', value: `${tasks.length}` },
                  { label: 'Início', value: fmtDay(new Date(phase.start_date)) },
                  ...(phase.due_date ? [{ label: 'Fim', value: fmtDay(new Date(phase.due_date)) }] : []),
                ],
              }

              return (
                <div key={phase.id}>
                  {/* Phase row */}
                  <div style={{ display: 'grid', gridTemplateColumns: '140px 1fr', gap: 4, marginBottom: 2, alignItems: 'center' }}>
                    <div
                      onClick={() => tasks.length > 0 && toggleExpand(phase.id)}
                      style={{
                        fontSize: 10, color: 'var(--fg2)',
                        paddingLeft: 18,
                        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                        cursor: tasks.length > 0 ? 'pointer' : 'default',
                        display: 'flex', alignItems: 'center', gap: 4,
                      }}
                      title={phase.title}
                    >
                      {tasks.length > 0 && (
                        <span style={{
                          fontSize: 7, color: 'var(--fg3)', display: 'inline-block',
                          transition: 'transform .15s',
                          transform: isPhaseExpanded ? 'rotate(90deg)' : 'none',
                        }}>▶</span>
                      )}
                      {phase.title}
                      {tasks.length > 0 && (
                        <span style={{ fontSize: 9, color: 'var(--fg3)', marginLeft: 2 }}>({tasks.length})</span>
                      )}
                    </div>
                    <div style={{ position: 'relative', height: 16, background: 'var(--gb)', borderRadius: 3, overflow: 'hidden' }}>
                      <div style={{ position: 'absolute', left: `${todayPct}%`, top: 0, bottom: 0, width: 1, background: 'var(--att)', zIndex: 2 }} />
                      {phInView && (
                        <div
                          onMouseEnter={e => showTooltip(e, phaseTooltip)}
                          onMouseLeave={hideTooltip}
                          onClick={() => tasks.length > 0 && toggleExpand(phase.id)}
                          style={{
                            position: 'absolute',
                            left: `${phLeft}%`, width: `${Math.max(1.5, phWidth)}%`,
                            top: 2, bottom: 2,
                            background: srcColor, borderRadius: 3, opacity: 0.5,
                            cursor: tasks.length > 0 ? 'pointer' : 'default',
                          }}
                        >
                          {''}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* ── Tasks ─── */}
                  {isPhaseExpanded && tasks.map(task => {
                    const isTaskExpanded = expanded.has(task.id)
                    // Lazy subitems: use loaded data if available, else empty
                    const lazyEntry = lazySubitems.get(task.id)
                    const subtasks: AgendaExternalEvent[] = Array.isArray(lazyEntry) ? lazyEntry : (childrenOf.get(task.id) ?? [])
                    const isLoadingSubitems = lazyEntry === 'loading'
                    const isMondayTask = task.id.startsWith('monday_item_')
                    // Monday tasks always show expand arrow (subitems unknown until fetch)
                    const hasOrMayHaveSubtasks = subtasks.length > 0 || (isMondayTask && !lazySubitems.has(task.id))
                    const { left: tLeft, width: tWidth, inView: tInView } = bar(task.start_date, task.due_date)

                    const taskTooltip: TooltipContent = {
                      title: task.title,
                      meta: [
                        { label: 'Fase', value: phase.title },
                        ...(task.location ? [{ label: 'Subfase', value: task.location }] : []),
                        ...(task.owner ? [{ label: 'Responsável', value: task.owner }] : []),
                        { label: 'Status', value: task.status || '—' },
                        ...(task.start_date ? [{ label: 'Início', value: fmtDay(new Date(task.start_date)) }] : []),
                        ...(task.due_date ? [{ label: 'Prazo', value: fmtDay(new Date(task.due_date)) }] : []),
                        ...(task.progress_pct != null ? [{ label: 'Progresso', value: `${task.progress_pct}%` }] : []),
                        ...(task.description ? [{ label: 'Descrição', value: task.description.slice(0, 80) }] : []),
                        ...(task.notes ? [{ label: 'Notas', value: task.notes.slice(0, 80) }] : []),
                      ],
                    }

                    return (
                      <div key={task.id}>
                        <div style={{ display: 'grid', gridTemplateColumns: '140px 1fr', gap: 4, marginBottom: 2, alignItems: 'center' }}>
                          <div
                            onClick={() => hasOrMayHaveSubtasks && toggleTask(task.id)}
                            style={{
                              fontSize: 10, color: 'var(--fg3)',
                              paddingLeft: 28,
                              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                              cursor: hasOrMayHaveSubtasks ? 'pointer' : 'default',
                              display: 'flex', alignItems: 'center', gap: 3,
                            }}
                            title={task.title}
                          >
                            {hasOrMayHaveSubtasks && (
                              <span style={{
                                fontSize: 7, color: 'var(--fg3)', display: 'inline-block',
                                transition: 'transform .15s',
                                transform: isTaskExpanded ? 'rotate(90deg)' : 'none',
                              }}>{isLoadingSubitems ? '⏳' : '▶'}</span>
                            )}
                            {task.title}
                            {task.owner && (
                              <span style={{
                                marginLeft: 4, fontSize: 8.5,
                                background: 'var(--gb2, rgba(255,255,255,.08))',
                                borderRadius: 3, padding: '1px 4px',
                                color: 'var(--fg3)',
                              }}>{task.owner.split(' ')[0]}</span>
                            )}
                            {subtasks.length > 0 && (
                              <span style={{ fontSize: 9, color: 'var(--fg3)' }}>({subtasks.length})</span>
                            )}
                          </div>
                          <div style={{ position: 'relative', height: 14, background: 'var(--gb)', borderRadius: 3, overflow: 'hidden' }}>
                            <div style={{ position: 'absolute', left: `${todayPct}%`, top: 0, bottom: 0, width: 1, background: 'var(--att)', zIndex: 2 }} />
                            {tInView && (
                              <div
                                onMouseEnter={e => showTooltip(e, taskTooltip)}
                                onMouseLeave={hideTooltip}
                                style={{
                                  position: 'absolute',
                                  left: `${tLeft}%`, width: `${Math.max(1.5, tWidth)}%`,
                                  top: 2, bottom: 2,
                                  background: srcColor, borderRadius: 2, opacity: 0.38,
                                  cursor: subtasks.length > 0 ? 'pointer' : 'default',
                                }}
                                onClick={() => subtasks.length > 0 && toggleTask(task.id)}
                              >
                                {task.progress_pct != null && (
                                  <div style={{
                                    position: 'absolute', left: 0, top: 0, bottom: 0,
                                    width: `${task.progress_pct}%`,
                                    background: srcColor, opacity: 0.7, borderRadius: 2,
                                  }} />
                                )}
                                {task.url && (
                                  <a
                                    href={task.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{ position: 'absolute', inset: 0 }}
                                    onClick={e => e.stopPropagation()}
                                  />
                                )}
                              </div>
                            )}
                          </div>
                        </div>

                        {/* ── Subitems (4th level) ─── */}
                        {isTaskExpanded && subtasks.map(sub => {
                          const { left: sLeft, width: sWidth, inView: sInView } = bar(sub.start_date, sub.due_date)
                          const subTooltip: TooltipContent = {
                            title: sub.title,
                            meta: [
                              { label: 'Tarefa', value: task.title },
                              ...(sub.owner ? [{ label: 'Responsável', value: sub.owner }] : []),
                              { label: 'Status', value: sub.status || '—' },
                              ...(sub.start_date ? [{ label: 'Início', value: fmtDay(new Date(sub.start_date)) }] : []),
                              ...(sub.due_date ? [{ label: 'Prazo', value: fmtDay(new Date(sub.due_date)) }] : []),
                              ...(sub.description ? [{ label: 'Descrição', value: sub.description.slice(0, 80) }] : []),
                            ],
                          }
                          return (
                            <div key={sub.id} style={{ display: 'grid', gridTemplateColumns: '140px 1fr', gap: 4, marginBottom: 2, alignItems: 'center' }}>
                              <div style={{
                                fontSize: 9.5, color: 'var(--fg3)',
                                textAlign: 'right', paddingRight: 8, paddingLeft: 30,
                                whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                                opacity: 0.8,
                              }} title={sub.title}>
                                ↳ {sub.title}
                              </div>
                              <div style={{ position: 'relative', height: 12, background: 'var(--gb)', borderRadius: 2, overflow: 'hidden' }}>
                                <div style={{ position: 'absolute', left: `${todayPct}%`, top: 0, bottom: 0, width: 1, background: 'var(--att)', zIndex: 2 }} />
                                {sInView && (
                                  <div
                                    onMouseEnter={e => showTooltip(e, subTooltip)}
                                    onMouseLeave={hideTooltip}
                                    style={{
                                      position: 'absolute',
                                      left: `${sLeft}%`, width: `${Math.max(1.5, sWidth)}%`,
                                      top: 1, bottom: 1,
                                      background: srcColor, borderRadius: 2, opacity: 0.25,
                                      cursor: 'default',
                                    }}
                                  />
                                )}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    )
                  })}
                </div>
              )
            })}
          </div>
        )
            })}
      </>)}


      {/* ════════════════════════════════════════════════════════════════════ */}
      {/* LANE 2: CALENDÁRIO — grade 2D (dias × horários)                      */}
      {/* ════════════════════════════════════════════════════════════════════ */}
      <LaneHeader title="Calendário" collapsed={laneCollapsed.calendario} onToggle={() => toggleLane('calendario')} />
      {!laneCollapsed.calendario && (
      <CalendarGrid
        events={calEvents}
        windowStart={windowStart}
        windowEnd={windowEnd}
        windowDays={windowDays}
        cols={cols}
        today={today}
        todayPct={todayPct}
        onShowTooltip={showTooltip}
        onHideTooltip={hideTooltip}
      />
      )}

      {/* LANE 3: ROTINAS                                                      */}
      {/* ════════════════════════════════════════════════════════════════════ */}
      <LaneHeader title="Rotinas" collapsed={laneCollapsed.rotinas} onToggle={() => toggleLane('rotinas')} />

      {!laneCollapsed.rotinas && (<>
      {routineTasks.length === 0 && approvalTasks.length === 0 ? (
        <div style={{ fontSize: 11, color: 'var(--fg3)', paddingLeft: 8, paddingTop: 6, paddingBottom: 6 }}>
          Nenhuma rotina configurada neste período.
        </div>
      ) : null}

      {routineTasks.map(t => {
        const color = ROUTINE_COLORS[t.domain] ?? ROUTINE_COLORS.Geral
        const occurrences = getRoutineOccurrences(t, windowStart, windowEnd)

        // Se não há ocorrências na janela, mostrar linha vazia
        if (occurrences.length === 0) {
          const tooltip_content: TooltipContent = {
            title: t.title,
            meta: [
              { label: 'Domínio', value: t.domain },
              { label: 'Status', value: t.status === 'active' ? 'Ativa' : 'Pausada' },
              { label: 'Frequência', value: t.schedule_cron ?? 'manual' },
            ],
          }
          return (
            <GanttRow
              key={t.task_id}
              label={t.title}
              barLeft={0}
              barWidth={0}
              barColor={color}
              isEmpty={true}
              onMouseEnter={e => showTooltip(e, tooltip_content)}
              onMouseLeave={hideTooltip}
            />
          )
        }

        // Renderizar com pins múltiplos no mesmo track
        const tooltip_content: TooltipContent = {
          title: t.title,
          meta: [
            { label: 'Domínio', value: t.domain },
            { label: 'Status', value: t.status === 'active' ? 'Ativa' : 'Pausada' },
            { label: 'Frequência', value: t.schedule_cron ?? 'manual' },
            { label: 'Próxima', value: fmtDay(occurrences[0]) },
            { label: 'Ocorrências', value: `${occurrences.length} no período` },
          ],
        }

        return (
          <div key={t.task_id} style={{
            display: 'grid',
            gridTemplateColumns: '140px 1fr',
            gap: 4,
            marginBottom: 3,
            alignItems: 'center',
          }}>
            {/* Label */}
            <div style={{
              fontSize: 11,
              color: 'var(--fg)',
              fontWeight: 700,
              paddingLeft: 8,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }} title={t.title}>
              {t.title}
            </div>
            {/* Track com pins múltiplos */}
            <div style={{
              position: 'relative',
              height: 18,
              background: 'var(--gb)',
              borderRadius: 4,
              overflow: 'hidden',
            }}
              onMouseEnter={e => showTooltip(e, tooltip_content)}
              onMouseLeave={hideTooltip}
            >
              {occurrences.map((date, i) => {
                const pct = toPct(date, windowStart, windowDays)
                return (
                  <div key={i} style={{
                    position: 'absolute',
                    left: `${pct}%`,
                    top: '50%',
                    transform: 'translate(-50%, -50%)',
                  }}>
                    {/* Círculo */}
                    <div style={{
                      position: 'relative',
                      width: 7,
                      height: 7,
                      borderRadius: '50%',
                      background: color,
                      opacity: t.status === 'paused' ? 0.35 : 0.9,
                      border: '1.5px solid rgba(255,255,255,0.3)',
                    }} />
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}

      {/* Approval tasks in routines lane (pending decisions) */}
      {approvalTasks.map(t => {
        const { left, width, inView } = bar(t.start_date, t.due_date)
        const tooltip_content: TooltipContent = {
          title: t.title,
          meta: [
            { label: 'Tipo', value: 'Decisão pendente' },
            { label: 'Domínio', value: t.domain },
            { label: 'Criado', value: fmtDay(new Date(t.start_date)) },
          ],
        }
        return (
          <GanttRow
            key={t.task_id}
            label={`⚡ ${t.title}`}
            labelColor="var(--att)"
            barLeft={left}
            barWidth={width}
            barColor="var(--orange)"
            barOpacity={0.9}
            isEmpty={!inView}
            onMouseEnter={e => showTooltip(e, tooltip_content)}
            onMouseLeave={hideTooltip}
          />
        )
      })}
      </>)}

      {/* ════════════════════════════════════════════════════════════════════ */}
    </div>
  )
}
