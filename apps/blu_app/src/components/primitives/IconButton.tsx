import { type ButtonHTMLAttributes, type ReactNode } from 'react'
import { cn } from '@/utils/cn'

type IconButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
type IconButtonSize = 'sm' | 'md' | 'lg'

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  'aria-label': string
  variant?: IconButtonVariant
  size?: IconButtonSize
  children: ReactNode
}

const variantClasses: Record<IconButtonVariant, string> = {
  primary:
    'bg-blu-500 hover:bg-blu-600 text-white border border-transparent',
  secondary:
    'bg-elevated border border-border hover:border-blu-500 text-white',
  ghost:
    'bg-transparent hover:bg-elevated text-gray-200 hover:text-white border border-transparent',
  danger:
    'bg-urgent/10 hover:bg-urgent/20 text-urgent border border-urgent/30',
}

const sizeClasses: Record<IconButtonSize, string> = {
  sm: 'p-1.5',
  md: 'p-2',
  lg: 'p-3',
}

export function IconButton({
  variant = 'ghost',
  size = 'md',
  disabled,
  children,
  className,
  ...props
}: IconButtonProps) {
  return (
    <button
      disabled={disabled}
      className={cn(
        // Base — min 44×44px touch target
        'inline-flex items-center justify-center rounded',
        'min-w-[44px] min-h-[44px]',
        'transition-all duration-fast cursor-pointer',
        // Focus ring
        'focus-visible:ring-2 focus-visible:ring-blu-500 focus-visible:ring-offset-1 focus-visible:ring-offset-base',
        // Scale press
        'active:scale-[0.95]',
        // Disabled
        disabled && 'opacity-75 cursor-not-allowed pointer-events-none',
        // Variant + size
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
      {...props}
    >
      {children}
    </button>
  )
}
