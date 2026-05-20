import { useState, useCallback, useEffect } from 'react'
import { useQueries, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAppStore } from '../../store/appStore'
import { useAuth } from '../../hooks/useAuth'
import {
  fetchApprovalsByAgent,
  approveRequest,
  snoozeApproval,
  type ApprovalRequest,
} from '../../api/approvals'
import { fetchInsights, type ClientInsight } from '../../api/insights'
import {
  fetchRecentDocuments,
  fetchDocTemplates,
  saveDocument,
  createDocument,
  type BluDocument,
  type DocTemplate,
} from '../../api/documents'
import { snoozeUntil } from '../../utils/time'
import RColResizeHandle from '../../components/shared/RColResizeHandle'
import CollapsiblePanel from '../../components/shared/CollapsiblePanel'
import RoutineConfigSection from '../../components/shared/RoutineConfigSection'
import RoutineStatusWidget from '../../components/shared/RoutineStatusWidget'

type Tab = 'ativos' | 'rascunhos' | 'modelos' | 'config'
type SaveStatus = 'idle' | 'saving' | 'saved' | 'error'

function relativeTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime()
  const d = Math.floor(diff / 86400000)
  if (d === 0) return 'hoje'
  if (d === 1) return 'ontem'
  return `${d}d atrás`
}

interface DocumentosRoomProps {
  openEditor: (docName: string) => void
}

export default function DocumentosRoom({ openEditor }: DocumentosRoomProps) {
  const { go, addToast, pendingDocId, setPendingDocId } = useAppStore()
  const { clientId } = useAuth()
  const qc = useQueryClient()
  const [tab, setTab] = useState<Tab>('ativos')
  const [activeDocId, setActiveDocId] = useState<string | null>(null)
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle')

  useEffect(() => {
    if (pendingDocId) {
      setActiveDocId(pendingDocId)
      setPendingDocId(null)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const [approvalsQ, insightsQ, docsQ, templatesQ] = useQueries({
    queries: [
      {
        queryKey: ['approvals', 'documentos', clientId ?? ''],
        queryFn: () => fetchApprovalsByAgent('documentos', clientId!),
        enabled: !!clientId,
        staleTime: 30_000,
      },
      {
        queryKey: ['insights'],
        queryFn: () => fetchInsights(),
        enabled: !!clientId,
        staleTime: 60_000,
      },
      {
        queryKey: ['documents', clientId ?? ''],
        queryFn: () => fetchRecentDocuments(clientId!),
        enabled: !!clientId,
        staleTime: 30_000,
      },
      {
        queryKey: ['doc-templates', clientId ?? ''],
        queryFn: () => fetchDocTemplates(clientId!),
        enabled: !!clientId,
        staleTime: 300_000,
      },
    ],
  })

  const approveMut = useMutation({
    mutationFn: (id: string) => approveRequest(id, clientId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['approvals', 'documentos', clientId] })
      addToast('ok', 'Aprovado', 'Aprovação registrada.')
    },
  })

  const snoozeMut = useMutation({
    mutationFn: (id: string) => snoozeApproval(id, clientId!, snoozeUntil()),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['approvals', 'documentos', clientId] })
      addToast('sn', 'Adiado', 'Lembrete em 2 horas.')
    },
  })

  const saveMut = useMutation({
    mutationFn: ({ id, content }: { id: string; content: string }) =>
      saveDocument(id, clientId!, content),
    onSuccess: () => {
      setSaveStatus('saved')
      qc.invalidateQueries({ queryKey: ['documents', clientId] })
      setTimeout(() => setSaveStatus('idle'), 2000)
    },
    onError: () => setSaveStatus('error'),
  })

  const createMut = useMutation({
    mutationFn: (title: string) => createDocument(clientId!, title),
    onSuccess: (doc) => {
      qc.invalidateQueries({ queryKey: ['documents', clientId] })
      setActiveDocId(doc.id)
    },
  })

  const approvals: ApprovalRequest[] = approvalsQ.data ?? []
  const docs: BluDocument[] = docsQ.data ?? []
  const templates: DocTemplate[] = templatesQ.data ?? []
  const insights: ClientInsight[] = (insightsQ.data ?? []).filter(
    (i) => !i.dimension || i.dimension === 'documentos'
  )

  const activeDoc = docs.find((d) => d.id === activeDocId) ?? null

  const handleSave = useCallback(
    (content: string) => {
      if (!activeDocId) return
      setSaveStatus('saving')
      saveMut.mutate({ id: activeDocId, content })
    },
    [activeDocId, saveMut]
  )

  return (
    <div>
      <div className="rh">
        <div className="rav">✍️</div>
        <div>
          <div className="rn">Documentos</div>
          <div className="rd">Rascunhos, modelos e aprovações</div>
        </div>
        <div className="ra">
          <button className="btn bs" style={{ fontSize: 11 }} onClick={() => go('home', 'Início')}>
            ← Início
          </button>
          <button
            className="btn bp"
            style={{ fontSize: 11 }}
            onClick={() => createMut.mutate('Novo Documento')}
            disabled={createMut.isPending || !clientId}
          >
            {createMut.isPending ? '…' : '+ Novo documento'}
          </button>
        </div>
      </div>

      <div className="room-grid">
        <div className="panel" style={{ gridColumn: 1, gridRow: 1 }}>
          <div className="ph">
            <span className="ph-ttl">Mesa de Trabalho</span>
            <span className="ph-cnt">
              {approvalsQ.isLoading ? '…' : approvals.length > 0 ? `${approvals.length} para assinar` : ''}
            </span>
          </div>
          <div className="rtabs" id="dTabs">
            {(['ativos', 'rascunhos', 'modelos', 'config'] as Tab[]).map((t) => (
              <div
                key={t}
                className={`rtab${tab === t ? ' on' : ''}`}
                onClick={() => { setActiveDocId(null); setTab(t) }}
              >
                {t === 'ativos' ? 'Ativos' : t === 'rascunhos' ? 'Rascunhos' : t === 'modelos' ? 'Modelos' : 'Config'}
              </div>
            ))}
          </div>

          <div className="pb">
            {/* ATIVOS — approvals + recent docs */}
            <div className={`tc${tab === 'ativos' ? ' on' : ''}`} id="d-ativos">
              {approvalsQ.isLoading ? (
                <div className="dc" style={{ opacity: 0.4 }}>Carregando…</div>
              ) : activeDoc && tab === 'ativos' ? (
                <DocEditor
                  doc={activeDoc}
                  saveStatus={saveStatus}
                  onSave={handleSave}
                  onClose={() => setActiveDocId(null)}
                />
              ) : (
                <>
                  {approvals.map((ap) => (
                    <ApprovalCard
                      key={ap.id}
                      ap={ap}
                      onApprove={() => { approveMut.mutate(ap.id); openEditor(ap.title) }}
                      onSnooze={() => snoozeMut.mutate(ap.id)}
                    />
                  ))}
                  <div style={{ marginTop: 9, display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {docsQ.isLoading ? (
                      <div style={{ fontSize: 11, color: 'var(--mu)', padding: '4px 0' }}>Carregando documentos…</div>
                    ) : docs.length === 0 ? (
                      <div style={{ fontSize: 11, color: 'var(--mu)', padding: '8px 0', textAlign: 'center' }}>
                        Nenhum documento ainda. Crie um ou use um modelo.
                      </div>
                    ) : (
                      docs.map((doc) => (
                        <div
                          key={doc.id}
                          className="doc-row"
                          style={{ cursor: 'pointer' }}
                          onClick={() => setActiveDocId(doc.id)}
                        >
                          <span className="doc-icon">📋</span>
                          <div className="doc-name">{doc.title}</div>
                          <span className="doc-date">{relativeTime(doc.updated_at)}</span>
                          <span
                            className="doc-status"
                            style={{ background: 'var(--adim2)', color: 'var(--att)' }}
                          >
                            {doc.editor_content ? 'Editado' : 'Rascunho'}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </>
              )}
            </div>

            {/* RASCUNHOS — docs without content */}
            <div className={`tc${tab === 'rascunhos' ? ' on' : ''}`} id="d-rascunhos">
              {docsQ.isLoading ? (
                <div style={{ fontSize: 11, color: 'var(--mu)' }}>Carregando…</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {docs.filter((d) => !d.editor_content).length === 0 ? (
                    <div style={{ fontSize: 11, color: 'var(--mu)', padding: '8px 0', textAlign: 'center' }}>
                      Nenhum rascunho pendente.
                    </div>
                  ) : (
                    docs
                      .filter((d) => !d.editor_content)
                      .map((doc) => (
                        <div
                          key={doc.id}
                          className="doc-row"
                          style={{ cursor: 'pointer' }}
                          onClick={() => { setActiveDocId(doc.id); setTab('ativos') }}
                        >
                          <span className="doc-icon">✏️</span>
                          <div className="doc-name">{doc.title}</div>
                          <span className="doc-date">{relativeTime(doc.updated_at)}</span>
                        </div>
                      ))
                  )}
                </div>
              )}
            </div>

            {/* MODELOS */}
            <div className={`tc${tab === 'modelos' ? ' on' : ''}`} id="d-modelos">
              {templatesQ.isLoading ? (
                <div style={{ fontSize: 11, color: 'var(--mu)' }}>Carregando modelos…</div>
              ) : templates.length === 0 ? (
                <div style={{ fontSize: 11, color: 'var(--mu)', padding: '8px 0', textAlign: 'center' }}>
                  Nenhum modelo disponível.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {templates.map((t) => (
                    <div key={t.id} className="doc-row">
                      <span className="doc-icon">🗂️</span>
                      <div className="doc-name">{t.name}</div>
                      {t.description && (
                        <span className="doc-date" style={{ fontSize: 10.5 }}>{t.description}</span>
                      )}
                      <button
                        className="btn bs"
                        style={{ fontSize: 10, padding: '3px 7px' }}
                        onClick={() => createMut.mutate(t.name)}
                        disabled={createMut.isPending}
                      >
                        Usar
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* CONFIG */}
            <div className={`tc${tab === 'config' ? ' on' : ''}`} id="d-config">
              <RoutineConfigSection domain="documentos" />
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN */}
        <div className="rcol">
          <RColResizeHandle />
          <CollapsiblePanel id="docs-rotinas" icon="⚙️" title="Rotinas ativas">
            <RoutineStatusWidget domain="documentos" />
          </CollapsiblePanel>
          <CollapsiblePanel id="docs-modelos" icon="🗂️" title="Modelos" action={<button className="ph-add">＋</button>}>
            <div className="dr-sec">
                {templatesQ.isLoading ? (
                  <div style={{ fontSize: 11, color: 'var(--mu)' }}>Carregando…</div>
                ) : (
                  templates.slice(0, 5).map((t) => (
                    <div key={t.id} className="hi">
                      <div className="hi-n">{t.name}</div>
                      <div className="hi-m">
                        {t.is_system && <span style={{ color: 'var(--ok)' }}>★ Sistema</span>}
                      </div>
                    </div>
                  ))
                )}
              </div>
              <div className="dr-sec">
                <div className="dr-ttl">Este mês</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 5, fontSize: 11.5 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--mu)' }}>Documentos criados</span>
                    <span style={{ fontFamily: 'var(--mono)' }}>{docs.length}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--mu)' }}>Com conteúdo</span>
                    <span style={{ fontFamily: 'var(--mono)', color: 'var(--ok)' }}>
                      {docs.filter((d) => !!d.editor_content).length}
                    </span>
                  </div>
                </div>
              </div>
          </CollapsiblePanel>
          <CollapsiblePanel id="docs-recentes" icon="📂" title="Recentes">
            <div className="dr-sec">
                {docsQ.isLoading ? (
                  <div style={{ fontSize: 11, color: 'var(--mu)' }}>Carregando…</div>
                ) : (
                  docs.slice(0, 4).map((doc) => (
                    <div
                      key={doc.id}
                      className="hi"
                      style={{ cursor: 'pointer' }}
                      onClick={() => { setActiveDocId(doc.id); setTab('ativos') }}
                    >
                      <div className="hi-n">{doc.title}</div>
                      <div className="hi-m">
                        <span>{relativeTime(doc.updated_at)}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
          </CollapsiblePanel>
        </div>

        {/* BOTTOM STRIP */}
        <div className="bstrip">
          {insights.slice(0, 3).map((ins) => (
            <div key={ins.id} className="ich">
              <span className="ich-em">💡</span>
              <div className="ich-body">
                <span className="ich-tag tg-a">Insight</span>
                <div className="ich-txt">{ins.title}</div>
              </div>
            </div>
          ))}
          <div className="nums-chip" onClick={() => setTab('config')} style={{ cursor: 'pointer' }}>
            <div className="nums-head">⚙️ Rotinas ativas</div>
            <div style={{ fontSize: 11, color: 'var(--mu)' }}>Ver na aba Config →</div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Approval card ──────────────────────────────────────────────
function ApprovalCard({
  ap,
  onApprove,
  onSnooze,
}: {
  ap: ApprovalRequest
  onApprove: () => void
  onSnooze: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const priorityColor = ap.priority === 'urgent' ? '#f87171' : ap.priority === 'high' ? '#fb923c' : '#f472b6'

  return (
    <div className={`dc warn${expanded ? ' expanded' : ''}`}>
      <div className="dc-row" onClick={() => setExpanded(!expanded)}>
        <div className="ag">
          <div className="agd" style={{ background: priorityColor }} />
          Documentos
        </div>
        <span className="bdg bw">
          {new Date(ap.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
        </span>
        <span className="dc-row-summary">{ap.title}</span>
        <span className="dc-chev">{expanded ? '▼' : '▶'}</span>
      </div>
      {expanded && (
        <div className="dc-expand">
          {ap.body && <div className="db">{ap.body}</div>}
          <div className="dc-act">
            <button className="btn bp" onClick={onApprove}>✍️ Assinar</button>
            <button className="btn bg" onClick={onSnooze}>⏰ Depois</button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Inline doc editor ─────────────────────────────────────────
function DocEditor({
  doc,
  saveStatus,
  onSave,
  onClose,
}: {
  doc: BluDocument
  saveStatus: SaveStatus
  onSave: (content: string) => void
  onClose: () => void
}) {
  const [text, setText] = useState(
    typeof doc.editor_content === 'string' ? doc.editor_content : ''
  )

  // Auto-save debounce 30s
  useEffect(() => {
    const t = setTimeout(() => {
      if (text !== (typeof doc.editor_content === 'string' ? doc.editor_content : '')) {
        onSave(text)
      }
    }, 30_000)
    return () => clearTimeout(t)
  }, [text, doc.editor_content, onSave])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11.5 }}>
        <button className="btn bs" style={{ fontSize: 10 }} onClick={onClose}>← Voltar</button>
        <span style={{ flex: 1, fontWeight: 500, color: 'var(--mu2)' }}>{doc.title}</span>
        <span style={{ fontSize: 10, color: saveStatus === 'saved' ? 'var(--ok)' : saveStatus === 'error' ? 'var(--urg)' : 'var(--mu)' }}>
          {saveStatus === 'saving' ? 'Salvando…' : saveStatus === 'saved' ? '✓ Salvo' : saveStatus === 'error' ? 'Erro' : ''}
        </span>
        <button className="btn bp" style={{ fontSize: 10 }} onClick={() => onSave(text)}>Salvar</button>
      </div>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Comece a escrever…"
        style={{
          width: '100%',
          minHeight: 280,
          background: 'transparent',
          border: '1px solid var(--gb)',
          borderRadius: 6,
          padding: '10px 12px',
          fontSize: 12.5,
          color: 'var(--fg)',
          resize: 'vertical',
          lineHeight: 1.6,
        }}
        autoFocus
      />
    </div>
  )
}
