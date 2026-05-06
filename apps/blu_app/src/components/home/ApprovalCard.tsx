import { useState } from 'react'
import { CheckCircle, X, AlarmClock, ChevronUp, ChevronDown } from 'lucide-react'
import { cn } from '@/utils/cn'
import { AgentBadge } from '@/components/navigation/AgentBadge'
import { useApproveRequest, useRejectRequest } from '@/hooks/useApproval'
import { useTrust } from '@/hooks/useTrust'
import { AGENT_MAP } from '@/utils/constants'
import { relativeTime, snoozeLabel } from '@/utils/format'
import type { ApprovalRequest } from '@/types/approval'
import { SnoozePicker } from './SnoozePicker'

interface ApprovalCardProps {
  approval: ApprovalRequest
  onCollapse?: () => void
}

export function ApprovalCard({ approval, onCollapse }: ApprovalCardProps) {
  const agent = AGENT_MAP[approval.agent_slug]
  const { checkMilestones } = useTrust()
  const approve = useApproveRequest(checkMilestones)
  const reject = useRejectRequest(checkMilestones)
  const [showSnooze, setShowSnooze] = useState(false)
  const [insightOpen, setInsightOpen] = useState(false)
  const [feedback, setFeedback] = useState<string | null>(null)
  const isUrgent = approval.priority === 'urgent'
  const isPending = approve.isPending || reject.isPending

  function showFeedbackThen(msg: string) {
    setFeedback(msg)
    setTimeout(() => setFeedback(null), 2500)
  }

  return (
    <div
      className={cn(
        'bg-surface border rounded-md p-4 animate-slide-up',
        isUrgent ? 'border-l-4 border-l-urgent border-y-border border-r-border' : 'border-border'
      )}
    >
      {/* Header */}
      <div className="flex items-start gap-3 mb-3">
        {agent && (
          <AgentBadge
            shape={agent.shape}
            color={agent.color}
            glowColor={agent.glowColor}
            size={32}
            status="idle"
          />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-caption text-gray-300">{agent?.name ?? approval.agent_slug}</span>
            {isUrgent && (
              <span className="text-caption-sm text-urgent font-medium">Urgente</span>
            )}
            <span className="text-caption-sm text-gray-500 ml-auto">
              {relativeTime(approval.created_at)}
            </span>
          </div>
          <h3 className="text-heading-sm text-white mt-1">{approval.title}</h3>
        </div>
        {onCollapse && (
          <button
            onClick={onCollapse}
            className="p-1 text-gray-400 hover:text-white transition-colors cursor-pointer rounded focus-visible:ring-2 focus-visible:ring-blu-500"
            aria-label="Recolher"
          >
            <ChevronUp size={16} />
          </button>
        )}
      </div>

      {/* Previously snoozed indicator */}
      {approval.snooze_count > 0 && approval.snooze_until && (
        <p className="text-caption-sm text-gray-500 mb-3 flex items-center gap-1">
          <AlarmClock size={11} />
          Adiado de {snoozeLabel(approval.snooze_until)}
        </p>
      )}

      {/* Full description */}
      {approval.payload.description && (
        <p className="text-body-sm text-gray-200 mb-3 leading-relaxed">
          {approval.payload.description}
        </p>
      )}

      {/* Bullets */}
      {approval.payload.bullets && approval.payload.bullets.length > 0 && (
        <ul className="mb-4 space-y-1.5">
          {approval.payload.bullets.map((b, i) => (
            <li key={i} className="text-body-sm text-gray-300 flex items-start gap-2">
              <span className="mt-2 w-1.5 h-1.5 rounded-full bg-blu-400 shrink-0" />
              {b}
            </li>
          ))}
        </ul>
      )}

      {/* Collapsible insight */}
      {approval.insight_text && (
        <div className="mb-4">
          <button
            onClick={() => setInsightOpen((v) => !v)}
            className="text-caption text-blu-400 flex items-center gap-1 cursor-pointer hover:text-blu-300 transition-colors"
          >
            {insightOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            Contexto do agente
          </button>
          {insightOpen && (
            <p className="mt-2 text-caption text-blu-300 border-l-2 border-blu-500/30 pl-3 animate-fade-in">
              {approval.insight_text}
            </p>
          )}
        </div>
      )}

      {/* Primary actions */}
      <div className="flex gap-2 flex-wrap relative">
        <button
          onClick={() =>
            approve.mutate(approval.id, {
              onSuccess: () => showFeedbackThen('Aprovado com sucesso'),
            })
          }
          disabled={isPending}
          className={cn(
            'flex items-center gap-1.5 px-4 py-2 rounded text-body-sm font-medium',
            'bg-ok hover:bg-ok-dark text-white border border-transparent',
            'transition-colors cursor-pointer disabled:opacity-50',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ok'
          )}
        >
          <CheckCircle size={15} />
          Aprovar
        </button>
        <button
          onClick={() =>
            reject.mutate(approval.id, {
              onSuccess: () => showFeedbackThen('Rejeitado'),
            })
          }
          disabled={isPending}
          className={cn(
            'flex items-center gap-1.5 px-4 py-2 rounded text-body-sm font-medium',
            'bg-urgent/10 hover:bg-urgent/20 text-urgent border border-urgent/30',
            'transition-colors cursor-pointer disabled:opacity-50',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-urgent'
          )}
        >
          <X size={15} />
          Rejeitar
        </button>
        <button
          onClick={() => setShowSnooze((v) => !v)}
          disabled={isPending}
          className={cn(
            'flex items-center gap-1.5 px-3 py-2 rounded text-body-sm',
            'bg-transparent hover:bg-elevated text-gray-300 hover:text-white border border-border',
            'transition-colors cursor-pointer disabled:opacity-50',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500'
          )}
        >
          <AlarmClock size={14} />
          Depois
        </button>

        {showSnooze && (
          <SnoozePicker
            approvalId={approval.id}
            onClose={() => setShowSnooze(false)}
          />
        )}
      </div>

      {/* Inline feedback */}
      {feedback && (
        <p className="mt-3 text-body-sm text-ok text-center animate-fade-in">
          {feedback}
        </p>
      )}
    </div>
  )
}
