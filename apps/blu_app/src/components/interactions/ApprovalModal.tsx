import { useEffect, useCallback } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { X, ChevronLeft, ChevronRight } from 'lucide-react'
import { cn } from '@/utils/cn'
import { ApprovalCard } from '@/components/home/ApprovalCard'
import type { ApprovalRequest } from '@/types/approval'
import { useApproveRequest } from '@/hooks/useApproval'

interface ApprovalModalProps {
  approval: ApprovalRequest | null
  approvals?: ApprovalRequest[]
  open: boolean
  onClose: () => void
  /** Navigate to adjacent approval index */
  onNavigate?: (direction: 'prev' | 'next') => void
  currentIndex?: number
}

export function ApprovalModal({
  approval,
  approvals = [],
  open,
  onClose,
  onNavigate,
  currentIndex = 0,
}: ApprovalModalProps) {
  const approve = useApproveRequest()
  const total = approvals.length
  const hasPrev = total > 1 && currentIndex > 0
  const hasNext = total > 1 && currentIndex < total - 1

  // Keyboard shortcuts: Enter = Aprovar, j = next, k = prev
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!open || !approval) return

      if (e.key === 'Enter' && !e.metaKey && !e.ctrlKey) {
        const activeTag = document.activeElement?.tagName
        // Don't intercept Enter on buttons/inputs
        if (activeTag !== 'BUTTON' && activeTag !== 'INPUT' && activeTag !== 'TEXTAREA') {
          e.preventDefault()
          approve.mutate(approval.id, { onSuccess: onClose })
        }
      }

      if (e.key === 'j' || e.key === 'ArrowDown') {
        if (hasNext) {
          e.preventDefault()
          onNavigate?.('next')
        }
      }

      if (e.key === 'k' || e.key === 'ArrowUp') {
        if (hasPrev) {
          e.preventDefault()
          onNavigate?.('prev')
        }
      }
    },
    [open, approval, approve, onClose, onNavigate, hasNext, hasPrev]
  )

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  return (
    <Dialog.Root open={open} onOpenChange={(v) => !v && onClose()}>
      <Dialog.Portal>
        {/* Backdrop */}
        <Dialog.Overlay
          className={cn(
            'fixed inset-0 z-40 bg-black/70 backdrop-blur-sm',
            'data-[state=open]:animate-fade-in data-[state=closed]:animate-fade-out'
          )}
        />

        {/* Panel */}
        <Dialog.Content
          className={cn(
            // Mobile: full-screen
            'fixed inset-0 z-50 flex flex-col bg-base outline-none',
            // Desktop: centered modal
            'md:inset-auto md:left-1/2 md:top-1/2 md:-translate-x-1/2 md:-translate-y-1/2',
            'md:w-full md:max-w-xl md:max-h-[90dvh] md:rounded-lg md:shadow-xl',
            'md:bg-surface md:border md:border-border',
            'data-[state=open]:animate-slide-up data-[state=closed]:opacity-0'
          )}
          aria-label={approval?.title ?? 'Decisão'}
        >
          {/* Header bar */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
            <div className="flex items-center gap-3">
              <Dialog.Title className="text-body font-medium text-white">
                Decisão
              </Dialog.Title>
              {total > 1 && (
                <span className="text-caption text-gray-400">
                  {currentIndex + 1} / {total}
                </span>
              )}
            </div>

            <div className="flex items-center gap-1">
              {/* j/k nav arrows (desktop power-user) */}
              {total > 1 && (
                <div className="hidden md:flex items-center gap-1 mr-2">
                  <button
                    onClick={() => onNavigate?.('prev')}
                    disabled={!hasPrev}
                    className={cn(
                      'p-1.5 rounded text-gray-400 transition-colors cursor-pointer',
                      'hover:text-white hover:bg-elevated',
                      'disabled:opacity-30 disabled:cursor-not-allowed',
                      'focus-visible:ring-2 focus-visible:ring-blu-500 outline-none'
                    )}
                    aria-label="Decisão anterior (k)"
                    title="Anterior (k)"
                  >
                    <ChevronLeft size={16} />
                  </button>
                  <button
                    onClick={() => onNavigate?.('next')}
                    disabled={!hasNext}
                    className={cn(
                      'p-1.5 rounded text-gray-400 transition-colors cursor-pointer',
                      'hover:text-white hover:bg-elevated',
                      'disabled:opacity-30 disabled:cursor-not-allowed',
                      'focus-visible:ring-2 focus-visible:ring-blu-500 outline-none'
                    )}
                    aria-label="Próxima decisão (j)"
                    title="Próxima (j)"
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              )}

              <Dialog.Close asChild>
                <button
                  className={cn(
                    'p-1.5 rounded text-gray-400 hover:text-white transition-colors cursor-pointer',
                    'focus-visible:ring-2 focus-visible:ring-blu-500 outline-none'
                  )}
                  aria-label="Fechar (Esc)"
                >
                  <X size={18} />
                </button>
              </Dialog.Close>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4 md:p-6">
            {approval && (
              <ApprovalCard approval={approval} onCollapse={onClose} />
            )}
          </div>

          {/* Desktop keyboard hint */}
          <div className="hidden md:flex items-center gap-4 px-6 py-2 border-t border-border shrink-0">
            <span className="text-caption-sm text-gray-500">
              <kbd className="px-1 py-0.5 bg-elevated border border-border rounded text-caption-sm">Enter</kbd>
              {' '}Aprovar
            </span>
            {total > 1 && (
              <span className="text-caption-sm text-gray-500">
                <kbd className="px-1 py-0.5 bg-elevated border border-border rounded text-caption-sm">j</kbd>
                {'/'}
                <kbd className="px-1 py-0.5 bg-elevated border border-border rounded text-caption-sm">k</kbd>
                {' '}Navegar
              </span>
            )}
            <span className="text-caption-sm text-gray-500">
              <kbd className="px-1 py-0.5 bg-elevated border border-border rounded text-caption-sm">Esc</kbd>
              {' '}Fechar
            </span>
          </div>

          {/* Mobile nav arrows */}
          {total > 1 && (
            <div className="flex md:hidden items-center justify-between px-4 py-3 border-t border-border shrink-0">
              <button
                onClick={() => onNavigate?.('prev')}
                disabled={!hasPrev}
                className={cn(
                  'flex items-center gap-1.5 px-3 py-2 rounded text-body-sm',
                  'text-gray-300 hover:text-white hover:bg-elevated transition-colors cursor-pointer',
                  'disabled:opacity-30 disabled:cursor-not-allowed'
                )}
              >
                <ChevronLeft size={16} /> Anterior
              </button>
              <span className="text-caption text-gray-500">
                {currentIndex + 1} de {total}
              </span>
              <button
                onClick={() => onNavigate?.('next')}
                disabled={!hasNext}
                className={cn(
                  'flex items-center gap-1.5 px-3 py-2 rounded text-body-sm',
                  'text-gray-300 hover:text-white hover:bg-elevated transition-colors cursor-pointer',
                  'disabled:opacity-30 disabled:cursor-not-allowed'
                )}
              >
                Próxima <ChevronRight size={16} />
              </button>
            </div>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
