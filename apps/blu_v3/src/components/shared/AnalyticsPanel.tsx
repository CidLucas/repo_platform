import { useState } from 'react'

export interface AnalyticsPanelProps {
  title: string
  period: string
  onPeriodChange: (p: string) => void
  children?: React.ReactNode
  defaultOpen?: boolean
  kpis: Array<{ label: string; value: string | number; color?: string }>
}

export default function AnalyticsPanel(props: AnalyticsPanelProps) {
  const { title, kpis, period, onPeriodChange, children, defaultOpen = false } = props
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className="anl-card">
      <div className="anl-hd" onClick={() => setOpen(o => !o)}>
        <span className="anl-ttl">{title}</span>
        <div className="anl-nums">
          {kpis.map((kpi, i) => (
            <div key={i} className="anl-kpi">
              <span className="anl-v" style={kpi.color ? { color: kpi.color } : undefined}>
                {kpi.value}
              </span>
              <span className="anl-l">{kpi.label}</span>
            </div>
          ))}
        </div>
        <span className={`anl-chev${open ? ' open' : ''}`}>▶</span>
      </div>
      <div style={{ display: 'flex', gap: 4, padding: '0 12px 8px' }}>
        {(['30d', '90d', '1y'] as const).map(p => (
          <span
            key={p}
            className={`pill${period === p ? ' on' : ''}`}
            style={{ cursor: 'pointer' }}
            onClick={() => onPeriodChange(p)}
          >
            {p === '30d' ? '30d' : p === '90d' ? '90d' : '1 ano'}
          </span>
        ))}
      </div>
      <div className={`anl-body${open ? ' open' : ''}`}>
        {children}
      </div>
    </div>
  )
}
