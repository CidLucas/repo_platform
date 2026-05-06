import { type SVGProps } from 'react'
import { cn } from '@/utils/cn'
import type { OrbShape, AgentStatus } from '@/types/agent'

interface AgentBadgeProps {
  shape: OrbShape
  color: string
  glowColor: string
  name?: string
  status?: AgentStatus
  size?: number
  className?: string
}

/** Inline SVG orbs for each agent shape */
function OrbSvg({
  shape,
  color,
  glowColor,
  size,
  status,
}: {
  shape: OrbShape
  color: string
  glowColor: string
  size: number
  status: AgentStatus
} & SVGProps<SVGSVGElement>) {
  const animClass =
    status === 'working'
      ? 'animate-orb-pulse'
      : status === 'attention'
      ? 'animate-orb-attention'
      : status === 'offline'
      ? 'opacity-30'
      : 'animate-orb-idle'

  const s = size
  const cx = s / 2
  const cy = s / 2
  const r = s * 0.4

  const shapeEl = (() => {
    switch (shape) {
      case 'circle':
        return <circle cx={cx} cy={cy} r={r} />
      case 'square':
        return (
          <rect
            x={cx - r * 0.85}
            y={cy - r * 0.85}
            width={r * 1.7}
            height={r * 1.7}
          />
        )
      case 'diamond': {
        const d = r * 0.95
        return (
          <polygon
            points={`${cx},${cy - d} ${cx + d},${cy} ${cx},${cy + d} ${cx - d},${cy}`}
          />
        )
      }
      case 'triangle': {
        const h = r * 1.1
        return (
          <polygon
            points={`${cx},${cy - h} ${cx + h * 0.9},${cy + h * 0.55} ${cx - h * 0.9},${cy + h * 0.55}`}
          />
        )
      }
      case 'hexagon': {
        const pts = Array.from({ length: 6 }, (_, i) => {
          const angle = (Math.PI / 3) * i - Math.PI / 6
          return `${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}`
        }).join(' ')
        return <polygon points={pts} />
      }
      case 'pentagon': {
        const pts = Array.from({ length: 5 }, (_, i) => {
          const angle = (2 * Math.PI * i) / 5 - Math.PI / 2
          return `${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}`
        }).join(' ')
        return <polygon points={pts} />
      }
    }
  })()

  return (
    <svg
      width={s}
      height={s}
      viewBox={`0 0 ${s} ${s}`}
      className={cn('shrink-0', animClass)}
      style={{ filter: `drop-shadow(0 0 ${s * 0.45}px ${glowColor})` }}
    >
      <defs>
        <radialGradient id={`orb-grad-${shape}-${color.replace('#', '')}`} cx="40%" cy="35%" r="65%">
          <stop offset="0%" stopColor={color} stopOpacity="1" />
          <stop offset="100%" stopColor={color} stopOpacity="0.5" />
        </radialGradient>
      </defs>
      <g fill={`url(#orb-grad-${shape}-${color.replace('#', '')})`}>{shapeEl}</g>
    </svg>
  )
}

export function AgentBadge({
  shape,
  color,
  glowColor,
  name,
  status = 'idle',
  size = 20,
  className,
}: AgentBadgeProps) {
  return (
    <span className={cn('inline-flex items-center gap-2', className)}>
      <OrbSvg
        shape={shape}
        color={color}
        glowColor={glowColor}
        size={size}
        status={status}
      />
      {name && (
        <span className="text-heading-sm font-medium" style={{ color }}>
          {name}
        </span>
      )}
    </span>
  )
}
