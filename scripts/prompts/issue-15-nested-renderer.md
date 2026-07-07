# Fix: SmartRenderer — handle nested/mixed JSON structures

## Goal
Add a `NestedRenderer` to SmartRenderer that handles arbitrary nested JSON with mixed types (objects + arrays + scalars). This fixes "Padrões escondidos" and "Análise de concorrência" which have JSON like `{"contexto": {...}, "achados": {...}, "recomendacoes": [...]}`.

## What to change

File: `/home/ec2-user/repo_platform/apps/blu_v3/src/components/chat/SmartRenderer.tsx`

### Add NestedRenderer component (after KeyValueCard, before FormattedText)

Insert this new component before `FormattedText`:

```typescript
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
                    <div key={k} style={{ background: 'rgba(255,255,255,0.055)', borderRadius: 8, padding: '7px 9px', border: '1px solid rgba(255,255,255,0.07)' }}>
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
```

### Update the main renderer to use NestedRenderer

In the `SmartRenderer` component, find the fallback for nested objects (around line 420-421):

**Before:**
```typescript
// Fallback for nested objects that don't fit above
return <KeyValueCard data={obj} />
```

**After:**
```typescript
// Nested/mixed structure → recursive renderer
return <NestedRenderer data={obj} />
```

## Verification
`cd apps/blu_v3 && npx tsc --noEmit` — zero errors
