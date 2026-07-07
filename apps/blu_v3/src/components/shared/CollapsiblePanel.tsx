import { useState, useCallback, useEffect } from 'react'
import { useAuth } from '@blu/auth'

interface Props {
  id: string
  icon?: string
  title: string
  badge?: React.ReactNode
  action?: React.ReactNode
  defaultOpen?: boolean
  style?: React.CSSProperties
  children: React.ReactNode
}

export default function CollapsiblePanel({
  id, icon, title, badge, action, defaultOpen = true, style, children,
}: Props) {
  const { clientId } = useAuth()
  const [open, setOpen] = useState(defaultOpen)

  // Read scoped preference once clientId resolves
  useEffect(() => {
    if (!clientId) return
    try {
      const v = localStorage.getItem(`panel:${clientId}:${id}`)
      if (v !== null) setOpen(v === 'true')
    } catch {}
  }, [clientId, id])

  const toggle = useCallback(() => {
    setOpen(o => {
      const next = !o
      try {
        if (clientId) localStorage.setItem(`panel:${clientId}:${id}`, String(next))
      } catch {}
      return next
    })
  }, [clientId, id])

  return (
    <div className={`panel${open ? '' : ' collapsed'}`} style={style}>
      <div className="ph" onClick={toggle} style={{ cursor: 'pointer' }}>
        {icon && <span className="ph-ico">{icon}</span>}
        <span className="ph-ttl">{title}</span>
        {badge}
        {action && <span onClick={e => e.stopPropagation()}>{action}</span>}
        <span className="ph-toggle">▾</span>
      </div>
      <div className="pb">
        {children}
      </div>
    </div>
  )
}
