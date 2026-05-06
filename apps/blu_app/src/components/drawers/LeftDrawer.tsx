import { type ReactNode } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import { cn } from '@/utils/cn'
import { DrawerHeader } from './DrawerHeader'

interface LeftDrawerProps {
  title: string
  children: ReactNode
  /** Desktop: is panel collapsed */
  collapsed?: boolean
  onCollapse?: () => void
  /** Mobile: is bottom sheet open */
  mobileOpen: boolean
  onMobileClose: () => void
  /** Label shown on the pill button (mobile) */
  pillLabel?: string
  /** Icon for the pill button */
  pillIcon?: ReactNode
  /** Slot for header actions (e.g. search button) */
  headerActions?: ReactNode
  /** When false the desktop persistent panel is hidden (mobile sheet still works) */
  showDesktopPanel?: boolean
  className?: string
}

/**
 * Left drawer panel.
 * - Desktop (lg+): Persistent sidebar on the left, collapsible
 * - Mobile: Pill button triggers slide-up bottom sheet via Radix Dialog
 */
export function LeftDrawer({
  title,
  children,
  collapsed = false,
  onCollapse,
  mobileOpen,
  onMobileClose,
  headerActions,
  showDesktopPanel = true,
  className,
}: LeftDrawerProps) {
  return (
    <>
      {/* ── Desktop panel ─────────────────────────── */}
      <aside
        className={cn(
          'flex-col bg-gray-900 border-r border-border',
          'transition-all duration-slow ease-in-out',
          collapsed ? 'w-0 overflow-hidden opacity-0' : 'w-64',
          showDesktopPanel ? 'hidden lg:flex' : 'hidden',
          className
        )}
      >
        {!collapsed && (
          <>
            <DrawerHeader
              title={title}
              side="left"
              onCollapse={onCollapse}
              collapsed={collapsed}
              actions={headerActions}
            />
            <div className="flex-1 overflow-y-auto scroll-container">
              {children}
            </div>
          </>
        )}
      </aside>

      {/* ── Mobile bottom sheet ────────────────────── */}
      <Dialog.Root open={mobileOpen} onOpenChange={(o) => !o && onMobileClose()}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-base/60 backdrop-blur-sm z-overlay lg:hidden" />
          <Dialog.Content
            className={cn(
              'fixed bottom-0 left-0 right-0 z-modal lg:hidden',
              'bg-gray-900 border-t border-border rounded-t-lg',
              'max-h-[80dvh] flex flex-col',
              'animate-slide-up',
              'focus:outline-none'
            )}
          >
            {/* Drag handle */}
            <div className="flex justify-center pt-3 pb-1">
              <div className="w-8 h-1 rounded-full bg-gray-600" />
            </div>

            {/* Header */}
            <div className="flex items-center justify-between px-4 py-2 border-b border-border shrink-0">
              <Dialog.Title className="text-heading-sm text-white font-medium">
                {title}
              </Dialog.Title>
              <Dialog.Close asChild>
                <button
                  aria-label="Fechar"
                  className="w-8 h-8 flex items-center justify-center rounded
                    text-gray-400 hover:text-white hover:bg-elevated
                    transition-colors cursor-pointer
                    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500"
                >
                  <X size={16} />
                </button>
              </Dialog.Close>
            </div>

            {/* Scrollable content */}
            <div className="flex-1 overflow-y-auto scroll-container">
              {children}
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  )
}

/** Pill button that opens the mobile drawer */
export function LeftDrawerPill({
  label = 'Painel',
  icon,
  onClick,
  count,
}: {
  label?: string
  icon?: ReactNode
  onClick: () => void
  count?: number
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-2 px-4 py-2.5 rounded-full min-h-[44px]',
        'bg-surface border border-border text-body-sm text-gray-200',
        'hover:bg-elevated hover:text-white transition-colors cursor-pointer',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500'
      )}
    >
      {icon && <span className="shrink-0 text-gray-400">{icon}</span>}
      <span>{label}</span>
      {count != null && count > 0 && (
        <span className="text-caption-sm text-urgent font-medium ml-1">{count}</span>
      )}
    </button>
  )
}
