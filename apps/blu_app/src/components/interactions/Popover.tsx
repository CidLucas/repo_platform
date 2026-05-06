import { type ReactNode } from 'react'
import * as RadixPopover from '@radix-ui/react-popover'
import { cn } from '@/utils/cn'

interface PopoverProps {
  trigger: ReactNode
  children: ReactNode
  side?: 'top' | 'bottom' | 'left' | 'right'
  align?: 'start' | 'center' | 'end'
  sideOffset?: number
  className?: string
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

/**
 * Click-triggered accessible popover via @radix-ui/react-popover.
 * Closes on outside click. Focus is trapped while open.
 */
export function Popover({
  trigger,
  children,
  side = 'bottom',
  align = 'start',
  sideOffset = 6,
  className,
  open,
  onOpenChange,
}: PopoverProps) {
  return (
    <RadixPopover.Root open={open} onOpenChange={onOpenChange}>
      <RadixPopover.Trigger asChild>{trigger}</RadixPopover.Trigger>
      <RadixPopover.Portal>
        <RadixPopover.Content
          side={side}
          align={align}
          sideOffset={sideOffset}
          className={cn(
            'z-50 outline-none',
            'bg-elevated border border-border rounded-md shadow-lg',
            'p-2 min-w-[180px]',
            'data-[state=open]:animate-fade-in',
            'data-[state=closed]:opacity-0',
            'transition-opacity duration-fast',
            className
          )}
        >
          {children}
          <RadixPopover.Arrow className="fill-border" />
        </RadixPopover.Content>
      </RadixPopover.Portal>
    </RadixPopover.Root>
  )
}

/**
 * A single item inside a Popover menu.
 */
export function PopoverItem({
  children,
  onClick,
  variant = 'default',
  disabled,
}: {
  children: ReactNode
  onClick?: () => void
  variant?: 'default' | 'danger'
  disabled?: boolean
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'w-full flex items-center gap-2 px-3 py-2 rounded text-body-sm text-left',
        'transition-colors duration-fast cursor-pointer',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500',
        variant === 'danger'
          ? 'text-urgent hover:bg-urgent/10'
          : 'text-gray-200 hover:bg-surface hover:text-white',
        disabled && 'opacity-40 cursor-not-allowed pointer-events-none'
      )}
    >
      {children}
    </button>
  )
}
