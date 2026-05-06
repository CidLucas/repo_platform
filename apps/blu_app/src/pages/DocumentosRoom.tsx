import { useState, useCallback, useEffect } from 'react'
import { useQueries, useMutation, useQueryClient } from '@tanstack/react-query'
import { FileText, Archive, Plus, Save, CheckCircle, Loader2 } from 'lucide-react'
import { DeskLayout } from '@/components/layout/DeskLayout'
import { DeskSurface } from '@/components/desk/DeskSurface'
import { Corkboard } from '@/components/corkboard/Corkboard'
import { UnderDesk } from '@/components/underdesk/UnderDesk'
import { AgentIconBox } from '@/components/primitives/AgentIconBox'
import { Button } from '@/components/primitives/Button'
import { SkeletonCard } from '@/components/primitives/SkeletonCard'
import { EmptyDrawer } from '@/components/drawers/EmptyDrawer'
import { DrawerHeader } from '@/components/drawers/DrawerHeader'

import { useAuth } from '@/hooks/useAuth'
import { fetchApprovalsByAgent } from '@/api/approvals'
import { fetchInsights } from '@/api/insights'
import {
  fetchRecentDocuments,
  fetchDocTemplates,
  saveDocument,
  createDocument,
} from '@/api/documents'
import { fetchRoutines } from '@/api/routines'
import { ActiveRoutinesSlot } from '@/components/desk/ActiveRoutinesSlot'
import { relativeTime } from '@/utils/format'
import { cn } from '@/utils/cn'
import type { CorkboardInsight } from '@/components/corkboard/Corkboard'
import type { BluDocument, DocTemplate } from '@/api/documents'

const DOCUMENTOS_ORB = {
  shape: 'square' as const,
  color: '#06b6d4',
  glowColor: 'rgba(6,182,212,0.5)',
}

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error'

export function DocumentosRoom() {
  const { clientId } = useAuth()
  const queryClient = useQueryClient()
  const [activeDocId, setActiveDocId] = useState<string | null>(null)
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle')

  const [approvalsQ, insightsQ, docsQ, templatesQ, routinesQ] = useQueries({
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
        queryKey: ['doc-templates'],
        queryFn: () => fetchDocTemplates(),
        staleTime: 300_000,
      },
      {
        queryKey: ['routines', 'documentos', clientId ?? ''],
        queryFn: () => fetchRoutines(clientId!, 'documentos'),
        enabled: !!clientId,
        staleTime: 120_000,
      },
    ],
  })

  const docsInsights: CorkboardInsight[] = (insightsQ.data ?? [])
    .filter((i) => !i.dimension || i.dimension === 'documentos')
    .map((i) => ({ id: i.id, title: i.title, body: i.body, severity: undefined }))

  const saveMutation = useMutation({
    mutationFn: ({ id, content }: { id: string; content: unknown }) =>
      saveDocument(id, clientId!, content),
    onSuccess: () => {
      setSaveStatus('saved')
      queryClient.invalidateQueries({ queryKey: ['documents', clientId] })
      setTimeout(() => setSaveStatus('idle'), 2000)
    },
    onError: () => setSaveStatus('error'),
  })

  const createMutation = useMutation({
    mutationFn: (title: string) => createDocument(clientId!, title),
    onSuccess: (doc) => {
      queryClient.invalidateQueries({ queryKey: ['documents', clientId] })
      setActiveDocId(doc.id)
    },
  })

  const activeDoc = (docsQ.data ?? []).find((d) => d.id === activeDocId) ?? null

  const handleSave = useCallback((content: unknown) => {
    if (!activeDocId) return
    setSaveStatus('saving')
    saveMutation.mutate({ id: activeDocId, content })
  }, [activeDocId, saveMutation])

  return (
      <DeskLayout
        title="Documentos"
        subtitle="Criação, edição e arquivo de documentos"
        agentSlug="documentos"
        agentIcon={<AgentIconBox icon={FileText} color={DOCUMENTOS_ORB.color} />}
        accentColor={DOCUMENTOS_ORB.color}
        // ── Left drawer — Templates ───────────────────────────
        leftTitle="Modelos"
        leftPillLabel="Modelos"
        leftPillIcon={<FileText size={16} strokeWidth={1.5} />}
        leftContent={
          <TemplatesDrawer
            templates={templatesQ.data ?? []}
            loading={templatesQ.isLoading}
            onUseTemplate={(t) => createMutation.mutate(t.name)}
          />
        }
        // ── Right drawer — Archive ─────────────────────────────
        rightTitle="Arquivo"
        rightPillLabel="Arquivo"
        rightPillIcon={<Archive size={16} strokeWidth={1.5} />}
        rightContent={
          <DocumentsArchive
            docs={docsQ.data ?? []}
            loading={docsQ.isLoading}
            activeId={activeDocId}
            onSelect={setActiveDocId}
          />
        }
        corkboard={
          <Corkboard
            insights={docsInsights}
            loading={insightsQ.isLoading}
            initialRows={1}
          />
        }
        underDesk={
          <UnderDesk
            agentSlug="documentos"
            routinePrefix="documentos"
            accentColor={DOCUMENTOS_ORB.color}
          />
        }
      >
        {/* ── Editor / Document list ────────────────────────── */}
        {activeDoc ? (
          <EditorView
            doc={activeDoc}
            saveStatus={saveStatus}
            onSave={handleSave}
            onClose={() => setActiveDocId(null)}
          />
        ) : (
          <>
            <DocumentsListView
              docs={docsQ.data ?? []}
              loading={docsQ.isLoading}
              onSelect={setActiveDocId}
              onCreate={() => createMutation.mutate('Novo Documento')}
              creating={createMutation.isPending}
            />

            <DeskSurface
              approvals={approvalsQ.data ?? []}
              loading={approvalsQ.isLoading}
              agentName="Documentos"
              agentOrbShape={DOCUMENTOS_ORB.shape}
              agentOrbColor={DOCUMENTOS_ORB.color}
              agentOrbGlow={DOCUMENTOS_ORB.glowColor}
              tasksSlot={<ActiveRoutinesSlot routines={routinesQ.data ?? []} loading={routinesQ.isLoading} accentColor={DOCUMENTOS_ORB.color} />}
            />
          </>
        )}
    </DeskLayout>
  )
}

// ── Document list (default state) ─────────────────────────────
function DocumentsListView({
  docs,
  loading,
  onSelect,
  onCreate,
  creating,
}: {
  docs: BluDocument[]
  loading: boolean
  onSelect: (id: string) => void
  onCreate: () => void
  creating: boolean
}) {
  return (
    <div className="bg-surface border border-border rounded-md shadow-md overflow-hidden mb-3">
      <div className="px-4 pt-4 pb-3 border-b border-border flex items-center justify-between">
        <h2 className="text-heading-sm text-white">Documentos Recentes</h2>
        <Button
          variant="primary"
          size="sm"
          onClick={onCreate}
          loading={creating}
          leftIcon={<Plus size={14} strokeWidth={2} />}
        >
          Novo
        </Button>
      </div>

      {loading ? (
        <div className="p-4 space-y-3">
          {[...Array(4)].map((_, i) => <SkeletonCard key={i} lines={2} />)}
        </div>
      ) : docs.length === 0 ? (
        <div className="p-6 text-center">
          <FileText size={24} strokeWidth={1.5} className="text-gray-500 mx-auto mb-2" />
          <p className="text-body-sm text-gray-400">Nenhum documento ainda.</p>
          <p className="text-caption text-gray-500 mt-1">Crie um novo ou use um modelo da biblioteca.</p>
        </div>
      ) : (
        <ul className="divide-y divide-border">
          {docs.map((doc) => (
            <li
              key={doc.id}
              onClick={() => onSelect(doc.id)}
              className="flex items-center gap-3 px-4 py-3 hover:bg-elevated transition-colors duration-normal cursor-pointer"
            >
              <FileText size={16} strokeWidth={1.5} className="text-gray-500 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-body-sm text-white truncate">{doc.title}</p>
                <p className="text-caption-sm text-gray-500">{relativeTime(doc.updated_at)}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// ── Editor view (when a doc is active) ────────────────────────
function EditorView({
  doc,
  saveStatus,
  onSave,
  onClose,
}: {
  doc: BluDocument
  saveStatus: SaveStatus
  onSave: (content: unknown) => void
  onClose: () => void
}) {
  const [text, setText] = useState<string>(
    typeof doc.editor_content === 'string' ? doc.editor_content : ''
  )

  // Debounced auto-save (30s)
  useEffect(() => {
    const timer = setTimeout(() => {
      if (text !== (typeof doc.editor_content === 'string' ? doc.editor_content : '')) {
        onSave(text)
      }
    }, 30_000)
    return () => clearTimeout(timer)
  }, [text, doc.editor_content, onSave])

  return (
    <div className="bg-surface border border-border rounded-md shadow-md overflow-hidden mb-3">
      {/* DocToolbar sticky */}
      <div className="sticky top-0 z-10 px-4 py-2 border-b border-border bg-surface flex items-center gap-2 flex-wrap">
        <button
          onClick={onClose}
          className="text-caption text-gray-400 hover:text-white transition-colors duration-normal cursor-pointer"
        >
          ← Voltar
        </button>
        <span className="text-border">|</span>
        <span className="flex-1 text-body-sm text-white font-medium truncate">{doc.title}</span>

        {/* Save status */}
        <span className="flex items-center gap-1 text-caption-sm shrink-0">
          {saveStatus === 'saving' && (
            <><Loader2 size={12} strokeWidth={2} className="animate-spin text-attention" /><span className="text-attention">Salvando…</span></>
          )}
          {saveStatus === 'saved' && (
            <><CheckCircle size={12} strokeWidth={2} className="text-ok" /><span className="text-ok">Salvo</span></>
          )}
          {saveStatus === 'error' && (
            <span className="text-urgent">Erro ao salvar</span>
          )}
        </span>

        <Button
          variant="primary"
          size="sm"
          onClick={() => onSave(text)}
          leftIcon={<Save size={13} strokeWidth={2} />}
        >
          Salvar
        </Button>
      </div>

      {/* Minimal text editor — Tiptap not bundled yet, plain textarea as placeholder */}
      <div className="p-4">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Comece a escrever…"
          className={cn(
            'w-full min-h-[320px] bg-transparent resize-none',
            'text-body text-gray-200 placeholder-gray-500',
            'focus:outline-none focus-visible:outline-none',
            'leading-relaxed'
          )}
          autoFocus
          aria-label="Editor de documento"
        />
      </div>
    </div>
  )
}

// ── Templates drawer ───────────────────────────────────────────
function TemplatesDrawer({
  templates,
  loading,
  onUseTemplate,
}: {
  templates: DocTemplate[]
  loading: boolean
  onUseTemplate: (t: DocTemplate) => void
}) {
  if (loading) {
    return (
      <div className="px-4 py-3 space-y-3">
        {[...Array(4)].map((_, i) => <SkeletonCard key={i} lines={2} />)}
      </div>
    )
  }

  if (templates.length === 0) {
    return (
      <EmptyDrawer
        message="Nenhum modelo disponível."
        icon={<FileText size={18} strokeWidth={1.5} />}
      />
    )
  }

  const systemTemplates = templates.filter((t) => t.is_system)
  const clientTemplates = templates.filter((t) => !t.is_system)

  return (
    <div className="flex flex-col h-full">
      {systemTemplates.length > 0 && (
        <>
          <DrawerHeader title="Modelos do Sistema" />
          <ul className="divide-y divide-border mb-3">
            {systemTemplates.map((t) => (
              <TemplateRow key={t.id} template={t} onUse={onUseTemplate} />
            ))}
          </ul>
        </>
      )}
      {clientTemplates.length > 0 && (
        <>
          <DrawerHeader title="Meus Modelos" />
          <ul className="divide-y divide-border">
            {clientTemplates.map((t) => (
              <TemplateRow key={t.id} template={t} onUse={onUseTemplate} />
            ))}
          </ul>
        </>
      )}
    </div>
  )
}

function TemplateRow({ template, onUse }: { template: DocTemplate; onUse: (t: DocTemplate) => void }) {
  return (
    <li
      onClick={() => onUse(template)}
      className="flex items-start gap-3 px-4 py-3 hover:bg-elevated transition-colors duration-normal cursor-pointer"
    >
      <FileText size={14} strokeWidth={1.5} className="text-gray-500 mt-0.5 shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-body-sm text-white">{template.name}</p>
        {template.description && (
          <p className="text-caption-sm text-gray-400 mt-0.5 line-clamp-2">{template.description}</p>
        )}
      </div>
    </li>
  )
}

// ── Archive drawer ─────────────────────────────────────────────
function DocumentsArchive({
  docs,
  loading,
  activeId,
  onSelect,
}: {
  docs: BluDocument[]
  loading: boolean
  activeId: string | null
  onSelect: (id: string) => void
}) {
  if (loading) {
    return (
      <div className="px-4 py-3 space-y-3">
        {[...Array(4)].map((_, i) => <SkeletonCard key={i} lines={2} />)}
      </div>
    )
  }

  if (docs.length === 0) {
    return (
      <EmptyDrawer
        message="Nenhum documento arquivado."
        icon={<Archive size={18} strokeWidth={1.5} />}
      />
    )
  }

  return (
    <ul className="divide-y divide-border">
      {docs.map((doc) => (
        <li
          key={doc.id}
          onClick={() => onSelect(doc.id)}
          className={cn(
            'flex items-center gap-3 px-4 py-3 hover:bg-elevated transition-colors duration-normal cursor-pointer',
            activeId === doc.id && 'bg-elevated border-l-2 border-blu-500'
          )}
        >
          <FileText size={14} strokeWidth={1.5} className="text-gray-500 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-body-sm text-white truncate">{doc.title}</p>
            <p className="text-caption-sm text-gray-500">{relativeTime(doc.updated_at)}</p>
          </div>
        </li>
      ))}
    </ul>
  )
}

