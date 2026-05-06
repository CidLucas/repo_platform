import { useState } from 'react'
import { cn } from '@/utils/cn'
import { usePendingApprovals } from '@/hooks/useApproval'
import { weekdayAbbr, toDateStr } from '@/utils/format'

/** Returns Mon–Fri of the current calendar week */
function getWeekDays(): Date[] {
  const today = new Date()
  const dow = today.getDay() // 0=Sun, 1=Mon … 6=Sat
  const monday = new Date(today)
  monday.setDate(today.getDate() - (dow === 0 ? 6 : dow - 1))
  return Array.from({ length: 5 }, (_, i) => {
    const d = new Date(monday)
    d.setDate(monday.getDate() + i)
    return d
  })
}

export function VisaoSemana() {
  const { data: approvals } = usePendingApprovals()
  const [openDay, setOpenDay] = useState<string | null>(null)
  const days = getWeekDays()

  // Count approvals per day (scheduled_for)
  const countByDay = (days: Date[]) => {
    const map: Record<string, { urgent: number; normal: number }> = {}
    days.forEach((d) => {
      map[toDateStr(d)] = { urgent: 0, normal: 0 }
    })
    ;(approvals ?? []).forEach((a) => {
      if (!a.scheduled_for) return
      const dateStr = a.scheduled_for.slice(0, 10)
      if (map[dateStr]) {
        if (a.priority === 'urgent') map[dateStr].urgent++
        else map[dateStr].normal++
      }
    })
    return map
  }

  const counts = countByDay(days)

  return (
    <section>
      <h2 className="font-display text-heading-lg text-white mb-3">Visão da semana</h2>

      <div className="flex gap-2">
        {days.map((d) => {
          const dateStr = toDateStr(d)
          const isToday = dateStr === toDateStr(new Date())
          const dayCount = counts[dateStr]
          const total = (dayCount?.urgent ?? 0) + (dayCount?.normal ?? 0)
          const isOpen = openDay === dateStr

          return (
            <button
              key={dateStr}
              onClick={() => setOpenDay(isOpen ? null : dateStr)}
              className={cn(
                'flex-1 rounded py-2 px-1 text-center transition-colors cursor-pointer',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500',
                isToday
                  ? 'bg-elevated border border-blu-500/40'
                  : 'bg-surface border border-border hover:border-gray-500',
                isOpen && 'border-blu-500/60'
              )}
            >
              <p
                className={cn(
                  'text-caption-sm font-medium',
                  isToday ? 'text-blu-400' : 'text-gray-300'
                )}
              >
                {weekdayAbbr(d)}
              </p>
              {total > 0 ? (
                <span
                  className={cn(
                    'inline-flex items-center justify-center mt-1',
                    'text-caption-sm font-medium rounded-full w-5 h-5 mx-auto',
                    (dayCount?.urgent ?? 0) > 0
                      ? 'bg-urgent/20 text-urgent'
                      : 'bg-attention/20 text-attention'
                  )}
                >
                  {total}
                </span>
              ) : (
                <span className="inline-block mt-1 w-1.5 h-1.5 rounded-full bg-gray-600 mx-auto" />
              )}
            </button>
          )
        })}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 mt-2 px-0.5">
        <div className="flex items-center gap-1.5">
          <span className="w-4 h-4 rounded-full bg-urgent/20 flex items-center justify-center">
            <span className="text-caption-sm text-urgent leading-none font-medium">1</span>
          </span>
          <span className="text-caption-sm text-gray-500">Urgente</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-4 h-4 rounded-full bg-attention/20 flex items-center justify-center">
            <span className="text-caption-sm text-attention leading-none font-medium">1</span>
          </span>
          <span className="text-caption-sm text-gray-500">Normal</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-gray-600 inline-block" />
          <span className="text-caption-sm text-gray-500">Sem itens</span>
        </div>
      </div>

      {/* Inline expand for selected day */}
      {openDay && (
        <div className="mt-3 animate-slide-up space-y-2">
          {(approvals ?? [])
            .filter((a) => a.scheduled_for?.startsWith(openDay))
            .map((a) => (
              <div
                key={a.id}
                className="flex items-center gap-3 py-2 border-b border-border last:border-b-0"
              >
                <span
                  className={cn(
                    'text-caption-sm px-2 py-0.5 rounded border',
                    a.priority === 'urgent'
                      ? 'text-urgent border-urgent/30 bg-urgent/10'
                      : 'text-gray-400 border-border bg-elevated'
                  )}
                >
                  {a.priority === 'urgent' ? 'Urgente' : 'Normal'}
                </span>
                <p className="text-body-sm text-gray-200 truncate">{a.title}</p>
              </div>
            ))}
          {(approvals ?? []).filter((a) => a.scheduled_for?.startsWith(openDay)).length === 0 && (
            <p className="text-caption text-gray-500 py-2">Nenhum item para este dia.</p>
          )}
        </div>
      )}
    </section>
  )
}
