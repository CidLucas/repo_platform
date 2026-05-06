import { useEffect } from 'react'
import { useAppStore, Toast as ToastItem } from '../../store/appStore'

function ToastEntry({ toast }: { toast: ToastItem }) {
  const removeToast = useAppStore(s => s.removeToast)
  const ico: Record<string, string> = { ok: '✅', no: '❌', sn: '⏰' }

  useEffect(() => {
    const timer = setTimeout(() => removeToast(toast.id), 4000)
    return () => clearTimeout(timer)
  }, [toast.id, removeToast])

  return (
    <div className={`toast ${toast.type}`}>
      <span style={{ fontSize: 15 }}>{ico[toast.type]}</span>
      <div>
        <div className="t-ttl">{toast.title}</div>
        <div className="t-msg">{toast.msg}</div>
      </div>
    </div>
  )
}

export default function ToastContainer() {
  const toasts = useAppStore(s => s.toasts)

  return (
    <div id="toasts">
      {toasts.map(t => (
        <ToastEntry key={t.id} toast={t} />
      ))}
    </div>
  )
}
