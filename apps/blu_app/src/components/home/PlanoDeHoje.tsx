import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronDown, ChevronUp, Plus } from 'lucide-react'
import { cn } from '@/utils/cn'
import { usePendingApprovals } from '@/hooks/useApproval'
import { AGENT_MAP } from '@/utils/constants'
import { formatTime } from '@/utils/format'

/** Shows time-ordered items for today: scheduled_for approvals */
export function PlanoDeHoje() {
  const { data: approvals } = usePendingApprovals()
  const navigate = useNavigate()
  const [expanded, setExpanded] = useState(false)

  const today = new Date().toISOString().slice(0, 10)

  const todayItems = (approvals ?? [])
    .filter((a) => a.scheduled_for?.startsWith(today))
    .sort((a, b) =>
      (a.scheduled_for ?? '').localeCompare(b.scheduled_for ?? '')
    )

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-display text-heading-lg text-white">Plano de hoje</h2>
        {todayItems.length > 3 && (
          <button
            onClick={() => setExpanded((v) => !v)}
            className="text-caption text-gray-400 hover:text-white flex items-center gap-1 cursor-pointer transition-colors"
            aria-label={expanded ? 'Recolher' : 'Ver mais'}
          >
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            {expanded ? 'Menos' : 'Ver mais'}
          </button>
        )}
      </div>

      {todayItems.length === 0 ? (
        <div className="text-center py-3">
          <p className="text-caption text-gray-400 mb-3">Nenhum item agendado para hoje.</p>
          <button
            onClick={() => navigate('/agenda')}
            className={cn(
              'inline-flex items-center gap-1.5 px-3 py-1.5 rounded',
              'text-body-sm text-blu-400 hover:text-blu-300 border border-blu-500/30',
              'hover:bg-blu-500/10 transition-colors cursor-pointer',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500'
            )}
          >
            <Plus size={13} />
            Adicionar ao plano
          </button>
        </div>
      ) : (
        <div
          className={cn(
            'space-y-2 overflow-hidden transition-[max-height] duration-slow ease-in-out',
            expanded ? 'max-h-[600px]' : 'max-h-[200px]'
          )}
        >
          {todayItems.map((item) => {
            const agent = AGENT_MAP[item.agent_slug]
            return (
              <div
                key={item.id}
                className="flex items-center gap-3 py-2 border-b border-border last:border-b-0"
              >
                {/* Time pill */}
                <span
                  className="text-caption-sm font-mono text-gray-300 bg-elevated border border-border rounded px-2 py-0.5 shrink-0 min-w-[48px] text-center"
                >
                  {item.scheduled_for ? formatTime(item.scheduled_for) : '--:--'}
                </span>

                {/* Agent dot */}
                {agent && (
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: agent.color }}
                    aria-label={agent.name}
                  />
                )}

                {/* Title */}
                <p className="text-body-sm text-gray-200 truncate">{item.title}</p>
              </div>
            )
          })}
        </div>
      )}
    </section>
  )
}
