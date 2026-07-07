import { useEffect, useCallback, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

interface ModalProps {
  open: boolean
  onClose: () => void
  title?: string
  subtitle?: string
  children: ReactNode
  /** Largura máxima da box (default 420px) */
  width?: string
}

export default function Modal({ open, onClose, title, subtitle, children, width = '420px' }: ModalProps) {
  const handleKey = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') onClose()
  }, [onClose])

  useEffect(() => {
    if (open) {
      document.addEventListener('keydown', handleKey)
      return () => document.removeEventListener('keydown', handleKey)
    }
  }, [open, handleKey])

  const handleBackdrop = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose()
  }

  if (!open) return null

  return createPortal(
    <div className="intg-modal open" onClick={handleBackdrop}>
      <div className="intg-box" style={{ width, maxWidth: '93vw' }}>
        {title && (
          <div style={{ marginBottom: subtitle ? 3 : 17 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700 }}>{title}</h3>
            {subtitle && <p className="msub">{subtitle}</p>}
          </div>
        )}
        {children}
      </div>
    </div>,
    document.body
  )
}
