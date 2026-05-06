import { type InputHTMLAttributes, type ReactNode, useId } from 'react'
import { cn } from '@/utils/cn'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?: string
  leftIcon?: ReactNode
  rightIcon?: ReactNode
}

export function Input({
  label,
  error,
  hint,
  leftIcon,
  rightIcon,
  disabled,
  className,
  id: externalId,
  ...props
}: InputProps) {
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
        {leftIcon && (
          <span className="absolute left-3 text-gray-400 pointer-events-none flex items-center">
            {leftIcon}
          </span>
        )}

        <input
          id={id}
          disabled={disabled}
          className={cn(
            // Base
            'bg-elevated border border-border rounded text-white',
            'placeholder-gray-400 text-body-sm w-full',
            'transition-colors duration-normal',
            'focus:outline-none',
            // Padding adjusts for icons
            leftIcon ? 'pl-9' : 'px-3',
            rightIcon ? 'pr-9' : 'px-3',
            'py-2',
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
        />

        {rightIcon && (
          <span className="absolute right-3 text-gray-400 pointer-events-none flex items-center">
            {rightIcon}
          </span>
        )}
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
