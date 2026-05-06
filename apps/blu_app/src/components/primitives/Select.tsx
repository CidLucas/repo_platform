import { type SelectHTMLAttributes, type ReactNode, useId } from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/utils/cn'

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  error?: string
  hint?: string
  children: ReactNode
}

export function Select({
  label,
  error,
  hint,
  disabled,
  className,
  id: externalId,
  children,
  ...props
}: SelectProps) {
  const generatedId = useId()
  const id = externalId ?? generatedId

  return (
    <div className="w-full flex flex-col gap-1">
      {label && (
        <label
          htmlFor={id}
          className="text-caption text-gray-200 font-medium select-none"
        >
          {label}
        </label>
      )}

      <div className="relative flex items-center">
        <select
          id={id}
          disabled={disabled}
          className={cn(
            // Base
            'appearance-none bg-elevated border border-border rounded',
            'text-white px-3 py-2 pr-9 text-body-sm w-full',
            'transition-colors duration-normal',
            'focus:outline-none cursor-pointer',
            // States
            'hover:border-gray-400',
            error
              ? 'border-urgent focus:border-urgent'
              : 'focus:border-blu-500 focus:shadow-glow-blu',
            disabled && 'opacity-50 cursor-not-allowed bg-gray-800',
            className
          )}
          style={
            error
              ? { boxShadow: '0 0 0 3px rgba(224,122,95,0.15)' }
              : undefined
          }
          {...props}
        >
          {children}
        </select>

        <ChevronDown
          className="absolute right-3 w-4 h-4 text-gray-400 pointer-events-none"
          aria-hidden="true"
        />
      </div>

      {error && (
        <p className="text-caption-sm text-urgent" role="alert">
          {error}
        </p>
      )}
      {!error && hint && (
        <p className="text-caption-sm text-gray-400">{hint}</p>
      )}
    </div>
  )
}
