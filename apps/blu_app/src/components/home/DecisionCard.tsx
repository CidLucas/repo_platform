import { useState, useRef, useCallback } from 'react'
import { CheckCircle, Eye, AlarmClock, ChevronDown } from 'lucide-react'
import { cn } from '@/utils/cn'
import { AgentBadge } from '@/components/navigation/AgentBadge'
import { useApproveRequest, useRejectRequest } from '@/hooks/useApproval'
import { useTrust } from '@/hooks/useTrust'
import { AGENT_MAP } from '@/utils/constants'
import { relativeTime } from '@/utils/format'
import type { ApprovalRequest } from '@/types/approval'
import { SnoozePicker } from './SnoozePicker'
import { ApprovalCard } from './ApprovalCard'

interface DecisionCardProps {
  approval: ApprovalRequest
  showSwipeHint?: boolean
}

type SwipeState = 'idle' | 'approving' | 'rejecting'

const SWIPE_THRESHOLD = 72 // px before action triggers

export function DecisionCard({ approval, showSwipeHint = false }: DecisionCardProps) {
  const agent = AGENT_MAP[approval.agent_slug]
  const { checkMilestones } = useTrust()
  const approve = useApproveRequest(checkMilestones)
  const reject = useRejectRequest(checkMilestones)

  const [expanded, setExpanded] = useState(false)
  const [showSnooze, setShowSnooze] = useState(false)
  const [feedback, setFeedback] = useState<string | null>(null)

  // Swipe gesture state
  const pointerStart = useRef<{ x: number; y: number } | null>(null)
  const [dragX, setDragX] = useState(0)
  const [swipeState, setSwipeState] = useState<SwipeState>('idle')
  const isDragging = useRef(false)
  const cardRef = useRef<HTMLDivElement>(null)

  const isUrgent = approval.priority === 'urgent'
  const isPending = approve.isPending || reject.isPending

  function showFeedbackThen(msg: string) {
    setFeedback(msg)
    setTimeout(() => setFeedback(null), 2500)
  }

  function handleApprove() {
    approve.mutate(approval.id, {
      onSuccess: () => showFeedbackThen('Aprovado'),
    })
  }

  function handleReject() {
    reject.mutate(approval.id, {
      onSuccess: () => showFeedbackThen('Rejeitado'),
    })
  }

  // Pointer swipe handlers
  const onPointerDown = useCallback((e: React.PointerEvent) => {
    if (e.pointerType === 'mouse') return // desktop: no swipe
    pointerStart.current = { x: e.clientX, y: e.clientY }
    isDragging.current = false
    ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
  }, [])

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    if (!pointerStart.current) return
    const dx = e.clientX - pointerStart.current.x
    const dy = e.clientY - pointerStart.current.y

    // If vertical movement dominates, don't hijack scroll
    if (!isDragging.current && Math.abs(dy) > Math.abs(dx) + 4) {
      pointerStart.current = null
      return
    }

    if (Math.abs(dx) > 8) isDragging.current = true
    if (!isDragging.current) return

    setDragX(dx)
    if (dx > SWIPE_THRESHOLD) setSwipeState('approving')
    else if (dx < -SWIPE_THRESHOLD) setSwipeState('rejecting')
    else setSwipeState('idle')
  }, [])

  const onPointerUp = useCallback(() => {
    if (!pointerStart.current) return
    pointerStart.current = null

    if (swipeState === 'approving') handleApprove()
    else if (swipeState === 'rejecting') handleReject()

    setDragX(0)
    setSwipeState('idle')
    isDragging.current = false
  }, [swipeState]) // eslint-disable-line react-hooks/exhaustive-deps

  if (expanded) {
    return (
      <ApprovalCard
        approval={approval}
        onCollapse={() => setExpanded(false)}
      />
    )
  }

  return (
    <div className="relative overflow-hidden rounded-md" ref={cardRef}>
      {/* Swipe overlays */}
      {swipeState === 'approving' && (
        <div className="absolute inset-0 bg-ok/20 rounded-md flex items-center pl-4 z-10 pointer-events-none">
          <CheckCircle size={20} className="text-ok" />
          <span className="ml-2 text-ok text-body-sm font-medium">Aprovar</span>
        </div>
      )}
      {swipeState === 'rejecting' && (
        <div className="absolute inset-0 bg-urgent/20 rounded-md flex items-center justify-end pr-4 z-10 pointer-events-none">
          <span className="mr-2 text-urgent text-body-sm font-medium">Rejeitar</span>
        </div>
      )}

      {/* Card body */}
      <div
        className={cn(
          'bg-surface border rounded-md p-4 select-none',
          isUrgent ? 'border-l-4 border-l-urgent border-y-border border-r-border' : 'border-border',
          isDragging.current && 'transition-none',
          !isDragging.current && 'transition-transform duration-normal',
          feedback && 'opacity-60'
        )}
        style={{
          transform: `translateX(${dragX}px)`,
          touchAction: 'pan-y',
        }}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        {/* Header row */}
        <div className="flex items-start gap-3 mb-2">
          {agent && (
            <AgentBadge
              shape={agent.shape}
              color={agent.color}
              glowColor={agent.glowColor}
              size={24}
              status="idle"
            />
          )}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-caption text-gray-300 truncate">
                {agent?.name ?? approval.agent_slug}
              </span>
              {isUrgent && (
                <span className="text-caption-sm text-urgent font-medium shrink-0">
                  Urgente
                </span>
              )}
            </div>
            <p className="text-body-sm font-medium text-white mt-0.5 line-clamp-1">
              {approval.title}
            </p>
          </div>
          <span className="text-caption-sm text-gray-400 shrink-0 ml-1">
            {relativeTime(approval.created_at)}
          </span>
        </div>

        {/* Proposal text */}
        {approval.payload.description && (
          <p className="text-caption text-gray-300 line-clamp-2 mb-2">
            {approval.payload.description}
          </p>
        )}

        {/* Bullets */}
        {approval.payload.bullets && approval.payload.bullets.length > 0 && (
          <ul className="mb-3 space-y-0.5">
            {approval.payload.bullets.slice(0, 3).map((b, i) => (
              <li key={i} className="text-caption text-gray-400 flex items-start gap-1.5">
                <span className="mt-1.5 w-1 h-1 rounded-full bg-gray-500 shrink-0" />
                {b}
              </li>
            ))}
          </ul>
        )}

        {/* Swipe hint (first card only) */}
        {showSwipeHint && (
          <p className="text-caption-sm text-blu-400 mb-2 text-center">
            Deslize para aprovar ou rejeitar
          </p>
        )}

        {/* Action row */}
        <div className="flex gap-2 mt-1 relative">
          <button
            onClick={handleApprove}
            disabled={isPending}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded text-body-sm font-medium',
              'bg-ok/10 hover:bg-ok/20 text-ok border border-ok/20',
              'transition-colors cursor-pointer disabled:opacity-50',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ok'
            )}
          >
            <CheckCircle size={14} />
            Aprovar
          </button>
          <button
            onClick={() => setExpanded(true)}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded text-body-sm',
              'bg-transparent hover:bg-elevated text-gray-200 hover:text-white border border-border',
              'transition-colors cursor-pointer',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500'
            )}
          >
            <Eye size={14} />
            Ver
          </button>
          <button
            onClick={() => setShowSnooze((v) => !v)}
            disabled={isPending}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded text-body-sm',
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

        {/* Insight text */}
        {approval.insight_text && (
          <p className="mt-2 text-caption text-blu-300">
            {approval.insight_text}
          </p>
        )}

        {/* Snooze indicator */}
        {approval.snooze_count > 0 && approval.snooze_until && (
          <p className="mt-1 text-caption-sm text-gray-500 flex items-center gap-1">
            <AlarmClock size={11} />
            Adiado {approval.snooze_count}×
          </p>
        )}

        {/* Inline feedback */}
        {feedback && (
          <p className="mt-2 text-body-sm text-ok text-center animate-fade-in">
            {feedback}
          </p>
        )}
      </div>

      {/* Collapse/expand chevron (accessibility) */}
      <button
        onClick={() => setExpanded(true)}
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:right-2 focus:p-1 focus:bg-elevated focus:rounded focus:text-white"
        aria-label="Expandir detalhes"
      >
        <ChevronDown size={14} />
      </button>
    </div>
  )
}
