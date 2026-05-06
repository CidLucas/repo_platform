import { type LucideIcon, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn } from '@/utils/cn'
import { Card } from './Card'

type KpiAccent = 'blu' | 'ok' | 'urgent' | 'attention' | 'purple' | 'orange' | 'cyan'
type Trend = 'up' | 'down' | 'flat'

const accentHex: Record<KpiAccent, string> = {
  blu:       '#3b82f6',
  ok:        '#10b981',
  urgent:    '#E07A5F',
  attention: '#f97316',
  purple:    '#a855f7',
  orange:    '#f97316',
  cyan:      '#06b6d4',
}

const trendColorClass: Record<Trend, string> = {
  up:   'text-ok',
  down: 'text-urgent',
  flat: 'text-gray-400',
}

const TrendIconMap: Record<Trend, LucideIcon> = {
  up:   TrendingUp,
  down: TrendingDown,
  flat: Minus,
}

interface KpiCardProps {
  label: string
  value: string
  icon?: LucideIcon
  accent?: KpiAccent
  /** Override with a raw hex color */
  color?: string
  trend?: Trend
  delta?: string
  sublabel?: string
  className?: string
}

export function KpiCard({
  label,
  value,
  icon: Icon,
  accent = 'blu',
  color,
  trend,
  delta,
  sublabel,
  className,
}: KpiCardProps) {
  const hex = color ?? accentHex[accent]
  const TrendIcon = trend ? TrendIconMap[trend] : null

  return (
    <div
      className={cn(
        'bg-surface rounded-md p-5 relative overflow-hidden',
        'border border-[rgba(255,255,255,0.08)]',
        'shadow-[0_4px_24px_rgba(0,0,0,0.4)]',
        'transition-all duration-normal',
        'hover:-translate-y-1 hover:shadow-[0_8px_32px_rgba(0,0,0,0.5)]',
        className
      )}
    >
      {/* Left accent bar */}
      <div className="absolute top-0 left-0 w-[3px] h-full" style={{ background: hex }} />

      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-section-label mb-2">{label}</p>
          <p className="font-display text-display-md text-white leading-none tracking-tight">
            {value}
          </p>
          {trend && delta && TrendIcon && (
            <span className={cn('flex items-center gap-1 mt-2 text-caption', trendColorClass[trend])}>
              <TrendIcon size={13} strokeWidth={2.5} />
              {delta}
            </span>
          )}
          {sublabel && (
            <p className="text-caption-sm text-gray-500 mt-1">{sublabel}</p>
          )}
        </div>

        {Icon && (
          <div
            className="w-14 h-14 rounded-2xl flex items-center justify-center shrink-0 relative overflow-hidden"
            style={{
              background: `linear-gradient(135deg, ${hex}, ${hex}cc)`,
              boxShadow: `0 8px 24px ${hex}60, 0 0 0 1px ${hex}30`,
            }}
          >
            <div
              className="absolute inset-0"
              style={{ background: 'linear-gradient(135deg, rgba(255,255,255,0.18), transparent)' }}
            />
            <Icon size={24} strokeWidth={1.75} color="white" style={{ position: 'relative', zIndex: 1 }} />
          </div>
        )}
      </div>
    </div>
  )
}
