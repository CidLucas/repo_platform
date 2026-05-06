import { useNavigate } from 'react-router-dom'
import { AlertTriangle, Lock, ChevronRight } from 'lucide-react'
import { cn } from '@/utils/cn'
import { useAgentReadiness } from '@/hooks/useAgent'
import type { AgentSlug, KnowledgeReadinessStatus } from '@/types/agent'

interface KnowledgeGapAlertProps {
  agentSlug: AgentSlug
  /** Optional className for the wrapper */
  className?: string
}

/**
 * Inline alert shown inside an agent room when the agent is partial or blocked.
 * Lists the missing minimum-requirement documents and provides CTAs.
 */
export function KnowledgeGapAlert({ agentSlug, className }: KnowledgeGapAlertProps) {
  const { data: readiness = [] } = useAgentReadiness()
  const navigate = useNavigate()

  const agentData = readiness.find((r) => r.agent_slug === agentSlug)
  if (!agentData) return null

  const { status, min_coverage_pct, missing_docs } = agentData
  if (status === 'ready') return null

  return (
    <GapAlertView
      status={status}
      coveragePct={min_coverage_pct}
      missingDocs={missing_docs}
      onConnectIntegration={() => navigate('/onboarding')}
    />
  )
}

// ── Pure presentational sub-component ───────────────────────────────────────

interface GapAlertViewProps {
  status: KnowledgeReadinessStatus
  coveragePct: number
  missingDocs: string[]
  onConnectIntegration: () => void
}

function GapAlertView({
  status,
  coveragePct,
  missingDocs,
  onConnectIntegration,
}: GapAlertViewProps) {
  const isBlocked = status === 'blocked'

  return (
    <div
      className={cn(
        'rounded-lg border p-4',
        isBlocked
          ? 'border-red-500/20 bg-red-950/20'
          : 'border-amber-500/20 bg-amber-950/20'
      )}
    >
      {/* Header */}
      <div className="flex items-start gap-3 mb-3">
        <span className={cn(
          'shrink-0 mt-0.5',
          isBlocked ? 'text-red-400' : 'text-amber-400'
        )}>
          {isBlocked ? <Lock size={15} /> : <AlertTriangle size={15} />}
        </span>
        <div className="flex-1 min-w-0">
          <p className={cn(
            'text-body-sm font-medium',
            isBlocked ? 'text-red-300' : 'text-amber-300'
          )}>
            {isBlocked
              ? 'Agente bloqueado por falta de contexto'
              : 'Capacidade parcial — contexto incompleto'}
          </p>
          <p className="text-caption-sm text-gray-500 mt-0.5">
            {coveragePct}% dos documentos mínimos disponíveis
          </p>
        </div>
      </div>

      {/* Coverage bar */}
      <div className="mb-3 h-1 w-full rounded-full bg-white/5 overflow-hidden">
        <div
          className={cn(
            'h-full rounded-full transition-all duration-500',
            isBlocked ? 'bg-red-500' : 'bg-amber-400'
          )}
          style={{ width: `${Math.max(coveragePct, 2)}%` }}
        />
      </div>

      {/* Missing docs list */}
      {missingDocs.length > 0 && (
        <div className="space-y-1.5 mb-3">
          {missingDocs.map((docName) => (
            <div key={docName} className="flex items-center gap-2">
              <span className={cn(
                'shrink-0 w-1.5 h-1.5 rounded-full',
                isBlocked ? 'bg-red-500' : 'bg-amber-400'
              )} />
              <span className="text-caption-sm text-gray-400 flex-1 truncate">{docName}</span>
            </div>
          ))}
        </div>
      )}

      {/* CTA */}
      <button
        onClick={onConnectIntegration}
        className={cn(
          'flex items-center gap-1.5 text-caption-sm font-medium',
          'transition-colors cursor-pointer',
          isBlocked
            ? 'text-red-400 hover:text-red-300'
            : 'text-amber-400 hover:text-amber-300'
        )}
      >
        Conectar integração ou enviar documento
        <ChevronRight size={12} />
      </button>
    </div>
  )
}
