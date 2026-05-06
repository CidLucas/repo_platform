import { type ButtonHTMLAttributes, type ReactNode } from 'react'
import { cn } from '@/utils/cn'
import { Spinner } from './Spinner'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
type ButtonSize = 'sm' | 'md' | 'lg'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  leftIcon?: ReactNode
  rightIcon?: ReactNode
  children?: ReactNode
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'bg-blu-500 hover:bg-blu-600 text-white border border-transparent',
  secondary:
    'bg-elevated border border-border hover:border-blu-500 text-white',
  ghost:
    'bg-transparent hover:bg-elevated text-gray-200 hover:text-white border border-transparent',
  danger:
    'bg-urgent/10 hover:bg-urgent/20 text-urgent border border-urgent/30',
}

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-caption gap-1.5',
  md: 'px-4 py-2 text-body-sm gap-2',
  lg: 'px-6 py-3 text-body gap-2',
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled,
  leftIcon,
  rightIcon,
  children,
  className,
  ...props
}: ButtonProps) {
  const isDisabled = disabled || loading

  return (
    <button
      disabled={isDisabled}
      className={cn(
        // Base
        'inline-flex items-center justify-center rounded font-medium',
        'transition-all duration-fast cursor-pointer',
        // Focus ring
        'focus-visible:ring-2 focus-visible:ring-blu-500 focus-visible:ring-offset-1 focus-visible:ring-offset-base',
        // Scale press
        'active:scale-[0.98] transition-transform',
        // Disabled
        isDisabled && 'opacity-75 cursor-not-allowed pointer-events-none',
        // Variant + size
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
      {...props}
    >
      {loading ? (
        <Spinner size="sm" className="text-current" />
      ) : (
        leftIcon && <span className="shrink-0">{leftIcon}</span>
      )}
      {children && <span>{children}</span>}
      {!loading && rightIcon && <span className="shrink-0">{rightIcon}</span>}
    </button>
  )
}
