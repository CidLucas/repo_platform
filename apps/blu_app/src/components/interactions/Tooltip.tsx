import { type ReactNode } from 'react'
import * as RadixTooltip from '@radix-ui/react-tooltip'
import { cn } from '@/utils/cn'

interface TooltipProps {
  content: ReactNode
  children: ReactNode
  side?: 'top' | 'bottom' | 'left' | 'right'
  /** Delay in ms before tooltip appears. Default: 300ms per design spec. */
  delayDuration?: number
  className?: string
}

/**
 * Accessible tooltip via @radix-ui/react-tooltip.
 * Default 300ms hover delay. Positioned and ARIA-managed automatically.
 */
export function Tooltip({
  content,
  children,
  side = 'top',
  delayDuration = 300,
  className,
}: TooltipProps) {
  return (
    <RadixTooltip.Provider delayDuration={delayDuration} skipDelayDuration={0}>
      <RadixTooltip.Root>
        <RadixTooltip.Trigger asChild>{children}</RadixTooltip.Trigger>
        <RadixTooltip.Portal>
          <RadixTooltip.Content
            side={side}
            sideOffset={6}
            className={cn(
              'z-50 px-3 py-1.5 rounded',
              'bg-elevated border border-border shadow-md',
              'text-caption text-gray-200 leading-tight',
              'max-w-[220px] text-center',
              // Animate
              'data-[state=delayed-open]:animate-fade-in',
              'data-[state=closed]:opacity-0',
              'transition-opacity duration-fast',
              className
            )}
          >
            {content}
            <RadixTooltip.Arrow className="fill-elevated" />
          </RadixTooltip.Content>
        </RadixTooltip.Portal>
      </RadixTooltip.Root>
    </RadixTooltip.Provider>
  )
}
