import { cn } from '@/utils/cn'

interface SkeletonCardProps {
  className?: string
  lines?: number
}

/**
 * Shimmer skeleton card for loading states.
 * Uses the `shimmer` keyframe defined in tailwind.config.js.
 */
export function SkeletonCard({ className, lines = 3 }: SkeletonCardProps) {
  return (
    <div
      className={cn(
        'bg-surface border border-border rounded-md p-4 space-y-3',
        className
      )}
      aria-hidden="true"
    >
      {/* Header row */}
      <div className="flex items-center gap-3">
        <SkeletonPulse className="w-6 h-6 rounded-full" />
        <SkeletonPulse className="h-4 w-24 rounded" />
        <SkeletonPulse className="h-4 w-12 rounded ml-auto" />
      </div>
      {/* Text lines */}
      {Array.from({ length: lines }).map((_, i) => (
        <SkeletonPulse
          key={i}
          className={cn('h-3 rounded', i === lines - 1 ? 'w-2/3' : 'w-full')}
        />
      ))}
      {/* Action row */}
      <div className="flex gap-2 pt-1">
        <SkeletonPulse className="h-8 w-20 rounded" />
        <SkeletonPulse className="h-8 w-16 rounded" />
        <SkeletonPulse className="h-8 w-16 rounded" />
      </div>
    </div>
  )
}

function SkeletonPulse({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'bg-elevated',
        'animate-shimmer',
        '[background-image:linear-gradient(90deg,transparent_0%,rgba(255,255,255,0.04)_50%,transparent_100%)]',
        '[background-size:200%_100%]',
        className
      )}
    />
  )
}
