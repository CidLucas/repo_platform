import { useState, useRef, useMemo } from 'react'
import { useAppStore } from '../../store/appStore'
import { useAuth } from '../../hooks/useAuth'
import { useKnowledgeBase } from '../../hooks/useKnowledgeBase'
import { KB_CATEGORIES, isCsvFile, type KBDocument, type KBCategory } from '../../services/knowledgeBaseService'
import RColResizeHandle from '../../components/shared/RColResizeHandle'
import CollapsiblePanel from '../../components/shared/CollapsiblePanel'
import EmptyState from '../../components/shared/EmptyState'
import LoadingState from '../../components/shared/LoadingState'

type ViewMode = 'grid' | 'list'
type CategoryFilter = 'all' | string
type StatusFilter = 'all' | KBDocument['status']

function fileTypeIcon(fileName: string): string {
  const ext = fileName.split('.').pop()?.toLowerCase() ?? ''
  if (ext === 'pdf') return 'PDF'
  if (['doc', 'docx'].includes(ext)) return 'DOC'
  if (['xls', 'xlsx'].includes(ext)) return 'XLS'
  if (['ppt', 'pptx'].includes(ext)) return 'PPT'
  if (ext === 'csv') return 'CSV'
  if (['txt', 'md'].includes(ext)) return 'TXT'
  if (ext === 'json') return 'JSON'
  return 'FILE'
}

function fileTypeColor(fileName: string): string {
  const ext = fileName.split('.').pop()?.toLowerCase() ?? ''
  if (ext === 'pdf') return '#ef4444'
  if (['doc', 'docx'].includes(ext)) return '#3b82f6'
  if (['xls', 'xlsx'].includes(ext)) return '#22c55e'
  if (['ppt', 'pptx'].includes(ext)) return '#f97316'
  if (ext === 'csv') return '#10b981'
  if (['txt', 'md'].includes(ext)) return '#8b5cf6'
  if (ext === 'json') return '#f59e0b'
  return '#6b7280'
}

function kbStatusBadge(status: KBDocument['status']): { label: string; color: string } {
  switch (status) {
    case 'completed':        return { label: 'Processado', color: 'var(--ok)' }
    case 'processing':       return { label: 'Processando…', color: 'var(--att)' }
    case 'pending':          return { label: 'Pendente', color: 'var(--att)' }
    case 'failed':           return { label: 'Erro', color: 'var(--urg)' }
    case 'partially_failed': return { label: 'Parcial', color: 'var(--att)' }
    default:                 return { label: status, color: 'var(--mu)' }
  }
}

function relativeTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime()
  const d = Math.floor(diff / 86400000)
  if (d === 0) return 'hoje'
  if (d === 1) return 'ontem'
  return `${d}d atrás`
}

function catLabel(cat: string | null): string {
  return KB_CATEGORIES.find(c => c.value === cat)?.label ?? cat ?? '—'
}

// F-3-B3: falha desconhecida para documentos presos em processing > 2min
function isTimedOut(doc: KBDocument): boolean {
  return doc.status === 'processing' && Date.now() - new Date(doc.created_at).getTime() > 120_000
}

// ── Document card (grid view) ─────────────────────────────────────────────────

function DocCard({ doc, onRemove, onRetry, onDownload }: {
  doc: KBDocument
  onRemove: (id: string, path: string | null) => Promise<void>
  onRetry: (doc: KBDocument) => Promise<void>
  onDownload: (doc: KBDocument) => void
}) {
  const { label, color } = kbStatusBadge(doc.status)
  const tag = fileTypeIcon(doc.file_name)
  const tagColor = fileTypeColor(doc.file_name)
  const [hover, setHover] = useState(false)

  return (
    <div
      title={doc.description ?? ''}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        padding: '12px 12px 10px',
        background: hover ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,.18)',
        border: '1px solid var(--gb)',
        borderRadius: 'var(--r)',
        transition: 'background 0.15s',
        overflow: 'hidden',
      }}
    >
      {/* File type badge */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 6 }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: 40,
          height: 40,
          borderRadius: 8,
          background: `${tagColor}18`,
          border: `1px solid ${tagColor}30`,
          flexShrink: 0,
        }}>
          <span style={{ fontSize: 9, fontWeight: 800, letterSpacing: '0.04em', color: tagColor, fontFamily: 'var(--mono)' }}>
            {tag}
          </span>
        </div>
        <span style={{
          fontSize: 8.5,
          fontWeight: 700,
          padding: '2px 6px',
          borderRadius: 3,
          background: `${color}18`,
          color,
          alignSelf: 'flex-start',
          whiteSpace: 'nowrap',
        }}>
          {label}
        </span>
      </div>

      {/* Filename */}
      <div style={{
        fontSize: 11.5,
        fontWeight: 500,
        color: 'var(--fg)',
        lineHeight: 1.3,
        overflow: 'hidden',
        display: '-webkit-box',
        WebkitLineClamp: 2,
        WebkitBoxOrient: 'vertical',
        wordBreak: 'break-all',
        minHeight: 28,
      }}>
        {doc.file_name}
      </div>

      {doc.description && (
        <div style={{ fontSize: 9.5, color: 'var(--mu)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {doc.description}
        </div>
      )}

      {/* Category + date */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 5, flexWrap: 'wrap' }}>
        {doc.category && (
          <span style={{
            fontSize: 9,
            padding: '1px 5px',
            borderRadius: 3,
            background: 'var(--glass)',
            color: 'var(--mu2)',
            border: '1px solid var(--gb)',
          }}>
            {catLabel(doc.category)}
          </span>
        )}
        {doc.status === 'completed' && ('🔗 ' + doc.chunk_count + ' chunks')}
        <span style={{ fontSize: 9.5, color: 'var(--mu)', marginLeft: 'auto' }}>
          {relativeTime(doc.created_at)}
        </span>
      </div>

      {(doc.status === 'failed' || doc.status === 'partially_failed') && doc.error_message && (
        <div title={doc.error_message} style={{ fontSize: 9, color: 'var(--urg)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginTop: 2 }}>
          {doc.error_message}
        </div>
      )}

      {/* Actions shown on hover */}
      <div style={{
        display: 'flex',
        gap: 4,
        opacity: hover ? 1 : 0,
        transition: 'opacity 0.15s',
        marginTop: 2,
      }}>
        {(doc.status === 'failed' || doc.status === 'partially_failed' || isTimedOut(doc)) && (
          <button
            className="btn bs"
            style={{ fontSize: 9.5, padding: '2px 7px', flex: 1 }}
            onClick={() => onRetry(doc)}
          >
            {doc.status === 'processing' ? '↻ Reprocessar' : '↻ Reprocessar'}
          </button>
        )}
        <button
          className="btn bs"
          style={{ fontSize: 9.5, padding: '2px 7px' }}
          onClick={() => onDownload(doc)}
        >
          ⬇ Download
        </button>
        <button
          className="btn brd"
          style={{ fontSize: 9.5, padding: '2px 7px', marginLeft: 'auto' }}
          onClick={() => onRemove(doc.id, doc.storage_path)}
        >
          Remover
        </button>
      </div>
    </div>
  )
}

// ── Document row (list view) ──────────────────────────────────────────────────

function DocRow({ doc, onRemove, onRetry, onDownload }: {
  doc: KBDocument
  onRemove: (id: string, path: string | null) => Promise<void>
  onRetry: (doc: KBDocument) => Promise<void>
  onDownload: (doc: KBDocument) => void
}) {
  const { label, color } = kbStatusBadge(doc.status)
  const tag = fileTypeIcon(doc.file_name)
  const tagColor = fileTypeColor(doc.file_name)

  return (
    <div title={doc.description ?? ''} style={{
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      padding: '7px 10px',
      background: 'rgba(0,0,0,.18)',
      border: '1px solid var(--gb)',
      borderRadius: 'var(--r)',
    }}>
      <div style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: 30,
        height: 30,
        borderRadius: 6,
        background: `${tagColor}18`,
        border: `1px solid ${tagColor}30`,
        flexShrink: 0,
      }}>
        <span style={{ fontSize: 8, fontWeight: 800, color: tagColor, fontFamily: 'var(--mono)' }}>{tag}</span>
      </div>
      <span style={{ flex: 1, fontSize: 11.5, color: 'var(--fg)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {doc.file_name}
      </span>
      {doc.status === 'completed' && ('🔗 ' + doc.chunk_count)}
      {(doc.status === 'failed' || doc.status === 'partially_failed') && doc.error_message && (
        <span title={doc.error_message} style={{ fontSize: 9, color: 'var(--urg)', maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {doc.error_message}
        </span>
      )}
      {doc.category && (
        <span style={{ fontSize: 9.5, padding: '1px 6px', borderRadius: 3, background: 'var(--glass)', color: 'var(--mu2)', border: '1px solid var(--gb)', whiteSpace: 'nowrap' }}>
          {catLabel(doc.category)}
        </span>
      )}
      <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 3, background: `${color}18`, color, whiteSpace: 'nowrap' }}>
        {label}
      </span>
      <span style={{ fontSize: 10, color: 'var(--mu)', whiteSpace: 'nowrap' }}>
        {relativeTime(doc.created_at)}
      </span>
      {(doc.status === 'failed' || doc.status === 'partially_failed' || isTimedOut(doc)) && (
        <button className="btn bs" style={{ fontSize: 9.5, padding: '2px 7px' }} onClick={() => onRetry(doc)}>↻</button>
      )}
      <button className="btn bs" style={{ fontSize: 9.5, padding: '2px 7px' }} onClick={() => onDownload(doc)} title="Baixar arquivo original">⬇</button>
      <button className="btn brd" style={{ fontSize: 9.5, padding: '2px 7px' }} onClick={() => onRemove(doc.id, doc.storage_path)}>×</button>
    </div>
  )
}

// ── Preview modal (TXT / MD) ──────────────────────────────────────────────────

function PreviewModal({ title, text, onClose }: {
  title: string
  text: string
  onClose: () => void
}) {
  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.55)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
        padding: 24,
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: 'var(--bg, #0e0e10)',
          border: '1px solid var(--gb)',
          borderRadius: 'var(--r)',
          width: 'min(820px, 100%)',
          maxHeight: '85vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 14px',
          borderBottom: '1px solid var(--gb)',
          fontSize: 12,
          fontWeight: 600,
        }}>
          <span>👁 {title}</span>
          <button className="btn brd" style={{ fontSize: 10, padding: '2px 8px' }} onClick={onClose}>Fechar</button>
        </div>
        <pre style={{
          margin: 0,
          padding: '14px 16px',
          overflow: 'auto',
          fontSize: 12,
          lineHeight: 1.55,
          fontFamily: 'var(--mono)',
          color: 'var(--fg)',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}>{text}</pre>
      </div>
    </div>
  )
}

// ── Screen ────────────────────────────────────────────────────────────────────

export default function BibliotecaRoom() {
  const { go } = useAppStore()
  const { clientId } = useAuth()
  const kb = useKnowledgeBase()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>('all')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [sortBy, setSortBy] = useState<'created_at' | 'file_name' | 'status'>('created_at')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [kbCategory, setKbCategory] = useState<KBCategory>(KB_CATEGORIES[0].value)
  const [dragging, setDragging] = useState(false)
  const [previewContent, setPreviewContent] = useState<{ title: string; text: string } | null>(null)

  const filtered = useMemo(() => {
    return kb.documents.filter(doc => {
      if (search && !doc.file_name.toLowerCase().includes(search.toLowerCase())) return false
      if (categoryFilter !== 'all' && doc.category !== categoryFilter) return false
      if (statusFilter !== 'all' && doc.status !== statusFilter) return false
      return true
    })
  }, [kb.documents, search, categoryFilter, statusFilter])

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let cmp = 0
      if (sortBy === 'file_name') cmp = a.file_name.localeCompare(b.file_name)
      else if (sortBy === 'status') cmp = a.status.localeCompare(b.status)
      else if (sortBy === 'created_at') cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [filtered, sortBy, sortDir])

  // Stats
  const totalDocs = kb.documents.length
  const completedDocs = kb.documents.filter(d => d.status === 'completed').length
  const processingDocs = kb.documents.filter(d => d.status === 'processing' || d.status === 'pending').length
  const failedDocs = kb.documents.filter(d => d.status === 'failed' || d.status === 'partially_failed').length

  const catCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const doc of kb.documents) {
      const cat = doc.category ?? 'sem_categoria'
      counts[cat] = (counts[cat] ?? 0) + 1
    }
    return counts
  }, [kb.documents])

  async function handleUpload(file: File) {
    if (isCsvFile(file.name)) {
      await kb.uploadCsv(file)
    } else {
      await kb.upload(file, false, 'upload', { category: kbCategory })
    }
  }

  async function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) await handleUpload(file)
  }

  function handleDownload(doc: KBDocument) {
    if (!doc.storage_path) return
    kb.getDownloadUrl(doc).then(url => {
      window.open(url, '_blank')
    }).catch(err => {
      console.error('Download failed:', err)
    })
  }

  async function handlePreview(doc: KBDocument) {
    if (!doc.storage_path) return
    const url = await kb.getDownloadUrl(doc)
    const ext = doc.file_name.split('.').pop()?.toLowerCase() ?? ''
    if (ext === 'pdf') {
      window.open(url, '_blank')
      return
    }
    if (ext === 'txt' || ext === 'md') {
      try {
        const res = await fetch(url)
        const text = await res.text()
        setPreviewContent({ title: doc.file_name, text })
      } catch {
        setPreviewContent({ title: doc.file_name, text: 'Falha ao carregar preview.' })
      }
    }
  }

  return (
    <div>
      <div className="rh">
        <div className="rav">📚</div>
        <div>
          <div className="rn">Biblioteca de Conhecimento</div>
          <div className="rd">Documentos indexados para os agentes</div>
        </div>
        <div className="ra">
          <button className="btn bs" style={{ fontSize: 11 }} onClick={() => go('home', 'Início')}>
            ← Início
          </button>
          <input
            ref={fileInputRef}
            type="file"
            style={{ display: 'none' }}
            accept=".pdf,.doc,.docx,.txt,.csv,.xlsx,.xls,.pptx,.md,.json"
            onChange={async e => {
              const file = e.target.files?.[0]
              if (!file) return
              await handleUpload(file)
              e.target.value = ''
            }}
          />
          <select
            value={kbCategory}
            onChange={e => setKbCategory(e.target.value as KBCategory)}
            style={{ fontSize: 10.5, padding: '4px 8px', background: 'var(--glass)', border: '1px solid var(--gb)', borderRadius: 4, color: 'var(--fg)', cursor: 'pointer' }}
          >
            {KB_CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
          <button
            className="btn bp"
            style={{ fontSize: 11 }}
            disabled={kb.uploading || !clientId}
            onClick={() => fileInputRef.current?.click()}
          >
            {kb.uploading ? '↑ Enviando…' : '+ Adicionar arquivo'}
          </button>
        </div>
      </div>

      <div className="room-grid">
        {/* ── MAIN PANEL ── */}
        <div className="panel" style={{ gridColumn: 1, gridRow: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div className="ph">
            <span className="ph-ttl">Documentos</span>
            <span className="ph-cnt">{totalDocs > 0 ? `${totalDocs} arquivo${totalDocs !== 1 ? 's' : ''}` : ''}</span>
            {/* View toggle */}
            <div style={{ display: 'flex', gap: 2, marginLeft: 'auto' }}>
              <button
                className={`btn ${viewMode === 'grid' ? 'bp' : 'bs'}`}
                style={{ fontSize: 11, padding: '3px 8px' }}
                onClick={() => setViewMode('grid')}
                title="Grade"
              >⊞</button>
              <button
                className={`btn ${viewMode === 'list' ? 'bp' : 'bs'}`}
                style={{ fontSize: 11, padding: '3px 8px' }}
                onClick={() => setViewMode('list')}
                title="Lista"
              >≡</button>
            </div>
          </div>

          {/* Filter row */}
          <div style={{ padding: '8px 14px', display: 'flex', alignItems: 'center', gap: 8, borderBottom: '1px solid var(--gb)', flexShrink: 0 }}>
            <input
              type="text"
              placeholder="Buscar documento…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{
                flex: 1,
                fontSize: 11,
                padding: '4px 9px',
                background: 'rgba(0,0,0,.2)',
                border: '1px solid var(--gb)',
                borderRadius: 4,
                color: 'var(--fg)',
                outline: 'none',
              }}
            />
            <select
              value={categoryFilter}
              onChange={e => setCategoryFilter(e.target.value)}
              style={{ fontSize: 10.5, padding: '4px 7px', background: 'var(--glass)', border: '1px solid var(--gb)', borderRadius: 4, color: 'var(--fg)' }}
            >
              <option value="all">Todas as categorias</option>
              {KB_CATEGORIES.map(c => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value as StatusFilter)}
              style={{ fontSize: 10.5, padding: '4px 7px', background: 'var(--glass)', border: '1px solid var(--gb)', borderRadius: 4, color: 'var(--fg)' }}
            >
              <option value="all">Todos os status</option>
              <option value="completed">Processado</option>
              <option value="processing">Processando</option>
              <option value="pending">Pendente</option>
              <option value="failed">Erro</option>
              <option value="partially_failed">Parcial</option>
            </select>
            <select
              value={`${sortBy}_${sortDir}`}
              onChange={e => {
                const [b, d] = e.target.value.split('_') as ['created_at' | 'file_name' | 'status', 'asc' | 'desc']
                setSortBy(b)
                setSortDir(d)
              }}
              style={{ fontSize: 10.5, padding: '4px 7px', background: 'var(--glass)', border: '1px solid var(--gb)', borderRadius: 4, color: 'var(--fg)' }}
            >
              <option value="created_at_desc">Mais recentes</option>
              <option value="created_at_asc">Mais antigos</option>
              <option value="file_name_asc">Nome A-Z</option>
              <option value="file_name_desc">Nome Z-A</option>
              <option value="status_asc">Status A-Z</option>
              <option value="status_desc">Status Z-A</option>
            </select>
          </div>

          {/* Drop zone */}
          <div
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            style={{
              margin: '10px 14px 6px',
              border: `1px dashed ${dragging ? 'var(--acc, #FF5701)' : 'var(--gb)'}`,
              borderRadius: 'var(--r)',
              padding: '9px 14px',
              textAlign: 'center',
              fontSize: 11,
              color: dragging ? 'var(--acc, #FF5701)' : 'var(--mu)',
              cursor: 'pointer',
              transition: 'border-color 0.15s, color 0.15s',
              flexShrink: 0,
              background: dragging ? 'rgba(255,87,1,0.04)' : 'transparent',
            }}
          >
            {kb.uploading
              ? '↑ Enviando arquivo…'
              : 'Arraste arquivos aqui ou clique para selecionar (PDF, DOCX, CSV, XLSX, TXT…)'}
          </div>

          {kb.uploadError && (
            <div style={{ fontSize: 11, color: 'var(--urg)', margin: '0 14px 6px' }}>{kb.uploadError}</div>
          )}

          {kb.csvResult && (
            <div style={{ fontSize: 11, color: 'var(--ok)', margin: '0 14px 6px', padding: '6px 10px', background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.2)', borderRadius: 'var(--r)' }}>
              ✓ <strong>{kb.csvResult.file_name}</strong> adicionado como fonte de dados — {kb.csvResult.columns} coluna{kb.csvResult.columns !== 1 ? 's' : ''} detectada{kb.csvResult.columns !== 1 ? 's' : ''}
            </div>
          )}

          {/* Document list */}
          <div className="pb" style={{ flex: 1, overflowY: 'auto' }}>
            {kb.loading ? (
              <LoadingState message="Carregando documentos da base de conhecimento…" />
            ) : sorted.length === 0 ? (
              <EmptyState
                icon="📚"
                title={kb.documents.length === 0 ? 'Nenhum documento adicionado ainda' : 'Nenhum documento corresponde aos filtros'}
                description={kb.documents.length === 0
                  ? 'Adicione arquivos para que os agentes possam consultá-los.'
                  : 'Ajuste os filtros de categoria ou status para ver mais documentos.'}
              />
            ) : viewMode === 'grid' ? (
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(190px, 1fr))',
                gap: 8,
              }}>
                {sorted.map(doc => (
                  <DocCard key={doc.id} doc={doc} onRemove={kb.remove} onRetry={kb.retry} onDownload={handleDownload} />
                ))}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {sorted.map(doc => (
                  <DocRow key={doc.id} doc={doc} onRemove={kb.remove} onRetry={kb.retry} onDownload={handleDownload} />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ── RIGHT COLUMN ── */}
        <div className="rcol">
          <RColResizeHandle />

          <CollapsiblePanel id="kb-upload" icon="📤" title="Upload">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: '8px 14px 10px' }}>
              <div style={{ fontSize: 10.5, color: 'var(--mu)', marginBottom: 2 }}>Categoria padrão</div>
              <select
                value={kbCategory}
                onChange={e => setKbCategory(e.target.value as KBCategory)}
                style={{ fontSize: 10.5, padding: '4px 8px', background: 'var(--glass)', border: '1px solid var(--gb)', borderRadius: 4, color: 'var(--fg)', width: '100%' }}
              >
                {KB_CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
              <button
                className="btn bp"
                style={{ fontSize: 11, width: '100%' }}
                disabled={kb.uploading || !clientId}
                onClick={() => fileInputRef.current?.click()}
              >
                {kb.uploading ? '↑ Enviando…' : '+ Escolher arquivo'}
              </button>
              <div style={{ fontSize: 10, color: 'var(--mu)', textAlign: 'center', lineHeight: 1.4 }}>
                PDF · DOCX · XLSX · PPTX · CSV · TXT · MD · JSON
              </div>
            </div>
          </CollapsiblePanel>

          <CollapsiblePanel id="kb-stats" icon="📊" title="Resumo">
            <div style={{ padding: '8px 14px 10px', display: 'flex', flexDirection: 'column', gap: 6 }}>
              {[
                { label: 'Total de arquivos', value: totalDocs, color: 'var(--fg)' },
                { label: 'Processados', value: completedDocs, color: 'var(--ok)' },
                { label: 'Em processamento', value: processingDocs, color: 'var(--att)' },
                { label: 'Com erro', value: failedDocs, color: failedDocs > 0 ? 'var(--urg)' : 'var(--mu)' },
              ].map(({ label, value, color }) => (
                <div key={label} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 11.5 }}>
                  <span style={{ color: 'var(--mu)' }}>{label}</span>
                  <span style={{ fontFamily: 'var(--mono)', color }}>{value}</span>
                </div>
              ))}
            </div>
          </CollapsiblePanel>

          <CollapsiblePanel id="kb-categories" icon="🗂️" title="Por categoria">
            <div style={{ padding: '8px 14px 10px', display: 'flex', flexDirection: 'column', gap: 5 }}>
              {KB_CATEGORIES.map(cat => {
                const count = catCounts[cat.value] ?? 0
                const pct = totalDocs > 0 ? (count / totalDocs) * 100 : 0
                return (
                  <div key={cat.value}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 3 }}>
                      <span style={{ color: 'var(--mu2)' }}>{cat.label}</span>
                      <span style={{ fontFamily: 'var(--mono)', color: 'var(--fg)' }}>{count}</span>
                    </div>
                    <div style={{ height: 3, background: 'var(--gb)', borderRadius: 2, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${pct}%`, background: 'var(--acc, #FF5701)', borderRadius: 2, transition: 'width 0.4s' }} />
                    </div>
                  </div>
                )
              })}
              {catCounts['sem_categoria'] ? (
                <div style={{ fontSize: 10.5, color: 'var(--mu)', marginTop: 4 }}>
                  {catCounts['sem_categoria']} sem categoria
                </div>
              ) : null}
            </div>
          </CollapsiblePanel>
        </div>

        {/* ── BOTTOM STRIP ── */}
        <div className="bstrip">
          <div className="nums-chip">
            <div className="nums-head">📚 Base de Conhecimento</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                <span style={{ color: 'var(--mu)' }}>Chunks indexados</span>
                <span style={{ fontFamily: 'var(--mono)' }}>
                  {kb.documents.reduce((sum, d) => sum + (d.chunk_count ?? 0), 0)}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                <span style={{ color: 'var(--mu)' }}>Cobertura</span>
                <span style={{ fontFamily: 'var(--mono)', color: completedDocs > 0 ? 'var(--ok)' : 'var(--mu)' }}>
                  {totalDocs > 0 ? `${Math.round((completedDocs / totalDocs) * 100)}%` : '—'}
                </span>
              </div>
            </div>
          </div>
          {processingDocs > 0 && (
            <div className="ich">
              <span className="ich-em">⏳</span>
              <div className="ich-body">
                <span className="ich-tag tg-a">Em fila</span>
                <div className="ich-txt">{processingDocs} documento{processingDocs !== 1 ? 's' : ''} sendo processado{processingDocs !== 1 ? 's' : ''}. A indexação pode levar alguns minutos.</div>
              </div>
            </div>
          )}
          {failedDocs > 0 && (
            <div className="ich">
              <span className="ich-em">⚠️</span>
              <div className="ich-body">
                <span className="ich-tag" style={{ background: 'rgba(220,38,38,0.15)', color: 'var(--urg)' }}>Atenção</span>
                <div className="ich-txt">{failedDocs} documento{failedDocs !== 1 ? 's' : ''} com erro de processamento. Use ↻ para reprocessar.</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {previewContent && (
        <PreviewModal
          title={previewContent.title}
          text={previewContent.text}
          onClose={() => setPreviewContent(null)}
        />
      )}
    </div>
  )
}
