import { useState } from 'react'
import { Plus, Trash2, Lock } from 'lucide-react'
import { cn } from '@/utils/cn'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/hooks/useAuth'
import {
  fetchApprovalRules,
  createApprovalRule,
  deleteApprovalRule,
} from '@/api/approval-rules'
import type { AgentSlug } from '@/types/agent'

interface RuleBuilderProps {
  agentSlug: AgentSlug
  /** Minimum trust level required to show this component */
  trustLevel?: 'rules' | 'full_config'
  /** Current user trust level from useApprovalStats */
  currentTrustLevel?: string
}

const RULE_TYPES = [
  { value: 'auto_approve_below', label: 'Aprovar automaticamente abaixo de' },
  { value: 'auto_reject_above', label: 'Rejeitar automaticamente acima de' },
  { value: 'always_manual', label: 'Sempre aprovar manualmente' },
] as const

type RuleType = (typeof RULE_TYPES)[number]['value']

const TRUST_ORDER = ['none', 'similar_toggle', 'rules', 'full_config']

function hasMinTrust(current: string | undefined, required: string): boolean {
  const cur = TRUST_ORDER.indexOf(current ?? 'none')
  const req = TRUST_ORDER.indexOf(required)
  return cur >= req
}

export function RuleBuilder({
  agentSlug,
  trustLevel = 'rules',
  currentTrustLevel,
}: RuleBuilderProps) {
  const { clientId } = useAuth()
  const qc = useQueryClient()
  const [ruleType, setRuleType] = useState<RuleType>('auto_approve_below')
  const [conditionValue, setConditionValue] = useState('')
  const [error, setError] = useState<string | null>(null)

  const unlocked = hasMinTrust(currentTrustLevel, trustLevel)

  const { data: rules = [], isLoading } = useQuery({
    queryKey: ['approval-rules', agentSlug, clientId],
    queryFn: () => fetchApprovalRules(clientId!),
    enabled: !!clientId && unlocked,
    select: (all) => all.filter((r) => r.agent_slug === agentSlug),
  })

  const create = useMutation({
    mutationFn: () =>
      createApprovalRule({
        client_id: clientId!,
        agent_slug: agentSlug,
        rule_type: ruleType,
        condition: conditionValue ? { value: conditionValue } : {},
        action: ruleType === 'auto_approve_below' ? 'approve' : 'reject',
        enabled: true,
      }),
    onSuccess: () => {
      setConditionValue('')
      setError(null)
      qc.invalidateQueries({ queryKey: ['approval-rules', agentSlug, clientId] })
    },
    onError: () => setError('Não foi possível salvar a regra. Tente novamente.'),
  })

  const remove = useMutation({
    mutationFn: (id: string) => deleteApprovalRule(id, clientId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['approval-rules', agentSlug, clientId] })
    },
  })

  // Locked state
  if (!unlocked) {
    return (
      <div className="flex items-center gap-2 px-4 py-3 text-gray-500">
        <Lock size={14} strokeWidth={1.5} />
        <p className="text-caption">
          Regras avançadas desbloqueadas após 25 aprovações.
        </p>
      </div>
    )
  }

  function handleSave() {
    if (!conditionValue.trim() && ruleType !== 'always_manual') {
      setError('Informe o valor da condição.')
      return
    }
    create.mutate()
  }

  return (
    <div className="px-4 py-3 space-y-4">
      <p className="text-caption-sm text-gray-500 uppercase tracking-wider">
        Regras de aprovação
      </p>

      {/* Existing rules */}
      {!isLoading && rules.length > 0 && (
        <ul className="space-y-2">
          {rules.map((rule) => {
            const typeLabel =
              RULE_TYPES.find((t) => t.value === rule.rule_type)?.label ??
              rule.rule_type
            const val = rule.condition?.value as string | undefined
            return (
              <li
                key={rule.id}
                className="flex items-center justify-between gap-2 bg-elevated
                  border border-border rounded px-3 py-2"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-body-sm text-gray-200 truncate">
                    {typeLabel}
                    {val && (
                      <span className="text-blu-400 ml-1 font-mono">
                        R$ {val}
                      </span>
                    )}
                  </p>
                  <p className="text-caption-sm text-gray-500">
                    {rule.enabled ? 'Ativa' : 'Inativa'}
                  </p>
                </div>
                <button
                  onClick={() => remove.mutate(rule.id)}
                  aria-label="Excluir regra"
                  disabled={remove.isPending}
                  className="text-gray-500 hover:text-urgent transition-colors
                    cursor-pointer p-1 rounded disabled:opacity-50
                    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-urgent"
                >
                  <Trash2 size={13} />
                </button>
              </li>
            )
          })}
        </ul>
      )}

      {/* Builder form */}
      <div className="space-y-2">
        <select
          value={ruleType}
          onChange={(e) => {
            setRuleType(e.target.value as RuleType)
            setError(null)
          }}
          className={cn(
            'w-full px-3 py-2 rounded bg-base border border-border',
            'text-body-sm text-gray-200',
            'focus:border-blu-500 focus:outline-none focus:shadow-glow-blu',
            'transition-colors duration-normal'
          )}
        >
          {RULE_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>

        {ruleType !== 'always_manual' && (
          <div className="flex items-center gap-2">
            <span className="text-body-sm text-gray-400 shrink-0">R$</span>
            <input
              type="number"
              inputMode="numeric"
              placeholder="500"
              value={conditionValue}
              onChange={(e) => {
                setConditionValue(e.target.value)
                setError(null)
              }}
              className={cn(
                'flex-1 px-3 py-2 rounded bg-base border text-body-sm text-white',
                'placeholder:text-gray-500',
                'focus:border-blu-500 focus:outline-none focus:shadow-glow-blu',
                'transition-colors duration-normal',
                error ? 'border-urgent' : 'border-border'
              )}
            />
          </div>
        )}

        {error && (
          <p className="text-caption text-urgent">{error}</p>
        )}

        <button
          onClick={handleSave}
          disabled={create.isPending}
          className={cn(
            'flex items-center gap-1.5 px-3 py-1.5 rounded w-full justify-center',
            'text-body-sm text-white bg-blu-500 hover:bg-blu-600',
            'transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500'
          )}
        >
          <Plus size={14} />
          {create.isPending ? 'Salvando…' : 'Salvar regra'}
        </button>
      </div>
    </div>
  )
}
