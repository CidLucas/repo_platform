import { useEffect, useState, useCallback, createContext, useContext, type ReactNode } from 'react'
import { cn } from '@/utils/cn'
import { CheckCircle, X } from 'lucide-react'

interface Toast {
  id: string
  message: string
  variant?: 'success' | 'info' | 'warning'
  duration?: number
}

interface ToastContextValue {
  showToast: (message: string, options?: Omit<Toast, 'id' | 'message'>) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const showToast = useCallback(
    (message: string, options: Omit<Toast, 'id' | 'message'> = {}) => {
      const id = Math.random().toString(36).slice(2)
      const toast: Toast = { id, message, duration: 3000, variant: 'success', ...options }
      setToasts((prev) => [...prev, toast])
    },
    []
  )

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {/* Toast stack — bottom of screen */}
      <div
        className="fixed bottom-safe-4 left-1/2 -translate-x-1/2 z-50 flex flex-col gap-2 items-center pointer-events-none"
        style={{ bottom: 'max(1rem, env(safe-area-inset-bottom))' }}
        aria-live="polite"
        aria-atomic="false"
      >
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}

// ── Toast item ────────────────────────────────────────────────────────────────

interface ToastItemProps {
  toast: Toast
  onDismiss: (id: string) => void
}

function ToastItem({ toast, onDismiss }: ToastItemProps) {
  const [visible, setVisible] = useState(false)

  // Slide-up entrance
  useEffect(() => {
    const show = requestAnimationFrame(() => setVisible(true))
    const hide = setTimeout(() => setVisible(false), (toast.duration ?? 3000) - 300)
    const remove = setTimeout(() => onDismiss(toast.id), toast.duration ?? 3000)
    return () => {
      cancelAnimationFrame(show)
      clearTimeout(hide)
      clearTimeout(remove)
    }
  }, [toast, onDismiss])

  const variantClass = {
    success: 'bg-ok text-white',
    info: 'bg-blu-500 text-white',
    warning: 'bg-attention text-black',
  }[toast.variant ?? 'success']

  return (
    <div
      role="status"
      className={cn(
        'flex items-center gap-3 px-4 py-3 rounded-lg shadow-md max-w-sm w-max pointer-events-auto',
        'transition-all duration-200 ease-out',
        variantClass,
        visible ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'
      )}
    >
      {toast.variant !== 'warning' && <CheckCircle size={16} className="shrink-0" />}
      <p className="text-body-sm font-medium">{toast.message}</p>
      <button
        onClick={() => onDismiss(toast.id)}
        aria-label="Fechar notificação"
        className="shrink-0 ml-1 opacity-80 hover:opacity-100 transition-opacity cursor-pointer"
      >
        <X size={14} />
      </button>
    </div>
  )
}

/** Convenience component for inline use (backward compat) */
export function SuccessToast({
  message,
  visible,
  onDismiss,
}: {
  message: string
  visible: boolean
  onDismiss?: () => void
}) {
  useEffect(() => {
    if (!visible) return
    const timer = setTimeout(() => onDismiss?.(), 3000)
    return () => clearTimeout(timer)
  }, [visible, onDismiss])

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        'fixed bottom-6 left-1/2 -translate-x-1/2 z-50',
        'flex items-center gap-3 px-4 py-3 rounded-lg shadow-md',
        'bg-ok text-white max-w-sm',
        'transition-all duration-200 ease-out',
        visible ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0 pointer-events-none'
      )}
    >
      <CheckCircle size={16} className="shrink-0" />
      <p className="text-body-sm font-medium">{message}</p>
      {onDismiss && (
        <button
          onClick={onDismiss}
          aria-label="Fechar"
          className="shrink-0 ml-1 opacity-80 hover:opacity-100 transition-opacity cursor-pointer"
        >
          <X size={14} />
        </button>
      )}
    </div>
  )
}
