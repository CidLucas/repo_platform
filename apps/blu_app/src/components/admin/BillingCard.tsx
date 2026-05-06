import { Check, ArrowUpRight, Zap } from 'lucide-react'
import { cn } from '@/utils/cn'
import { Button } from '@/components/primitives/Button'
import { Badge } from '@/components/primitives/Badge'
import type { ClienteBlu } from '@/types/user'

// ── Tier config ────────────────────────────────────────────────────────────

type Tier = ClienteBlu['tier']

interface TierConfig {
  label: string
  description: string
  price: string
  features: string[]
  color: string
  badge: 'info' | 'ok' | 'attention' | 'urgent'
  cta: string | null
}

const TIER_CONFIG: Record<Tier, TierConfig> = {
  free: {
    label: 'Free',
    description: 'Comece a explorar o Blu sem compromisso.',
    price: 'R$ 0/mês',
    features: [
      '1 agente ativo',
      'Até 20 aprovações/mês',
      'Histórico de 7 dias',
      'Suporte por e-mail',
    ],
    color: '#4A90D9',
    badge: 'info',
    cta: 'Fazer upgrade',
  },
  starter: {
    label: 'Starter',
    description: 'Para negócios que estão crescendo.',
    price: 'R$ 197/mês',
    features: [
      '3 agentes ativos',
      'Aprovações ilimitadas',
      'Histórico de 90 dias',
      'Regras de automação básicas',
      'Suporte prioritário',
    ],
    color: '#5FB8A3',
    badge: 'ok',
    cta: 'Fazer upgrade para Growth',
  },
  growth: {
    label: 'Growth',
    description: 'Automação completa para times em expansão.',
    price: 'R$ 397/mês',
    features: [
      'Todos os 6 agentes ativos',
      'Aprovações e automações ilimitadas',
      'Histórico completo',
      'Regras avançadas de automação',
      'Acesso multi-usuário (até 5)',
      'Suporte dedicado',
    ],
    color: '#D4A843',
    badge: 'attention',
    cta: 'Fazer upgrade para Enterprise',
  },
  enterprise: {
    label: 'Enterprise',
    description: 'Para empresas que precisam de controle total.',
    price: 'Sob consulta',
    features: [
      'Tudo do Growth',
      'Usuários ilimitados',
      'Integrações customizadas',
      'SLA garantido',
      'Treinamento e onboarding dedicado',
      'Contrato personalizado',
    ],
    color: '#E07A5F',
    badge: 'urgent',
    cta: null,
  },
}

// ── UpgradeTierCard ────────────────────────────────────────────────────────

interface UpgradeTierCardProps {
  tier: Tier
  isCurrent?: boolean
}

function UpgradeTierCard({ tier, isCurrent }: UpgradeTierCardProps) {
  const cfg = TIER_CONFIG[tier]

  return (
    <div
      className={cn(
        'rounded-md border p-4 transition-colors duration-normal',
        isCurrent
          ? 'bg-elevated border-blu-500 shadow-glow-blu'
          : 'bg-surface border-border opacity-70'
      )}
    >
      <div className="flex items-center justify-between mb-1">
        <span
          className="text-body-sm font-medium"
          style={{ color: isCurrent ? cfg.color : undefined }}
        >
          {cfg.label}
        </span>
        {isCurrent && <Badge variant={cfg.badge}>Seu plano</Badge>}
      </div>
      <p className="text-caption text-gray-400 mb-3">{cfg.description}</p>
      <p className="text-heading-sm text-white mb-3">{cfg.price}</p>
      <ul className="space-y-1.5">
        {cfg.features.map((f) => (
          <li key={f} className="flex items-start gap-2 text-caption text-gray-300">
            <Check
              size={13}
              strokeWidth={2.5}
              className="shrink-0 mt-0.5"
              style={{ color: cfg.color }}
            />
            {f}
          </li>
        ))}
      </ul>
    </div>
  )
}

// ── BillingCard ────────────────────────────────────────────────────────────

interface BillingCardProps {
  tier: Tier
}

export function BillingCard({ tier }: BillingCardProps) {
  const cfg = TIER_CONFIG[tier]

  return (
    <div className="space-y-6">
      {/* Current plan summary */}
      <div className="bg-surface border border-blu-500/30 rounded-md p-5 shadow-glow-blu">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Zap size={16} strokeWidth={1.5} style={{ color: cfg.color }} />
              <span className="text-heading-sm text-white">Plano atual: {cfg.label}</span>
            </div>
            <p className="text-caption text-gray-400">{cfg.description}</p>
            <p className="text-display-md text-white mt-2">{cfg.price}</p>
          </div>
          <Badge variant={cfg.badge}>{cfg.label}</Badge>
        </div>

        {cfg.cta && (
          <Button
            variant="primary"
            size="sm"
            className="mt-4"
            rightIcon={<ArrowUpRight size={14} strokeWidth={1.5} />}
            onClick={() => window.open('https://blu.ai/planos', '_blank', 'noopener')}
          >
            {cfg.cta}
          </Button>
        )}
      </div>

      {/* All plans comparison */}
      <div>
        <h3 className="text-body-sm font-medium text-gray-300 mb-3">Todos os planos</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {(Object.keys(TIER_CONFIG) as Tier[]).map((t) => (
            <UpgradeTierCard key={t} tier={t} isCurrent={t === tier} />
          ))}
        </div>
      </div>

      {/* Billing actions */}
      <div className="bg-surface border border-border rounded-md p-4">
        <h3 className="text-body-sm font-medium text-white mb-3">Faturamento</h3>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-caption text-gray-400">Histórico de faturas</span>
            <Button
              variant="ghost"
              size="sm"
              rightIcon={<ArrowUpRight size={13} strokeWidth={1.5} />}
              onClick={() => window.open('https://blu.ai/faturas', '_blank', 'noopener')}
            >
              Ver faturas
            </Button>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-caption text-gray-400">Método de pagamento</span>
            <Button
              variant="ghost"
              size="sm"
              rightIcon={<ArrowUpRight size={13} strokeWidth={1.5} />}
              onClick={() => window.open('https://blu.ai/pagamento', '_blank', 'noopener')}
            >
              Gerenciar
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
