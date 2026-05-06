import { useEffect } from 'react'
import { Trophy } from 'lucide-react'
import { cn } from '@/utils/cn'
import { useTrust } from '@/hooks/useTrust'
import { useToast } from '@/components/feedback/SuccessToast'

/**
 * Mounts in AppShell.
 * Watches activeMilestone and fires a toast for the 50-approval full_config milestone.
 */
export function TrustMilestoneToast() {
  const { activeMilestone } = useTrust()
  const { showToast } = useToast()

  useEffect(() => {
    if (activeMilestone?.showToast) {
      showToast('Configuração completa desbloqueada. Blu conhece o seu negócio.', {
        variant: 'success',
        duration: 5000,
      })
    }
  }, [activeMilestone, showToast])

  return null
}

// ── Trust level badge (for AdminPage / UnderDesk info row) ────────────────────

const TRUST_LABELS: Record<string, { label: string; color: string; hint: string }> = {
  none: {
    label: 'Disponível em breve',
    color: 'text-gray-500',
    hint: 'Aprove as primeiras decisões para desbloquear automações personalizadas',
  },
  similar_toggle: {
    label: 'Automação similar',
    color: 'text-attention',
    hint: 'Blu pode repetir decisões parecidas automaticamente',
  },
  rules: {
    label: 'Regras avançadas',
    color: 'text-blu-400',
    hint: 'Configure regras customizadas de automação',
  },
  full_config: {
    label: 'Configuração completa',
    color: 'text-ok',
    hint: 'Blu conhece seu negócio e opera com total autonomia configurável',
  },
}

export function TrustLevelBadge({
  trustLevel,
  className,
}: {
  trustLevel?: string
  className?: string
}) {
  const level = TRUST_LABELS[trustLevel ?? 'none'] ?? TRUST_LABELS.none

  return (
    <span
      title={level.hint}
      className={cn(
        'inline-flex items-center gap-1.5 text-caption font-medium cursor-help',
        level.color,
        className
      )}
    >
      <Trophy size={11} className="fill-current opacity-80" />
      {level.label}
    </span>
  )
}
