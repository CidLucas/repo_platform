import { useState } from 'react'
import { Clock, CheckSquare, History } from 'lucide-react'
import { cn } from '@/utils/cn'
import { TabGroup } from '@/components/primitives/TabGroup'
import { SkeletonCard } from '@/components/primitives/SkeletonCard'
import { LoadingAgent } from '@/components/feedback/LoadingAgent'
import { DecisionCard } from './DecisionCard'
import { EmptyDesk } from './EmptyDesk'
import type { ApprovalRequest } from '@/types/approval'
import type { OrbShape } from '@/types/agent'

type DeskTab = 'decisions' | 'tasks' | 'history'

interface DeskSurfaceProps {
  /** Pending approvals for this agent room */
  approvals?: ApprovalRequest[]
  /** Initial data loading — shows skeleton cards */
  loading?: boolean
  /**
   * Agent is actively processing (current_status='working').
   * Shows a pulsing LoadingAgent banner at the top of the Decisions tab
   * while existing approvals remain visible beneath it.
   */
  agentWorking?: boolean
  agentOrbShape?: OrbShape
  agentOrbColor?: string
  agentOrbGlow?: string
  /** Agent name — used to scope label */
  agentName?: string
  /** Optional "active tasks" slot rendered in the Tasks tab */
  tasksSlot?: React.ReactNode
  /** Optional history slot rendered in the History tab */
  historySlot?: React.ReactNode
  className?: string
}

const TABS = [
  { id: 'decisions', label: 'Decisões', icon: Clock },
  { id: 'tasks', label: 'Tarefas', icon: CheckSquare },
  { id: 'history', label: 'Histórico', icon: History },
] as const

/**
 * Main surface of every agent room. Three tabs:
 * 1. Decisions — pending approvals for this agent
 * 2. Tasks — active work items (room-specific slot)
 * 3. History — completed decisions (room-specific slot)
 */
export function DeskSurface({
  approvals = [],
  loading = false,
  agentWorking = false,
  agentOrbShape = 'circle',
  agentOrbColor = '#4A90D9',
  agentOrbGlow = 'rgba(74,144,217,0.3)',
  agentName,
  tasksSlot,
  historySlot,
  className,
}: DeskSurfaceProps) {
  const [activeTab, setActiveTab] = useState<DeskTab>('decisions')

  const urgentApprovals = approvals.filter((a) => a.priority === 'urgent')
  const normalApprovals = approvals.filter((a) => a.priority !== 'urgent')

  const pendingCount = approvals.length
  const urgentCount = urgentApprovals.length

  const tabItems = TABS.map((t) => ({
    id: t.id,
    label:
      t.id === 'decisions' && pendingCount > 0
        ? `${t.label} (${pendingCount})`
        : t.label,
  }))

  return (
    <div
      className={cn(
        'bg-surface border border-border rounded-md shadow-md overflow-hidden',
        className
      )}
    >
      {/* Colored top accent strip */}
      <div className="h-[3px] w-full" style={{ background: `linear-gradient(90deg, ${agentOrbColor}, ${agentOrbColor}66)` }} />

      {/* Header */}
      <div className="px-4 pt-4 pb-0 border-b border-border">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-display text-heading-sm text-white">
            {agentName ? `Mesa — ${agentName}` : 'Mesa'}
          </h2>
          {urgentCount > 0 && (
            <span className="text-caption-sm text-urgent font-medium flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-urgent animate-orb-attention" />
              {urgentCount} urgente{urgentCount > 1 ? 's' : ''}
            </span>
          )}
        </div>

        <TabGroup
          tabs={tabItems}
          activeId={activeTab}
          onChange={(id) => setActiveTab(id as DeskTab)}
          accentColor={agentOrbColor}
        />
      </div>

      {/* Tab content */}
      <div className="p-4">
        {/* Decisions tab */}
        {activeTab === 'decisions' && (
          <div className="space-y-3">
            {/* Initial loading skeletons */}
            {loading ? (
              <>
                <SkeletonCard lines={3} />
                <SkeletonCard lines={3} />
              </>
            ) : (
              <>
                {/* Agent working banner — current_status='working' */}
                {agentWorking && (
                  <div
                    className={cn(
                      'px-3 py-2.5 rounded-md',
                      'bg-blu-500/5 border border-blu-500/20'
                    )}
                  >
                    <LoadingAgent
                      compact
                      shape={agentOrbShape}
                      color={agentOrbColor}
                      glowColor={agentOrbGlow}
                      label={agentName ? `${agentName} está processando…` : 'Processando…'}
                    />
                  </div>
                )}

                {/* Empty state or card list */}
                {approvals.length === 0 ? (
                  <EmptyDesk
                    agentName={agentName}
                    onViewHistory={() => {
                      setActiveTab('history')
                    }}
                  />
                ) : (
                  <div className="space-y-3">
                    {/* Urgent first */}
                    {urgentApprovals.map((approval, i) => (
                      <DecisionCard
                        key={approval.id}
                        approval={approval}
                        showSwipeHint={i === 0}
                      />
                    ))}
                    {/* Divider between urgent + normal */}
                    {urgentApprovals.length > 0 && normalApprovals.length > 0 && (
                      <div className="flex items-center gap-2 py-1">
                        <div className="flex-1 border-t border-border" />
                        <span className="text-caption-sm text-gray-500">normais</span>
                        <div className="flex-1 border-t border-border" />
                      </div>
                    )}
                    {normalApprovals.map((approval) => (
                      <DecisionCard key={approval.id} approval={approval} />
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* Tasks tab */}
        {activeTab === 'tasks' && (
          <div>
            {tasksSlot ?? (
              <p className="text-caption text-gray-500 text-center py-4">
                Nenhuma tarefa ativa.
              </p>
            )}
          </div>
        )}

        {/* History tab */}
        {activeTab === 'history' && (
          <div>
            {historySlot ?? (
              <p className="text-caption text-gray-500 text-center py-4">
                Nenhum histórico disponível.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
