import { type KeyboardEvent } from 'react'
import { cn } from '@/utils/cn'

interface ToggleProps {
  checked: boolean
  onChange: (checked: boolean) => void
  label?: string
  disabled?: boolean
  className?: string
}

export function Toggle({ checked, onChange, label, disabled, className }: ToggleProps) {
  function handleKeyDown(e: KeyboardEvent<HTMLButtonElement>) {
    if (e.key === ' ') {
      e.preventDefault()
      if (!disabled) onChange(!checked)
    }
  }

  return (
    <div className={cn('min-h-[44px] flex items-center gap-3', className)}>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={disabled}
        onClick={() => !disabled && onChange(!checked)}
        onKeyDown={handleKeyDown}
        className={cn(
          'relative inline-flex items-center w-11 h-6 rounded-full',
          'transition-colors duration-normal',
          'focus-visible:ring-2 focus-visible:ring-blu-500 focus-visible:ring-offset-1 focus-visible:ring-offset-base',
          'focus-visible:outline-none cursor-pointer',
          checked ? 'bg-blu-500' : 'bg-gray-600',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      >
        <span
          className={cn(
            'absolute w-4 h-4 bg-white rounded-full shadow',
            'transition-transform duration-normal',
            checked ? 'translate-x-6' : 'translate-x-1'
          )}
        />
      </button>

      {label && (
        <span
          className={cn(
            'text-body-sm select-none',
            disabled ? 'text-gray-400' : 'text-gray-200'
          )}
        >
          {label}
        </span>
      )}
    </div>
  )
}
