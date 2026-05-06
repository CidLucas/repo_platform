import { useNavigate } from 'react-router-dom'
import { ArrowRight, AlertCircle, RefreshCcw } from 'lucide-react'
import { cn } from '@/utils/cn'
import { usePendingApprovals } from '@/hooks/useApproval'
import { SkeletonCard } from '@/components/primitives/SkeletonCard'
import { DecisionCard } from './DecisionCard'

const MAX_VISIBLE = 5

export function DecidirAgora() {
  const { data: approvals, isLoading, isError, refetch } = usePendingApprovals()
  const navigate = useNavigate()

  return (
    <section aria-label="Decisões pendentes">
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-display text-display-md text-white">Decidir agora</h2>
        {(approvals?.length ?? 0) > MAX_VISIBLE && (
          <button
            onClick={() => navigate('/aprovacoes')}
            className={cn(
              'flex items-center gap-1 text-body-sm text-blu-400 hover:text-blu-300',
              'transition-colors cursor-pointer',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500 rounded px-1'
            )}
          >
            Ver todas {approvals!.length} decisões
            <ArrowRight size={14} />
          </button>
        )}
      </div>

      {isError && (
        <div className="flex flex-col items-center justify-center py-8 px-4 text-center bg-surface border border-border rounded-md">
          <div className="w-10 h-10 rounded-full bg-urgent/10 flex items-center justify-center mb-3">
            <AlertCircle size={18} strokeWidth={1.5} className="text-urgent" />
          </div>
          <p className="text-body-sm text-white font-medium mb-1">
            Não foi possível carregar as decisões
          </p>
          <p className="text-caption text-gray-400 mb-4">
            Verifique sua conexão e tente novamente.
          </p>
          <button
            onClick={() => refetch()}
            className={cn(
              'inline-flex items-center gap-1.5 px-3 py-1.5 rounded',
              'text-body-sm text-blu-400 hover:text-blu-300 border border-blu-500/30',
              'hover:bg-blu-500/10 transition-colors cursor-pointer',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500'
            )}
          >
            <RefreshCcw size={13} />
            Tentar novamente
          </button>
        </div>
      )}

      {isLoading && (
        <div className="space-y-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {!isLoading && !isError && approvals?.length === 0 && (
        <EmptyDecidirAgora />
      )}

      {!isLoading && !isError && approvals && approvals.length > 0 && (
        <div
          className="space-y-3 max-h-[480px] overflow-y-auto overscroll-contain pr-0.5"
          style={{ scrollbarWidth: 'thin' }}
        >
          {approvals.slice(0, MAX_VISIBLE).map((approval, i) => (
            <DecisionCard
              key={approval.id}
              approval={approval}
              showSwipeHint={i === 0}
            />
          ))}

          {approvals.length > MAX_VISIBLE && (
            <button
              onClick={() => navigate('/aprovacoes')}
              className={cn(
                'w-full py-3 text-body-sm text-center text-blu-400 hover:text-blu-300',
                'bg-surface border border-border rounded-md',
                'transition-colors cursor-pointer',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500'
              )}
            >
              Ver todas {approvals.length} decisões →
            </button>
          )}
        </div>
      )}
    </section>
  )
}

function EmptyDecidirAgora() {
  return (
    <div className="bg-sand/10 border border-sand/20 rounded-md px-4 py-6 text-center">
      <div className="w-8 h-8 rounded-full bg-ok/20 flex items-center justify-center mx-auto mb-3">
        <div className="w-3 h-3 rounded-full bg-ok" />
      </div>
      <p className="text-body-sm text-white font-medium">Nada urgente agora</p>
      <p className="text-caption text-gray-400 mt-1">Seu time está trabalhando.</p>
    </div>
  )
}
