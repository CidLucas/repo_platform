import { useState, useCallback } from 'react'

interface Props {
  id: string
  icon?: string
  title: string
  badge?: React.ReactNode
  action?: React.ReactNode
  defaultOpen?: boolean
  children: React.ReactNode
}

export default function CollapsiblePanel({
  id, icon, title, badge, action, defaultOpen = true, children,
}: Props) {
  const [open, setOpen] = useState(() => {
    try {
      const v = localStorage.getItem(`panel:${id}`)
      return v === null ? defaultOpen : v === 'true'
    } catch { return defaultOpen }
  })

  const toggle = useCallback(() => {
    setOpen(o => {
      const next = !o
      try { localStorage.setItem(`panel:${id}`, String(next)) } catch {}
      return next
    })
  }, [id])

  return (
    <div className={`panel${open ? '' : ' collapsed'}`}>
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
