import CollapsiblePanel from './CollapsiblePanel'
import type { ContextMetricRow } from '../../api/analytics'

function fmtValue(val: number, unit: string): string {
  if (unit === 'R$') {
    if (val >= 1_000_000) return `R$ ${(val / 1_000_000).toFixed(1)}M`
    if (val >= 1_000) return `R$ ${(val / 1_000).toFixed(1)}k`
    return `R$ ${val.toFixed(0)}`
  }
  if (unit === '%') return `${val.toFixed(1)}%`
  return val.toLocaleString('pt-BR')
}

interface Props {
  id: string
  icon?: string
  title: string
  metrics: ContextMetricRow[]
  loading?: boolean
}

export default function KpiMetricsPanel({ id, icon = '📐', title, metrics, loading }: Props) {
  return (
    <CollapsiblePanel id={id} icon={icon} title={title}>
      {loading ? (
        <div style={{ fontSize: 11, color: 'var(--mu)' }}>Carregando…</div>
      ) : metrics.length === 0 ? (
        <div style={{ fontSize: 11, color: 'var(--mu)', textAlign: 'center', padding: '8px 0', lineHeight: 1.5 }}>
          Disponível após a<br />primeira sincronização.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          {metrics.map((m) => (
            <div
              key={m.kpi}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '5px 0',
                borderBottom: '1px solid var(--gb)',
                fontSize: 11.5,
              }}
            >
              <span style={{ flex: 1, color: 'var(--mu2)' }}>{m.label}</span>
              {m.current_value != null ? (
                <span style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--fg)', fontWeight: 500, flexShrink: 0 }}>
                  {fmtValue(m.current_value, m.unit)}
                </span>
              ) : (
                <span style={{ fontSize: 10, color: 'var(--mu)', fontFamily: 'var(--mono)', flexShrink: 0 }}>—</span>
              )}
              {m.mom_pct != null && (
                <span style={{
                  fontSize: 9,
                  fontFamily: 'var(--mono)',
                  color: m.mom_pct >= 0 ? 'var(--ok)' : 'var(--urg)',
                  background: m.mom_pct >= 0
                    ? 'color-mix(in srgb, var(--ok) 12%, transparent)'
                    : 'color-mix(in srgb, var(--urg) 12%, transparent)',
                  padding: '1px 4px',
                  borderRadius: 3,
                  whiteSpace: 'nowrap',
                  flexShrink: 0,
                }}>
                  {m.mom_pct >= 0 ? '↑' : '↓'}{Math.abs(m.mom_pct).toFixed(1)}%
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </CollapsiblePanel>
  )
}
