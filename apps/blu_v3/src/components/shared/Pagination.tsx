import { useMemo } from 'react'

export interface PaginationProps {
  currentPage: number
  totalPages: number
  totalItems: number
  pageSize: number
  onPageChange: (page: number) => void
  label?: string
}

const HOVER_STYLE = `
  .pg-btn:not(.pg-active):not(:disabled):hover {
    background: var(--glass) !important;
    border-color: var(--gb2) !important;
  }
`

function buildPageList(current: number, total: number): (number | 'ellipsis')[] {
  if (total <= 5) {
    return Array.from({ length: total }, (_, i) => i + 1)
  }

  const around = new Set<number>()
  for (let i = current - 1; i <= current + 1; i++) {
    if (i >= 1 && i <= total) around.add(i)
  }
  around.add(1)
  around.add(total)

  const sorted = [...around].sort((a, b) => a - b)

  const result: (number | 'ellipsis')[] = []
  for (let i = 0; i < sorted.length; i++) {
    if (i > 0 && sorted[i] - sorted[i - 1] >= 2) {
      result.push('ellipsis')
    }
    result.push(sorted[i])
  }

  return result
}

function computeDefaultLabel(currentPage: number, totalItems: number, pageSize: number): string {
  if (totalItems <= 0) return 'Nenhum item'
  const start = (currentPage - 1) * pageSize + 1
  const end = Math.min(currentPage * pageSize, totalItems)
  const noun = totalItems === 1 ? 'item' : 'itens'
  return `Exibindo ${start}–${end} de ${totalItems} ${noun}`
}

const baseBtn: React.CSSProperties = {
  width: 32,
  height: 32,
  borderRadius: 'var(--r)',
  background: 'transparent',
  border: '1px solid var(--gb)',
  fontSize: 12,
  fontWeight: 500,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  transition: 'all 0.1s',
  fontFamily: 'inherit',
}

function chevronStyle(disabled: boolean): React.CSSProperties {
  return {
    ...baseBtn,
    fontSize: 14,
    color: disabled ? 'var(--gb)' : 'var(--mu2)',
    opacity: disabled ? 0.4 : 1,
    cursor: disabled ? 'not-allowed' : 'pointer',
  }
}

function pageStyle(active: boolean): React.CSSProperties {
  return {
    ...baseBtn,
    background: active ? 'var(--ac)' : 'transparent',
    border: `1px solid ${active ? 'var(--ac)' : 'var(--gb)'}`,
    color: active ? '#fff' : 'var(--mu2)',
    fontWeight: active ? 600 : 500,
  }
}

export default function Pagination({
  currentPage,
  totalPages,
  totalItems,
  pageSize,
  onPageChange,
  label,
}: PaginationProps): React.JSX.Element | null {
  const pages = useMemo(
    () => buildPageList(currentPage, totalPages),
    [currentPage, totalPages]
  )
  const infoLabel = label ?? computeDefaultLabel(currentPage, totalItems, pageSize)

  if (totalItems <= 0 || totalPages <= 0) return null

  const prevDisabled = currentPage <= 1
  const nextDisabled = currentPage >= totalPages

  return (
    <>
      <style>{HOVER_STYLE}</style>
      <div
        role="navigation"
        aria-label="Paginação"
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '8px 12px',
          borderTop: '1px solid var(--gb)',
          fontFamily: 'var(--body)',
        }}
      >
        <div style={{ fontSize: 11, color: 'var(--mu)' }}>{infoLabel}</div>
        {totalPages > 1 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <button
              type="button"
              disabled={prevDisabled}
              onClick={() => onPageChange(currentPage - 1)}
              aria-label="Página anterior"
              className="pg-btn"
              style={chevronStyle(prevDisabled)}
            >
              ‹
            </button>
            {pages.map((p, i) =>
              p === 'ellipsis' ? (
                <span
                  key={`e-${i}`}
                  aria-hidden="true"
                  style={{
                    width: 32,
                    height: 32,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--mu)',
                    fontSize: 12,
                  }}
                >
                  …
                </span>
              ) : (
                <button
                  key={p}
                  type="button"
                  onClick={() => onPageChange(p)}
                  aria-current={p === currentPage ? 'page' : undefined}
                  aria-label={`Página ${p}`}
                  className={`pg-btn${p === currentPage ? ' pg-active' : ''}`}
                  style={pageStyle(p === currentPage)}
                >
                  {p}
                </button>
              )
            )}
            <button
              type="button"
              disabled={nextDisabled}
              onClick={() => onPageChange(currentPage + 1)}
              aria-label="Próxima página"
              className="pg-btn"
              style={chevronStyle(nextDisabled)}
            >
              ›
            </button>
          </div>
        )}
      </div>
    </>
  )
}
