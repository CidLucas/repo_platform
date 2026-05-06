import { cn } from '@/utils/cn'
import type { KpiPeriod } from '@/types/analytics'

const PERIODS: { label: string; value: KpiPeriod }[] = [
  { label: '7 dias', value: '7d' },
  { label: '30 dias', value: '30d' },
  { label: '90 dias', value: '90d' },
  { label: '1 ano', value: '1y' },
]

interface PeriodSelectorProps {
  value: KpiPeriod
  onChange: (period: KpiPeriod) => void
  className?: string
}

export function PeriodSelector({ value, onChange, className }: PeriodSelectorProps) {
  return (
    <div
      className={cn('flex items-center gap-0.5 bg-elevated rounded-full p-1', className)}
      role="group"
      aria-label="Selecionar período"
    >
      {PERIODS.map((p) => (
        <button
          key={p.value}
          onClick={() => onChange(p.value)}
          className={cn(
            'px-3 py-1 rounded-full text-caption font-medium',
            'transition-colors duration-normal cursor-pointer',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500',
            value === p.value
              ? 'bg-blu-500 text-white shadow-sm'
              : 'text-gray-400 hover:text-white hover:bg-surface'
          )}
          aria-pressed={value === p.value}
        >
          {p.label}
        </button>
      ))}
    </div>
  )
}
