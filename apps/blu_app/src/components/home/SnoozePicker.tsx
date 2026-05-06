import { useState, useRef, useEffect } from 'react'
import { X, Clock } from 'lucide-react'
import { cn } from '@/utils/cn'
import { useSnoozeRequest } from '@/hooks/useApproval'
import { useToast } from '@/components/feedback/SuccessToast'
import { snoozeLabel } from '@/utils/format'

interface SnoozePickerProps {
  approvalId: string
  onClose: () => void
  /** On mobile: renders as bottom sheet. On desktop: inline popover above trigger. */
  isMobile?: boolean
}

function getSnoozeOptions(): { label: string; getValue: () => string }[] {
  const now = new Date()
  return [
    {
      label: 'Em 1 hora',
      getValue: () => new Date(now.getTime() + 60 * 60 * 1000).toISOString(),
    },
    {
      label: 'Hoje à tarde',
      getValue: () => {
        const d = new Date(now)
        d.setHours(17, 0, 0, 0)
        if (d <= now) d.setDate(d.getDate() + 1)
        return d.toISOString()
      },
    },
    {
      label: 'Amanhã',
      getValue: () => {
        const d = new Date(now)
        d.setDate(d.getDate() + 1)
        d.setHours(9, 0, 0, 0)
        return d.toISOString()
      },
    },
    {
      label: 'Próxima semana',
      getValue: () => {
        const d = new Date(now)
        d.setDate(d.getDate() + 7)
        d.setHours(9, 0, 0, 0)
        return d.toISOString()
      },
    },
  ]
}

export function SnoozePicker({ approvalId, onClose, isMobile }: SnoozePickerProps) {
  const snooze = useSnoozeRequest()
  const { showToast } = useToast()
  const [showCustom, setShowCustom] = useState(false)
  const [customValue, setCustomValue] = useState('')
  const backdropRef = useRef<HTMLDivElement>(null)

  const options = getSnoozeOptions()

  function handleOption(getValue: () => string) {
    const snoozeUntil = getValue()
    snooze.mutate(
      { id: approvalId, snoozeUntil },
      {
        onSuccess: () => {
          showToast(`Lembrete agendado. Voltarei a isso ${snoozeLabel(snoozeUntil)}.`, {
            variant: 'info',
            duration: 3500,
          })
          onClose()
        },
        onError: onClose,
      }
    )
  }

  function handleCustom() {
    if (!customValue) return
    const snoozeUntil = new Date(customValue).toISOString()
    snooze.mutate(
      { id: approvalId, snoozeUntil },
      {
        onSuccess: () => {
          showToast(`Lembrete agendado. Voltarei a isso ${snoozeLabel(snoozeUntil)}.`, {
            variant: 'info',
            duration: 3500,
          })
          onClose()
        },
        onError: onClose,
      }
    )
  }

  // Close on backdrop click (mobile sheet)
  function handleBackdropClick(e: React.MouseEvent) {
    if (e.target === backdropRef.current) onClose()
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  const content = (
    <div
      className={cn(
        'bg-elevated border border-border rounded-md shadow-lg p-4',
        isMobile ? 'w-full rounded-b-none' : 'w-56'
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-body-sm font-medium text-white flex items-center gap-2">
          <Clock size={14} className="text-gray-300" />
          Adiar para
        </span>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-white transition-colors cursor-pointer p-1 -mr-1 rounded"
          aria-label="Fechar"
        >
          <X size={14} />
        </button>
      </div>

      <div className="space-y-1">
        {options.map((opt) => (
          <button
            key={opt.label}
            onClick={() => handleOption(opt.getValue)}
            disabled={snooze.isPending}
            className={cn(
              'w-full text-left px-3 py-2 rounded text-body-sm',
              'text-gray-200 hover:bg-surface hover:text-white',
              'transition-colors cursor-pointer disabled:opacity-50',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500'
            )}
          >
            {opt.label}
          </button>
        ))}

        {!showCustom ? (
          <button
            onClick={() => setShowCustom(true)}
            className={cn(
              'w-full text-left px-3 py-2 rounded text-body-sm',
              'text-blu-400 hover:text-blu-300 hover:bg-surface',
              'transition-colors cursor-pointer',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500'
            )}
          >
            Escolher data →
          </button>
        ) : (
          <div className="pt-1 space-y-2">
            <input
              type="datetime-local"
              value={customValue}
              onChange={(e) => setCustomValue(e.target.value)}
              className={cn(
                'w-full bg-surface border border-border rounded px-2 py-1.5',
                'text-caption text-gray-200',
                'focus:outline-none focus:border-blu-500',
                '[color-scheme:dark]'
              )}
            />
            <button
              onClick={handleCustom}
              disabled={!customValue || snooze.isPending}
              className={cn(
                'w-full px-3 py-1.5 rounded text-body-sm',
                'bg-blu-500 hover:bg-blu-600 text-white',
                'transition-colors cursor-pointer disabled:opacity-50',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500'
              )}
            >
              Confirmar
            </button>
          </div>
        )}
      </div>
    </div>
  )

  if (isMobile) {
    return (
      <div
        ref={backdropRef}
        className="fixed inset-0 z-50 bg-black/60 flex items-end"
        onClick={handleBackdropClick}
        role="dialog"
        aria-modal="true"
        aria-label="Adiar decisão"
      >
        <div className="w-full animate-slide-up">{content}</div>
      </div>
    )
  }

  return (
    <div className="absolute bottom-full left-0 mb-2 z-10 animate-slide-up">
      {content}
    </div>
  )
}
