import { Sparkline, LineChart } from '../shared/Charts'

/* ── Types ── */

interface SmartRendererProps {
  content: string
}

/* ── Helpers ── */

/**
 * Try to extract and parse the first JSON block from a string.
 * Returns the parsed value + the trimmed original, or null.
 */
function extractJson(raw: string): { json: unknown; cleaned: string } | null {
  const trimmed = raw.trim()

  // Try direct parse first
  try {
    const json = JSON.parse(trimmed)
    return { json, cleaned: trimmed }
  } catch {
    // fall through
  }

  // Try to find a JSON object or array inside backticks or bare text
  const jsonBlock = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/)
  const candidate = jsonBlock?.[1]?.trim() ?? trimmed

  try {
    const json = JSON.parse(candidate)
    return { json, cleaned: candidate }
  } catch {
    return null
  }
}

/** Check if a value is a plain object (not null, not array) */
function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

/** Try to coerce a value into a display string */
function displayVal(v: unknown): string {
  if (v === null || v === undefined) return '—'
  if (typeof v === 'number') return v.toLocaleString()
  if (typeof v === 'boolean') return v ? 'Sim' : 'Não'
  return String(v)
}

/** Get a status color based on common status values */
function statusColor(v: unknown): string {
  const s = String(v).toLowerCase()
  if (['ativo', 'ativo', 'normal', 'ok', 'success', 'bom'].includes(s)) return 'var(--ok)'
  if (['inativo', 'inactive', 'alerta', 'warning', 'pendente'].includes(s)) return 'var(--att)'
  if (['critico', 'critical', 'error', 'urgente'].includes(s)) return 'var(--urg)'
  return 'var(--mu2)'
}

/* ── Sub-renderers ── */

/** Render a grid of KPI sections (e.g. { performance: { financeiro: {...}, comercial: {...} } }) */
function KpiGrid({ data }: { data: Record<string, unknown> }) {
  // If it has a "performance" wrapper, unwrap it
  const sections = data.performance && isPlainObject(data.performance)
    ? data.performance as Record<string, unknown>
    : data

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: '2px 0' }}>
      {Object.entries(sections).map(([sectionName, sectionVal]) => {
        if (!isPlainObject(sectionVal)) return null
        const kpis = sectionVal as Record<string, unknown>
        return (
          <div key={sectionName}>
            <div style={{
              fontSize: 10,
              fontWeight: 600,
              color: 'var(--mu)',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              marginBottom: 5,
            }}>
              {sectionName}
            </div>
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 5,
            }}>
              {Object.entries(kpis).map(([key, val]) => (
                <div key={key} style={{
                  background: 'color-mix(in srgb, var(--fg) 5.5%, transparent)',
                  borderRadius: 8,
                  padding: '7px 9px',
                  border: '1px solid var(--gl2)',
                }}>
                  <div style={{
                    fontSize: 9,
                    color: 'var(--mu)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.3px',
                    marginBottom: 2,
                  }}>
                    {key.replace(/_/g, ' ')}
                  </div>
                  <div style={{
                    fontSize: 13,
                    fontWeight: 700,
                    color: statusColor(key === 'status' ? val : null),
                    fontFamily: 'var(--mono, monospace)',
                    lineHeight: 1.3,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}>
                    {displayVal(val)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

/** Render tabular data from an array of objects */
function DataTable({ data }: { data: Record<string, unknown>[] }) {
  if (data.length === 0) return <span style={{ fontSize: 11, color: 'var(--mu)' }}>Nenhum dado</span>

  const columns = [...new Set(data.flatMap(Object.keys))]

  return (
    <div style={{
      overflowX: 'auto',
      fontSize: 11,
      borderRadius: 8,
      border: '1px solid rgba(255,255,255,0.09)',
      maxWidth: '100%',
    }}>
      <table style={{
        width: '100%',
        borderCollapse: 'collapse',
        fontFamily: 'var(--body, sans-serif)',
      }}>
        <thead>
          <tr style={{ background: 'rgba(255,255,255,0.04)' }}>
            {columns.map(col => (
              <th key={col} style={{
                padding: '5px 8px',
                textAlign: 'left',
                fontWeight: 600,
                color: 'var(--mu)',
                fontSize: 10,
                textTransform: 'uppercase',
                letterSpacing: '0.3px',
                borderBottom: '1px solid var(--gl2)',
                whiteSpace: 'nowrap',
              }}>
                {col.replace(/_/g, ' ')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i} style={{
              borderBottom: i < data.length - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none',
            }}>
              {columns.map(col => {
                const val = row[col]
                const raw = String(val ?? '')
                const isStatus = col.toLowerCase().includes('status') || col.toLowerCase().includes('situação')
                return (
                  <td key={col} style={{
                    padding: '5px 8px',
                    color: 'var(--mu2)',
                    whiteSpace: 'nowrap',
                    fontSize: 11,
                  }}>
                    {isStatus ? (
                      <span style={{
                        display: 'inline-block',
                        padding: '1px 6px',
                        borderRadius: 4,
                        fontSize: 10,
                        fontWeight: 600,
                        background: `${statusColor(val)}22`,
                        color: statusColor(val),
                      }}>
                        {raw}
                      </span>
                    ) : (
                      displayVal(val)
                    )}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Render a simple chart (sparkline or line chart) from { mrr: number[], labels: string[] } */
function ChartBlock({ data }: { data: Record<string, unknown> }) {
  // Check for mrr+labels pattern
  if (Array.isArray(data.mrr) && Array.isArray(data.labels)) {
    const values = data.mrr as number[]
    const labels = data.labels as string[]
    if (values.length > 0 && labels.length > 0) {
      const chartData = values.map((v, i) => ({
        label: labels[i] ?? '',
        value: v,
      }))
      return (
        <div style={{ maxWidth: 280, padding: '5px 0' }}>
          <LineChart
            data={chartData}
            width={260}
            height={140}
            color="var(--ac)"
            gradient
            showDots
            showLabels
            formatValue={v => v.toLocaleString()}
          />
        </div>
      )
    }
  }

  // Check for numeric-only values that can be shown as sparkline
  const numericKeys = Object.entries(data).filter(
    ([, v]) => Array.isArray(v) && v.length > 0 && typeof v[0] === 'number'
  )
  if (numericKeys.length > 0) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, padding: '5px 0' }}>
        {numericKeys.map(([key, arr]) => (
          <div key={key} style={{
            background: 'color-mix(in srgb, var(--fg) 5.5%, transparent)',
            borderRadius: 8,
            padding: '6px 10px',
            border: '1px solid var(--gl2)',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
          }}>
            <div style={{ fontSize: 10, color: 'var(--mu)', fontWeight: 600, textTransform: 'uppercase', minWidth: 40 }}>
              {key}
            </div>
            <Sparkline
              data={arr as number[]}
              width={100}
              height={20}
              color="var(--ac)"
            />
            <div style={{ fontSize: 10, color: 'var(--mu2)', fontFamily: 'var(--mono, monospace)', marginLeft: 'auto' }}>
              {(arr as number[])[(arr as number[]).length - 1]?.toLocaleString()}
            </div>
          </div>
        ))}
      </div>
    )
  }

  return null
}

/** Render simple key-value pairs as a structured card */
function KeyValueCard({ data }: { data: Record<string, unknown> }) {
  return (
    <div style={{
      background: 'color-mix(in srgb, var(--fg) 5.5%, transparent)',
      borderRadius: 8,
      border: '1px solid rgba(255,255,255,0.09)',
      padding: 10,
      display: 'flex',
      flexDirection: 'column',
      gap: 5,
    }}>
      {Object.entries(data).map(([key, val]) => (
        <div key={key} style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 10,
          fontSize: 11.5,
          lineHeight: 1.5,
        }}>
          <span style={{ color: 'var(--mu)', fontWeight: 500, flexShrink: 0 }}>
            {key.replace(/_/g, ' ')}
          </span>
          <span style={{
            color: 'var(--fg)',
            fontWeight: 600,
            textAlign: 'right',
            fontFamily: 'var(--mono, monospace)',
            fontSize: 11,
          }}>
            {displayVal(val)}
          </span>
        </div>
      ))}
    </div>
  )
}

/** Render arbitrary nested JSON recursively — handles mixed objects + arrays + scalars */
function NestedRenderer({ data }: { data: Record<string, unknown> }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: '2px 0' }}>
      {Object.entries(data).map(([key, val]) => {
        const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
        
        // Array of objects → DataTable
        if (Array.isArray(val) && val.length > 0 && typeof val[0] === 'object' && val[0] !== null) {
          return (
            <div key={key}>
              <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--ac)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 4, marginTop: 4 }}>
                {label}
              </div>
              <DataTable data={val as Record<string, unknown>[]} />
            </div>
          )
        }
        
        // Array of strings/numbers → bullet list
        if (Array.isArray(val)) {
          return (
            <div key={key}>
              <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--ac)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 4, marginTop: 4 }}>
                {label}
              </div>
              {val.map((item, i) => (
                <div key={i} style={{ display: 'flex', gap: 6, margin: '1px 0', paddingLeft: 4 }}>
                  <span style={{ color: 'var(--mu)', flexShrink: 0 }}>•</span>
                  <span style={{ fontSize: 11.5, color: 'var(--mu2)' }}>
                    {typeof item === 'object' && item !== null ? JSON.stringify(item) : String(item)}
                  </span>
                </div>
              ))}
            </div>
          )
        }
        
        // Nested object → render recursively
        if (typeof val === 'object' && val !== null) {
          const inner = val as Record<string, unknown>
          // If all values are scalar → KPI grid
          const allScalar = Object.values(inner).every(v => typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean' || v === null)
          return (
            <div key={key}>
              <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--ac)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 4, marginTop: 4 }}>
                {label}
              </div>
              {allScalar ? (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 5 }}>
                  {Object.entries(inner).map(([k, v]) => (
                    <div key={k} style={{ background: 'color-mix(in srgb, var(--fg) 5.5%, transparent)', borderRadius: 8, padding: '7px 9px', border: '1px solid var(--gl2)' }}>
                      <div style={{ fontSize: 9, color: 'var(--mu)', textTransform: 'uppercase', letterSpacing: '0.3px', marginBottom: 2 }}>
                        {k.replace(/_/g, ' ')}
                      </div>
                      <div style={{ fontSize: 12, fontWeight: 600, color: statusColor(v), fontFamily: 'var(--mono)', lineHeight: 1.3 }}>
                        {displayVal(v)}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <NestedRenderer data={inner} />
              )}
            </div>
          )
        }
        
        // Scalar value
        return (
          <div key={key} style={{ display: 'flex', justifyContent: 'space-between', gap: 8, padding: '3px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
            <span style={{ fontSize: 11, color: 'var(--mu)', textTransform: 'uppercase', letterSpacing: '0.3px' }}>{label}</span>
            <span style={{ fontSize: 11.5, fontWeight: 600, color: statusColor(typeof val === 'string' ? val : null), fontFamily: 'var(--mono)', textAlign: 'right' }}>{displayVal(val)}</span>
          </div>
        )
      })}
    </div>
  )
}

/** Lightweight markdown-like rendering for plain text content */
function FormattedText({ text }: { text: string }) {
  const lines = text.split('\n')
  return (
    <>
      {lines.map((line, i) => {
        // Headers
        if (line.startsWith('### ')) {
          return <div key={i} style={{ fontSize: 13, fontWeight: 700, color: 'var(--fg)', marginTop: 6, marginBottom: 2 }}>{line.slice(4)}</div>
        }
        if (line.startsWith('## ')) {
          return <div key={i} style={{ fontSize: 14, fontWeight: 700, color: 'var(--fg)', marginTop: 8, marginBottom: 3 }}>{line.slice(3)}</div>
        }
        if (line.startsWith('# ')) {
          return <div key={i} style={{ fontSize: 15, fontWeight: 700, color: 'var(--fg)', marginTop: 8, marginBottom: 3 }}>{line.slice(2)}</div>
        }
        // Bold
        if (line.includes('**') || line.includes('__')) {
          const parts = line.split(/(\*\*[^*]+\*\*|__[^_]+__)/g)
          return (
            <div key={i} style={{ margin: '1px 0' }}>
              {parts.map((part, j) => {
                const isBold = (part.startsWith('**') && part.endsWith('**')) || (part.startsWith('__') && part.endsWith('__'))
                return isBold
                  ? <strong key={j} style={{ color: 'var(--fg)' }}>{part.slice(2, -2)}</strong>
                  : <span key={j}>{part}</span>
              })}
            </div>
          )
        }
        // Lists
        if (line.match(/^[\s]*[-*+]\s/)) {
          return <div key={i} style={{ display: 'flex', gap: 6, margin: '1px 0', paddingLeft: 8 }}><span style={{ color: 'var(--ac)' }}>•</span><span>{line.replace(/^[\s]*[-*+]\s/, '')}</span></div>
        }
        if (line.match(/^[\s]*\d+[.)]\s/)) {
          const match = line.match(/^([\s]*\d+[.)])\s(.*)/)
          return <div key={i} style={{ display: 'flex', gap: 6, margin: '1px 0', paddingLeft: 8 }}><span style={{ color: 'var(--mu)', fontFamily: 'var(--mono, monospace)', fontSize: 10 }}>{match![1]}</span><span>{match![2]}</span></div>
        }
        // Separator
        if (line.match(/^[-*_]{3,}$/)) {
          return <hr key={i} style={{ border: 'none', borderTop: '1px solid var(--gb)', margin: '6px 0' }} />
        }
        // Empty
        if (line.trim() === '') {
          return <div key={i} style={{ height: 4 }} />
        }
        // Regular paragraph
        return <div key={i} style={{ margin: '1px 0' }}>{line}</div>
      })}
    </>
  )
}

/* ── Main SmartRenderer ── */

export default function SmartRenderer({ content }: SmartRendererProps) {
  const extracted = extractJson(content)

  if (!extracted) {
    // No JSON found — render as formatted text
    return <FormattedText text={content} />
  }

  const { json } = extracted

  // a) Performance insights object (has nested section objects with KPIs)
  if (isPlainObject(json)) {
    const obj = json as Record<string, unknown>

    // Unwrap "performance" wrapper
    const inner = obj.performance && isPlainObject(obj.performance)
      ? obj.performance as Record<string, unknown>
      : obj

    // Check if it's a performance-like structure: all values are objects with scalar children
    const allValuesAreObjects = Object.values(inner).length > 0 &&
      Object.values(inner).every(v => isPlainObject(v))
    const hasScalarChildren = allValuesAreObjects
      ? Object.values(inner).every(v =>
          Object.values(v as Record<string, unknown>).every(
            child => typeof child === 'string' || typeof child === 'number' || typeof child === 'boolean'
          )
        )
      : false

    if (allValuesAreObjects && hasScalarChildren) {
      return <KpiGrid data={obj} />
    }

    // c) Chart data: has mrr+labels or numeric arrays
    if (
      (Array.isArray(obj.mrr) && Array.isArray(obj.labels)) ||
      Object.values(obj).some(v => Array.isArray(v) && v.length > 0 && typeof v[0] === 'number')
    ) {
      const chartBlock = <ChartBlock data={obj} />
      if (chartBlock) return chartBlock
    }

    // d) Simple key-value: all values are scalar
    const allScalar = Object.values(obj).every(
      v => typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean' || v === null || v === undefined
    )
    if (allScalar && Object.keys(obj).length > 0) {
      return <KeyValueCard data={obj} />
    }

    // Nested/mixed structure → recursive renderer
    return <NestedRenderer data={obj} />
  }

  // b) Array of objects — render as table
  if (Array.isArray(json)) {
    if (json.length > 0 && isPlainObject(json[0])) {
      return <DataTable data={json as Record<string, unknown>[]} />
    }
    // Array of primitives — show as inline
    return <FormattedText text={content} />
  }

  // Final fallback
  return <FormattedText text={content} />
}
