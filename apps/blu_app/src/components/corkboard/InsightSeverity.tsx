import { cn } from '@/utils/cn'

type SeverityLevel = 'critical' | 'warning' | 'info' | 'positive'

interface InsightSeverityProps {
  level: SeverityLevel
  className?: string
}

const levelConfig: Record<SeverityLevel, { dot: string; label: string }> = {
  critical: { dot: 'bg-urgent animate-orb-attention', label: 'Crítico' },
  warning: { dot: 'bg-attention', label: 'Atenção' },
  info: { dot: 'bg-blu-400', label: 'Info' },
  positive: { dot: 'bg-ok', label: 'Positivo' },
}

export function InsightSeverity({ level, className }: InsightSeverityProps) {
  const { dot, label } = levelConfig[level]
  return (
    <span className={cn('inline-flex items-center gap-1.5', className)}>
      <span className={cn('w-2 h-2 rounded-full shrink-0', dot)} />
      <span className="text-caption-sm text-gray-400">{label}</span>
    </span>
  )
}
