import { cn } from '@/utils/cn'

type AvatarSize = 'sm' | 'md' | 'lg'

interface AvatarProps {
  src?: string
  name?: string
  size?: AvatarSize
  className?: string
}

const sizeClasses: Record<AvatarSize, string> = {
  sm: 'w-8 h-8 text-caption',
  md: 'w-10 h-10 text-body-sm',
  lg: 'w-14 h-14 text-body',
}

function getInitials(name?: string): string {
  if (!name) return '?'
  const words = name.trim().split(/\s+/)
  if (words.length === 1) return words[0][0]?.toUpperCase() ?? '?'
  return (
    (words[0][0]?.toUpperCase() ?? '') +
    (words[words.length - 1][0]?.toUpperCase() ?? '')
  )
}

export function Avatar({ src, name, size = 'md', className }: AvatarProps) {
  const sizeClass = sizeClasses[size]

  if (src) {
    return (
      <img
        src={src}
        alt={name ?? 'Avatar'}
        className={cn(
          'rounded-full object-cover shrink-0 select-none',
          sizeClass,
          className
        )}
      />
    )
  }

  return (
    <div
      className={cn(
        'rounded-full bg-blu-500/20 text-blu-300 font-medium',
        'flex items-center justify-center shrink-0 select-none uppercase',
        sizeClass,
        className
      )}
      aria-label={name ? `Avatar de ${name}` : 'Avatar'}
    >
      {getInitials(name)}
    </div>
  )
}
