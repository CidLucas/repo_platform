import { BarChart2 } from 'lucide-react'
import { cn } from '@/utils/cn'
import { PeriodSelector } from './PeriodSelector'
import type { KpiPeriod } from '@/types/analytics'

interface AnalyticsHeaderProps {
  period: KpiPeriod
  onPeriodChange: (p: KpiPeriod) => void
  title?: string
  className?: string
}

/**
 * Standalone header row with a title and PeriodSelector.
 * Use when AnalyticsCard is not the right wrapper (e.g. a full-page analytics section).
 */
export function AnalyticsHeader({
  period,
  onPeriodChange,
  title = 'Analytics',
  className,
}: AnalyticsHeaderProps) {
  return (
    <div className={cn('flex items-center justify-between gap-3', className)}>
      <div className="flex items-center gap-2">
        <BarChart2 size={16} strokeWidth={1.5} className="text-blu-400 shrink-0" />
        <span className="text-body-sm font-medium text-gray-200">{title}</span>
      </div>
      <PeriodSelector value={period} onChange={onPeriodChange} />
    </div>
  )
}
