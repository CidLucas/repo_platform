import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn } from '@/utils/cn'

type Trend = 'up' | 'down' | 'flat'

interface MetricCardProps {
  label: string
  value: string
  trend?: Trend
  delta?: string
  /** Optional subtext below the value */
  sublabel?: string
  className?: string
}

export function MetricCard({ label, value, trend, delta, sublabel, className }: MetricCardProps) {
  const TrendIcon =
    trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus

  const trendColor =
    trend === 'up'
      ? 'text-ok'
      : trend === 'down'
        ? 'text-urgent'
        : 'text-gray-400'

  return (
    <div
      className={cn(
        'bg-surface border border-border rounded-md p-4 shadow',
        className
      )}
    >
      <p className="text-caption text-gray-400 mb-1">{label}</p>
      <div className="flex items-end gap-2">
        <span className="font-mono text-mono-lg text-white leading-none">{value}</span>
        {trend && delta && (
          <span className={cn('flex items-center gap-0.5 text-caption mb-0.5', trendColor)}>
            <TrendIcon size={13} strokeWidth={2} />
            {delta}
          </span>
        )}
      </div>
      {sublabel && (
        <p className="text-caption-sm text-gray-500 mt-1">{sublabel}</p>
      )}
    </div>
  )
}
