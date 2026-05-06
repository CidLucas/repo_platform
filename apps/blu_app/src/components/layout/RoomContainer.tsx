import { type ReactNode } from 'react'
import { cn } from '@/utils/cn'
import { RoomErrorBoundary } from './RoomErrorBoundary'

interface RoomContainerProps {
  children: ReactNode
  className?: string
}

/**
 * Wraps every agent room page.
 * - Accounts for navbar height with pt-20
 * - Constrains content width
 * - Wraps in RoomErrorBoundary so crashes stay local
 */
export function RoomContainer({ children, className }: RoomContainerProps) {
  return (
    <RoomErrorBoundary>
      <div
        className={cn(
          'pt-20 px-4 pb-8',
          'max-w-7xl mx-auto w-full',
          className
        )}
      >
        {children}
      </div>
    </RoomErrorBoundary>
  )
}
