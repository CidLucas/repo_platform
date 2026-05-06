import {
  useRef,
  useState,
  type ReactNode,
  type PointerEvent as ReactPointerEvent,
} from 'react'
import { CheckCircle, X } from 'lucide-react'
import { cn } from '@/utils/cn'

interface SwipeableCardProps {
  children: ReactNode
  onSwipeRight: () => void
  onSwipeLeft: () => void
  /** Pixels required to trigger a swipe action. Default: 80 */
  threshold?: number
  /** Show drag handles on first card (first-use hint) */
  showHint?: boolean
  className?: string
}

/**
 * Swipeable card using native pointer events + CSS transform.
 * Right swipe = Aprovar (green overlay)
 * Left swipe = Rejeitar (red overlay)
 *
 * touch-action: pan-y — prevents iOS browser back-navigation conflict.
 * No animation libraries used.
 */
export function SwipeableCard({
  children,
  onSwipeRight,
  onSwipeLeft,
  threshold = 80,
  showHint = false,
  className,
}: SwipeableCardProps) {
  const cardRef = useRef<HTMLDivElement>(null)
  const startXRef = useRef(0)
  const [deltaX, setDeltaX] = useState(0)
  const [isDragging, setIsDragging] = useState(false)

  /** Fraction: -1 (full left) to 1 (full right) */
  const fraction = Math.max(-1, Math.min(1, deltaX / threshold))
  const rightProgress = Math.max(0, fraction) // 0–1
  const leftProgress = Math.max(0, -fraction) // 0–1

  function onPointerDown(e: ReactPointerEvent<HTMLDivElement>) {
    // Only single-touch or mouse left button
    if (e.pointerType === 'mouse' && e.button !== 0) return
    startXRef.current = e.clientX
    setIsDragging(true)
    cardRef.current?.setPointerCapture(e.pointerId)
  }

  function onPointerMove(e: ReactPointerEvent<HTMLDivElement>) {
    if (!isDragging) return
    const dx = e.clientX - startXRef.current
    setDeltaX(dx)
  }

  function onPointerUp() {
    if (!isDragging) return
    setIsDragging(false)

    if (deltaX >= threshold) {
      onSwipeRight()
    } else if (deltaX <= -threshold) {
      onSwipeLeft()
    }

    // Snap back
    setDeltaX(0)
  }

  return (
    <div
      className={cn('relative overflow-hidden rounded-md', className)}
      style={{ touchAction: 'pan-y' }}
    >
      {/* Green (Aprovar) overlay */}
      <div
        aria-hidden
        className={cn(
          'absolute inset-0 z-10 flex items-center justify-start pl-6',
          'bg-ok rounded-md pointer-events-none'
        )}
        style={{ opacity: rightProgress }}
      >
        <CheckCircle size={28} className="text-white" />
        <span className="ml-2 text-body font-semibold text-white">Aprovar</span>
      </div>

      {/* Red (Rejeitar) overlay */}
      <div
        aria-hidden
        className={cn(
          'absolute inset-0 z-10 flex items-center justify-end pr-6',
          'bg-urgent rounded-md pointer-events-none'
        )}
        style={{ opacity: leftProgress }}
      >
        <span className="mr-2 text-body font-semibold text-white">Rejeitar</span>
        <X size={28} className="text-white" />
      </div>

      {/* First-use drag hint (drag handle icons) */}
      {showHint && (
        <div
          aria-hidden
          className="absolute left-2 top-1/2 -translate-y-1/2 z-20 text-gray-500 pointer-events-none select-none text-caption-sm"
          style={{ writingMode: 'vertical-rl', letterSpacing: '2px' }}
        >
          ⋮⋮
        </div>
      )}

      {/* Card content — translated with pointer drag */}
      <div
        ref={cardRef}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        className={cn(
          'relative z-20 cursor-grab select-none',
          isDragging ? 'cursor-grabbing' : ''
        )}
        style={{
          transform: `translateX(${deltaX}px)`,
          transition: isDragging ? 'none' : 'transform 300ms ease-out',
          willChange: 'transform',
        }}
      >
        {children}
      </div>
    </div>
  )
}
