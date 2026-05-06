import type { LucideIcon } from 'lucide-react'

interface AgentIconBoxProps {
  icon: LucideIcon
  color: string
  size?: 'sm' | 'md' | 'lg'
}

const sizeMap = {
  sm: { box: 40, icon: 18 },
  md: { box: 48, icon: 22 },
  lg: { box: 56, icon: 26 },
}

/**
 * Bright gradient icon box for agent room headers and cards.
 * Same treatment as KpiCard icon boxes — full-saturation gradient,
 * dual box-shadow glow, white shimmer overlay.
 */
export function AgentIconBox({ icon: Icon, color, size = 'md' }: AgentIconBoxProps) {
  const { box, icon } = sizeMap[size]

  return (
    <div
      className="rounded-2xl flex items-center justify-center shrink-0 relative overflow-hidden"
      style={{
        width: box,
        height: box,
        background: `linear-gradient(135deg, ${color}, ${color}cc)`,
        boxShadow: `0 8px 24px ${color}70, 0 0 0 1px ${color}40`,
      }}
    >
      {/* White shimmer overlay */}
      <div
        className="absolute inset-0"
        style={{ background: 'linear-gradient(135deg, rgba(255,255,255,0.22), transparent)' }}
      />
      <Icon
        size={icon}
        strokeWidth={1.75}
        color="white"
        style={{ position: 'relative', zIndex: 1 }}
      />
    </div>
  )
}
