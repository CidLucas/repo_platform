import { useState, useMemo } from 'react'
import {
  Database,
  Faders,
  CaretDown,
  CaretUp,
  CalendarCheck,
  Clock,
  Tag,
  Hash,
  ShieldCheck,
  WarningCircle,
} from '@phosphor-icons/react'
import { useBusinessMemory } from '../../hooks/useBusinessMemory'
import type { BusinessMemoryRecord } from '../../api/businessMemory'

// ── Layout helpers ──────────────────────────────────────────────────────────

const ENTITY_TYPE_OPTIONS = [
  { value: '', label: 'Todos os tipos' },
  { value: 'snapshot', label: 'Snapshot' },
  { value: 'routine', label: 'Rotina' },
  { value: 'skill', label: 'Skill' },
  { value: 'agent_result', label: 'Resultado de Agente' },
]

const ENTITY_TYPE_COLORS: Record<string, string> = {
  snapshot: 'var(--ac)',
  routine: 'var(--ok)',
  skill: 'var(--blue2)',
  client: 'var(--att)',
  contact: '#EC4899',
  supplier: '#6366F1',
  user: '#14B8A6',
  agent_result: 'var(--orange)',
  agent_metadata: '#A855F7',
}

function entityColor(type: string): string {
  return ENTITY_TYPE_COLORS[type] ?? '#64748B'
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    })
  } catch {
    return iso
  }
}

function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

function confidenceLabel(c: number | null): { label: string; color: string } {
  if (c === null || c === undefined) return { label: '—', color: 'var(--mu)' }
  if (c >= 0.9) return { label: `${Math.round(c * 100)}%`, color: 'var(--ok)' }
  if (c >= 0.7) return { label: `${Math.round(c * 100)}%`, color: 'var(--att)' }
  return { label: `${Math.round(c * 100)}%`, color: 'var(--urg)' }
}

function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max) + '…' : s
}

// ── Record detail row (expanded) ────────────────────────────────────────────

function RecordDetail({ record }: { record: BusinessMemoryRecord }) {
  const ci = confidenceLabel(record.confidence)

  return (
    <div className="bm-detail">
      <div className="bm-detail-grid">
        {/* Metadata fields */}
        <div className="bm-prop">
          <span className="bm-prop-label">
            <Tag size={12} weight="fill" /> Entity Type
          </span>
          <span
            className="bm-badge"
            style={{ background: entityColor(record.entity_type) + '22', color: entityColor(record.entity_type) }}
          >
            {record.entity_type}
          </span>
        </div>
        <div className="bm-prop">
          <span className="bm-prop-label">
            <Hash size={12} /> Entity Name
          </span>
          <span className="bm-prop-value">{record.entity_name}</span>
        </div>
        <div className="bm-prop">
          <span className="bm-prop-label">
            <Tag size={12} /> Key
          </span>
          <span className="bm-prop-value mono">{record.key}</span>
        </div>
        <div className="bm-prop">
          <span className="bm-prop-label">
            <ShieldCheck size={12} /> Confidence
          </span>
          <span className="bm-prop-value" style={{ color: ci.color }}>
            {ci.label}
          </span>
        </div>
        <div className="bm-prop">
          <span className="bm-prop-label">
            <Tag size={12} /> Source
          </span>
          <span className="bm-prop-value">{record.source ?? '—'}</span>
        </div>
        <div className="bm-prop">
          <span className="bm-prop-label">
            <Hash size={12} /> Version
          </span>
          <span className="bm-prop-value mono">{record.version ?? '—'}</span>
        </div>
        <div className="bm-prop">
          <span className="bm-prop-label">
            <CalendarCheck size={12} /> Created
          </span>
          <span className="bm-prop-value">{formatDateTime(record.created_at)}</span>
        </div>
        <div className="bm-prop">
          <span className="bm-prop-label">
            <Clock size={12} /> Updated
          </span>
          <span className="bm-prop-value">{formatDateTime(record.updated_at)}</span>
        </div>
      </div>

      {/* Metadata JSON display */}
      {record.metadata && Object.keys(record.metadata).length > 0 && (
        <div className="bm-section">
          <div className="bm-section-title">Metadata</div>
          <pre className="bm-json">{JSON.stringify(record.metadata, null, 2)}</pre>
        </div>
      )}

      {/* Value display */}
      {record.value && (
        <div className="bm-section">
          <div className="bm-section-title">Value</div>
          {typeof record.value === 'object' && record.value.resumo_executivo ? (
            <>
              <div className="bm-markdown">
                {(record.value.resumo_executivo as string)}
              </div>
              <details style={{ marginTop: 8 }}>
                <summary style={{ cursor: 'pointer', color: 'var(--mu)', fontSize: 11 }}>
                  Ver JSON completo
                </summary>
                <pre className="bm-json" style={{ marginTop: 6 }}>
                  {JSON.stringify(record.value, null, 2)}
                </pre>
              </details>
            </>
          ) : (
            <pre className="bm-json">{JSON.stringify(record.value, null, 2)}</pre>
          )}
        </div>
      )}
    </div>
  )
}

// ── Dimension filter chip ───────────────────────────────────────────────────

function DimensionChips({
  selected,
  onChange,
  counts,
}: {
  selected: string
  onChange: (v: string) => void
  counts: Record<string, number>
}) {
  return (
    <div className="bm-chips">
      {ENTITY_TYPE_OPTIONS.map((opt) => (
        <button
          key={opt.value}
          className={`bm-chip${selected === opt.value ? ' on' : ''}`}
          onClick={() => onChange(opt.value)}
        >
          {opt.label}
          {opt.value && counts[opt.value] ? (
            <span className="bm-chip-cnt">{counts[opt.value]}</span>
          ) : null}
        </button>
      ))}
    </div>
  )
}

// ── Main page ───────────────────────────────────────────────────────────────

export default function BusinessMemoryPage() {
  const [filterType, setFilterType] = useState('')
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const {
    data,
    isLoading,
    error,
    refetch,
  } = useBusinessMemory({
    entityType: filterType || undefined,
    limit: 100,
  })

  const records = data?.records ?? []
  const total = data?.total_records ?? 0

  // Count records per entity_type for filter chips
  const typeCounts = useMemo(() => {
    // Use the full (unfiltered) list via a separate instance or approximate
    // For accurate counts independent of filter, we'd need a separate query.
    // Here we show counts from the currently loaded data as a hint.
    const all = data?.records ?? []
    const counts: Record<string, number> = {}
    for (const r of all) {
      counts[r.entity_type] = (counts[r.entity_type] ?? 0) + 1
    }
    return counts
  }, [data])

  function toggleExpand(id: string) {
    setExpandedId((prev) => (prev === id ? null : id))
  }

  // ── Render states ──

  if (error) {
    return (
      <div className="bm-state">
        <WarningCircle size={40} weight="duotone" style={{ color: 'var(--urg)' }} />
        <div className="bm-state-title">Erro ao carregar</div>
        <div className="bm-state-desc">
          {(error as Error).message || 'Não foi possível carregar os dados da memória de negócio.'}
        </div>
        <button className="btn bp" onClick={() => refetch()} style={{ marginTop: 14 }}>
          Tentar novamente
        </button>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="bm-state">
        <div className="bm-spinner" />
        <div className="bm-state-title">Carregando memória de negócio…</div>
      </div>
    )
  }

  if (records.length === 0) {
    return (
      <div className="bm-state">
        <Database size={40} weight="duotone" style={{ color: 'var(--mu)' }} />
        <div className="bm-state-title">Nenhum registro encontrado</div>
        <div className="bm-state-desc">
          {filterType
            ? `Nenhum registro do tipo "${filterType}" disponível no momento.`
            : 'A memória de negócio está vazia. Registros serão populados automaticamente pelos agentes.'}
        </div>
        {filterType && (
          <button className="btn bp" onClick={() => setFilterType('')} style={{ marginTop: 14 }}>
            Limpar filtros
          </button>
        )}
      </div>
    )
  }

  // ── Main render ──

  return (
    <div className="bm-page">
      {/* Header */}
      <div className="bm-header">
        <div className="bm-header-left">
          <Database size={22} weight="duotone" style={{ color: 'var(--ac)', flexShrink: 0 }} />
          <div>
            <div className="bm-title">Memória de Negócio</div>
            <div className="bm-subtitle">
              {total} registro{total !== 1 ? 's' : ''}
              {filterType && ` · filtrando por "${filterType}"`}
            </div>
          </div>
        </div>
        <div className="bm-header-right">
          <Faders size={16} weight="duotone" style={{ color: 'var(--mu)' }} />
          <span style={{ fontSize: 11, color: 'var(--mu)' }}>
            {filterType || 'Todos os tipos'}
          </span>
        </div>
      </div>

      {/* Filter chips */}
      <DimensionChips selected={filterType} onChange={setFilterType} counts={typeCounts} />

      {/* Records list */}
      <div className="bm-list">
        {records.map((record) => {
          const isOpen = expandedId === record.id
          const ci = confidenceLabel(record.confidence)

          return (
            <div key={record.id} className={`bm-card${isOpen ? ' open' : ''}`}>
              <div className="bm-card-header" onClick={() => toggleExpand(record.id)}>
                <div className="bm-card-left">
                  {/* Entity type badge */}
                  <span
                    className="bm-badge bm-badge-sm"
                    style={{
                      background: entityColor(record.entity_type) + '22',
                      color: entityColor(record.entity_type),
                    }}
                  >
                    {record.entity_type}
                  </span>

                  {/* Main info */}
                  <div className="bm-card-info">
                    <div className="bm-card-name">
                      {record.value &&
                      typeof record.value === 'object' &&
                      (record.value as Record<string, unknown>).resumo_executivo
                        ? truncate(
                            (record.value as Record<string, unknown>).resumo_executivo as string,
                            120
                          )
                        : record.entity_name}
                    </div>
                    <div className="bm-card-meta">
                      <span className="mono" style={{ fontSize: 10 }}>
                        {record.entity_name}
                      </span>
                      <span style={{ color: 'var(--mu)', fontSize: 10 }}>·</span>
                      <span style={{ fontSize: 10, color: 'var(--mu)' }}>
                        {formatDate(record.created_at)}
                      </span>
                      <span style={{ color: 'var(--mu)', fontSize: 10 }}>·</span>
                      <span style={{ fontSize: 10, color: ci.color, fontWeight: 600 }}>
                        {ci.label}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="bm-card-right">
                  {/* Alert count */}
                  {record.value &&
                    typeof record.value === 'object' &&
                    Array.isArray((record.value as Record<string, unknown>).alertas) &&
                    ((record.value as Record<string, unknown>).alertas as unknown[]).length > 0 && (
                      <span className="bm-alert-badge">
                        <WarningCircle size={12} weight="fill" />
                        {((record.value as Record<string, unknown>).alertas as unknown[]).length}
                      </span>
                    )}
                  <span className="bm-chev">
                    {isOpen ? (
                      <CaretUp size={14} weight="bold" />
                    ) : (
                      <CaretDown size={14} weight="bold" />
                    )}
                  </span>
                </div>
              </div>

              {/* Expanded detail */}
              {isOpen && <RecordDetail record={record} />}
            </div>
          )
        })}
      </div>
    </div>
  )
}
