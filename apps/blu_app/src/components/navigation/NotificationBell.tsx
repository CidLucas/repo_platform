import { useState, useRef, useEffect } from 'react'
import { Bell } from 'lucide-react'
import { cn } from '@/utils/cn'
import { useNotificationContext } from '@/hooks/useNotificationContext'
import { NotificationDropdown } from './NotificationDropdown'

interface NotificationBellProps {
  className?: string
}

export function NotificationBell({ className }: NotificationBellProps) {
  const { unreadCount, criticalCount } = useNotificationContext()
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  // Close on outside click
  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (!containerRef.current?.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label={`Notificações${unreadCount > 0 ? ` (${unreadCount} não lidas)` : ''}`}
        className={cn(
          'relative flex items-center justify-center w-9 h-9 rounded',
          'text-gray-300 hover:text-white hover:bg-elevated',
          'transition-colors duration-normal cursor-pointer',
          'focus-visible:ring-2 focus-visible:ring-blu-500 focus-visible:outline-none'
        )}
      >
        <Bell size={18} strokeWidth={1.5} />

        {/* Unread badge */}
        {unreadCount > 0 && (
          <span
            className={cn(
              'absolute -top-0.5 -right-0.5',
              'flex items-center justify-center',
              'min-w-[16px] h-4 rounded-full px-1',
              'text-caption-sm font-medium text-white leading-none',
              criticalCount > 0
                ? 'bg-urgent animate-orb-attention'
                : 'bg-blu-500'
            )}
          >
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <NotificationDropdown onClose={() => setOpen(false)} />
      )}
    </div>
  )
}
