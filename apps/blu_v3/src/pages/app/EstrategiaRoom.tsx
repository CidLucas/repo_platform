import { useState, useEffect, useRef } from 'react'
import { useQueries, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAppStore } from '../../store/appStore'
import { useAuth } from '../../hooks/useAuth'
import {
  fetchApprovalsByAgent,
  approveRequest,
  rejectRequest,
  snoozeApproval,
  type ApprovalRequest,
} from '../../api/approvals'
import { fetchInsights, type ClientInsight } from '../../api/insights'
import {
  fetchEstrategiaHistory,
  type EstrategiaHistoryItem,
} from '../../api/estrategia'
import { getContextMetrics, type ContextMetricRow } from '../../api/analytics'
import { fetchContextReports, downloadContextReport, type ContextReport } from '../../api/contextReport'
import {
  fetchDocTemplates,
  fetchRecentDocuments,
  type BluDocument,
  createDocument,
  saveDocument,
  type DocTemplate,
} from '../../api/documents'
import RColResizeHandle from '../../components/shared/RColResizeHandle'
import CollapsiblePanel from '../../components/shared/CollapsiblePanel'
import { Sparkline } from '../../components/shared/Charts'
import RoutineConfigSection from '../../components/shared/RoutineConfigSection'

import { snoozeUntil } from '../../utils/time'

type Tab = 'objetivos' | 'documentos' | 'conhecimento' | 'config'

function formatCompactBRL(v: number) {
  if (v >= 1_000_000) return `R$ ${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `R$ ${(v / 1_000).toFixed(1)}k`
  return `R$ ${v.toFixed(0)}`
}

// ── Document type metadata (color + label) ─────────────────────────────────
const DOC_TYPE_META: Record<string, { type: string; typeColor: string; folder: string }> = {
  md:   { type: 'MD',  typeColor: 'var(--violet)', folder: 'estrategia' },
  doc:  { type: 'DOC', typeColor: 'var(--blue2)', folder: 'juridico' },
  pdf:  { type: 'PDF', typeColor: 'var(--urg)', folder: 'pesquisa' },
  xlsx: { type: 'XLS', typeColor: 'var(--ok)', folder: 'relatorios' },
  csv:  { type: 'CSV', typeColor: 'var(--ok)', folder: 'relatorios' },
}

// ── Design-system document templates (inline markdown) ───────────────────
const DOC_TEMPLATES: Record<string, string> = {
  'fechamento-mensal': `# Relatório de Fechamento Mensal\n\n## Resumo Executivo\n\n[Resumo do mês...]\n\n## Receitas\n\n| Linha | Valor | % |\n|---|---|---|\n| SaaS Corporativo | R$ 0 | 0% |\n\n## Despesas\n\n| Categoria | Valor | % |\n|---|---|---|\n| Infraestrutura | R$ 0 | 0% |\n\n## KPIs\n\n- Margem Bruta: 0%\n- Margem EBITDA: 0%\n- Margem Líquida: 0%\n- MRR: R$ 0`,
  'fluxo-caixa': `# Fluxo de Caixa\n\n## Atividades Operacionais\n\n- Lucro Líquido: R$ 0\n- Depreciação: R$ 0\n\n## Atividades de Investimento\n\n- CAPEX: R$ 0\n\n## Atividades de Financiamento\n\n- Empréstimos: R$ 0\n\n## Saldo Final: R$ 0`,
  'proposta-comercial': `# Proposta Comercial\n\n## Escopo\n\n- Item 1\n- Item 2\n\n## Investimento\n\n| Item | Valor |\n|---|---|\n| Licença | R$ 0 |\n| Implantação | R$ 0 |\n\n## Condições\n\n- Pagamento: ...\n- Prazo: ...`,
  'plano-estrategico': `# Plano Estratégico\n\n## Visão\n\n[Declaração de visão]\n\n## Missão\n\n[Declaração de missão]\n\n## Objetivos\n\n1. **Objetivo 1**\n2. **Objetivo 2**\n3. **Objetivo 3**\n\n## KPIs\n\n| Métrica | Meta | Atual |\n|---|---|---|\n| MRR | R$ 0 | R$ 0 |\n| NPS | 0 | 0 |`,
  'okr': `# OKR\n\n## Objective\n\n[Descrição do objetivo]\n\n## Key Results\n\n- KR1: [descrição] — 0%\n- KR2: [descrição] — 0%\n- KR3: [descrição] — 0%\n\n## Owner: [Nome]`,
  'ata-reuniao': `# Ata de Reunião\n\n**Data:** __/__/____\n**Participantes:**\n\n## Pauta\n\n1. \n2. \n\n## Discussões\n\n### 1. \n\n### 2. \n\n## Ações\n\n| # | Ação | Responsável | Prazo |\n|---|---|---|---|\n| 1 | | | |`,
  'swot': `# Análise SWOT\n\n## Forças (Strengths)\n\n-\n\n## Fraquezas (Weaknesses)\n\n-\n\n## Oportunidades (Opportunities)\n\n-\n\n## Ameaças (Threats)\n\n-`,
  'invoice': `# Fatura\n\n**Emitente:** Blu Tecnologia S.A.\n**Cliente:** [Nome do Cliente]\n\n## Itens\n\n| Item | Qtd | Valor Unit. | Total |\n|---|---|---|---|\n| | | R$ 0 | R$ 0 |\n\n**Total: R$ 0,00**`,
}

// ── Template metadata for the picker ──────────────────────────────────────
const TEMPLATE_META: { id: string; icon: string; name: string; desc: string }[] = [
  { id: 'fechamento-mensal', icon: '📊', name: 'Fechamento Mensal', desc: 'Relatório mensal com receitas, despesas e KPIs' },
  { id: 'fluxo-caixa',      icon: '💰', name: 'Fluxo de Caixa',   desc: 'Demonstrativo de fluxo de caixa (DCF)' },
  { id: 'proposta-comercial', icon: '📋', name: 'Proposta Comercial', desc: 'Escopo, investimento e condições' },
  { id: 'plano-estrategico', icon: '🎯', name: 'Plano Estratégico', desc: 'Visão, missão, objetivos e KPIs' },
  { id: 'okr',              icon: '✅', name: 'OKR',              desc: 'Objectives & Key Results' },
  { id: 'ata-reuniao',      icon: '📝', name: 'Ata de Reunião',   desc: 'Pauta, discussões e ações' },
  { id: 'swot',             icon: '🔍', name: 'SWOT',             desc: 'Forças, fraquezas, oportunidades e ameaças' },
  { id: 'invoice',          icon: '🧾', name: 'Invoice',          desc: 'Fatura comercial com itens e totais' },
]

interface StrategyDoc {
  id: string
  name: string
  type: string
  typeColor: string
  date: string
  content: string
  folder: string
}

// ── Folder tree definition for the Conhecimento tab ─────────────────────────
interface FolderNode {
  id: string
  label: string
  icon: string
  depth: number
  hasChildren: boolean
  parentId: string | null
}

const FOLDER_TREE: FolderNode[] = [
  { id: 'all',          label: 'Todos os documentos', icon: '📁', depth: 0, hasChildren: false, parentId: null },
  { id: 'estrategia',   label: 'Estratégia',         icon: '🎯', depth: 0, hasChildren: true,  parentId: null },
  { id: 'okrs',         label: 'OKRs',               icon: '📋', depth: 1, hasChildren: false, parentId: 'estrategia' },
  { id: 'planejamento', label: 'Planejamento',       icon: '📈', depth: 1, hasChildren: false, parentId: 'estrategia' },
  { id: 'relatorios',   label: 'Relatórios',         icon: '📊', depth: 0, hasChildren: false, parentId: null },
  { id: 'juridico',     label: 'Jurídico',           icon: '⚖', depth: 0, hasChildren: false, parentId: null },
  { id: 'pesquisa',     label: 'Pesquisa',           icon: '🔍', depth: 0, hasChildren: false, parentId: null },
]

const FOLDER_LABELS: Record<string, string> = {
  all: 'Todos os documentos',
  estrategia: 'Estratégia',
  okrs: 'OKRs',
  planejamento: 'Planejamento',
  relatorios: 'Relatórios',
  juridico: 'Jurídico',
  pesquisa: 'Pesquisa',
}

// ── Diff computation (line-level) ──────────────────────────────────────────
interface DiffResult { html: string; count: number }

function computeDiff(original: string, current: string): DiffResult {
  if (current === original) {
    return { html: '<div style="font-size:12px;color:var(--mu);text-align:center;padding:20px 0">Sem alterações</div>', count: 0 }
  }
  const orig = original.split('\n')
  const curr = current.split('\n')
  const max = Math.max(orig.length, curr.length)
  let html = ''
  let count = 0
  for (let i = 0; i < max; i++) {
    const o = orig[i] !== undefined ? orig[i] : ''
    const c = curr[i] !== undefined ? curr[i] : ''
    if (o === c) {
      html += `<div style="padding:1px 4px;color:var(--mu2);font-size:11px;line-height:1.5">${escapeHtml(o) || '&nbsp;'}</div>`
    } else if (c && !o) {
      html += `<div style="padding:1px 4px;border-left:2px solid var(--ok);background:rgba(16,185,129,.1);color:var(--ok);font-size:11px;line-height:1.5;margin:1px 0;border-radius:0 3px 3px 0">${escapeHtml(c)}</div>`
      count++
    } else if (o && !c) {
      html += `<div style="padding:1px 4px;text-decoration:line-through;color:rgba(239,68,68,.6);font-size:11px;line-height:1.5;margin:1px 0">${escapeHtml(o)}</div>`
      count++
    } else {
      html += `<div style="padding:1px 4px;text-decoration:line-through;color:rgba(239,68,68,.6);font-size:11px">${escapeHtml(o)}</div>`
      html += `<div style="padding:1px 4px;border-left:2px solid var(--ok);background:rgba(16,185,129,.1);color:var(--ok);font-size:11px;border-radius:0 3px 3px 0">${escapeHtml(c)}</div>`
      count++
    }
  }
  return { html, count }
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

// ── Markdown ↔ HTML for contentEditable preview ───────────────────────────
function renderMarkdownToHtml(md: string): string {
  if (!md) return '<p>Comece a escrever…</p>'
  const lines = md.split('\n')
  let html = ''
  let inList = false
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    if (inList && !line.startsWith('- ') && !line.startsWith('* ')) {
      if (line.startsWith('#') || line.trim() === '' || i === lines.length - 1) {
        html += '</ul>'; inList = false
      }
    }
    if (line.startsWith('# ')) {
      if (inList) { html += '</ul>'; inList = false }
      html += `<h1>${escapeHtml(line.slice(2))}</h1>`
    } else if (line.startsWith('## ')) {
      if (inList) { html += '</ul>'; inList = false }
      html += `<h2>${escapeHtml(line.slice(3))}</h2>`
    } else if (line.startsWith('- ') || line.startsWith('* ')) {
      if (!inList) { html += '<ul>'; inList = true }
      const content = line.slice(2)
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/~~([^~]+)~~/g, '<del>$1</del>')
      html += `<li>${content}</li>`
    } else if (line.startsWith('---')) {
      if (inList) { html += '</ul>'; inList = false }
      html += '<hr />'
    } else if (line.trim()) {
      if (inList) { html += '</ul>'; inList = false }
      const content = line
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/~~([^~]+)~~/g, '<del>$1</del>')
      html += `<p>${content}</p>`
    }
  }
  if (inList) html += '</ul>'
  return html
}

function htmlToMarkdown(html: string): string {
  const md = html
    .replace(/<span[^>]*>/gi, '')
    .replace(/<\/span>/gi, '')
    .replace(/<div[^>]*>/gi, '')
    .replace(/<\/div>/gi, '\n')
    .replace(/ style="[^"]*"/gi, '')
    .replace(/<h1[^>]*>/gi, '# ')
    .replace(/<\/h1>/gi, '\n')
    .replace(/<h2[^>]*>/gi, '## ')
    .replace(/<\/h2>/gi, '\n')
    .replace(/<strong>/gi, '**')
    .replace(/<\/strong>/gi, '**')
    .replace(/<del[^>]*>/gi, '~~')
    .replace(/<\/del>/gi, '~~')
    .replace(/<ul[^>]*>/gi, '')
    .replace(/<\/ul>/gi, '')
    .replace(/<li[^>]*>/gi, '- ')
    .replace(/<\/li>/gi, '\n')
    .replace(/<p[^>]*>/gi, '')
    .replace(/<\/p>/gi, '\n')
    .replace(/<hr[^>]*>/gi, '---\n')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&nbsp;/g, ' ')
    .replace(/<[^>]+>/g, '')
    .replace(/^\s+$/gm, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
  return md
}

export default function EstrategiaRoom() {
  const { go, addToast, openChatWith, pendingDocId, initialTab, setPendingDocId, clearInitialTab } = useAppStore()
  const { clientId } = useAuth()
  const qc = useQueryClient()
  const [tab, setTab] = useState<Tab>('conhecimento')
  const [analyticsOpen, setAnalyticsOpen] = useState(false)

  // Document editor state
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null)
  const [editorContent, setEditorContent] = useState('')
  const [originalContent, setOriginalContent] = useState('')
  const editorRef = useRef<HTMLDivElement>(null)

  // Conhecimento (knowledge) tab state
  const [selectedFolder, setSelectedFolder] = useState('all')
  const [expandedFolderIds, setExpandedFolderIds] = useState<string[]>(['estrategia'])

  const [approvalsQ, approvalsDocsQ, insightsQ, historyQ, contextReportsQ, contextMetricsQ] = useQueries({
    queries: [
      {
        queryKey: ['approvals', 'estrategia', clientId ?? ''],
        queryFn: () => fetchApprovalsByAgent('estrategia', clientId!),
        enabled: !!clientId,
        staleTime: 30_000,
      },
      {
        queryKey: ['approvals', 'documentos', clientId ?? ''],
        queryFn: () => fetchApprovalsByAgent('documentos', clientId!),
        enabled: !!clientId,
        staleTime: 30_000,
      },
      {
        queryKey: ['insights'],
        queryFn: () => fetchInsights(10, 'estrategia'),
        enabled: !!clientId,
        staleTime: 60_000,
      },
      {
        queryKey: ['estrategia-history', clientId ?? ''],
        queryFn: () => fetchEstrategiaHistory(clientId!),
        enabled: !!clientId,
        staleTime: 60_000,
      },
      {
        queryKey: ['contextReports'],
        queryFn: () => fetchContextReports(),
        enabled: !!clientId,
        staleTime: 5 * 60_000,
      },
      {
        queryKey: ['analytics', 'contextMetrics', clientId ?? ''],
        queryFn: () => getContextMetrics(),
        enabled: !!clientId,
        staleTime: 5 * 60_000,
      },
    ],
  })

  // Gerador de Documentos — templates + criação via inline editor
  const [selectedTemplate, setSelectedTemplate] = useState<DocTemplate | null>(null)
  const [docBeingCreated, setDocBeingCreated] = useState<{ id: string; title: string } | null>(null)
  const [showTemplatePicker, setShowTemplatePicker] = useState(false)

  const docTemplatesQ = useQuery({
    queryKey: ['docTemplates', clientId ?? ''],
    queryFn: () => fetchDocTemplates(clientId!),
    enabled: !!clientId,
    staleTime: 5 * 60_000,
  })
  const docTemplates: DocTemplate[] = docTemplatesQ.data ?? []

  const createDocMut = useMutation({
    mutationFn: (title: string) => createDocument(clientId!, title),
    onSuccess: (doc) => {
      setDocBeingCreated({ id: doc.id, title: doc.title })
      setSelectedDocId(doc.id)
      const initialContent = editorContent && editorContent.trim()
        ? editorContent
        : `# ${doc.title}\n\nComece a escrever aqui...`
      setEditorContent(initialContent)
      setOriginalContent(initialContent)
      qc.invalidateQueries({ queryKey: ['documents', clientId] })
      addToast('ok', 'Documento criado', `Rascunho "${doc.title}" aberto no editor.`)
    },
    onError: (e: Error) => {
      addToast('no', 'Erro ao criar', e.message)
    },
  })

  const saveDocMut = useMutation({
    mutationFn: (text: string) => {
      const docId = docBeingCreated?.id ?? (selectedDocId && !selectedDocId.startsWith('report-') ? selectedDocId : null)
      if (!docId || !clientId) return Promise.resolve()
      const payload = { text, source: 'editor' as const, templateId: selectedTemplate?.id ?? null }
      return saveDocument(docId, clientId, payload)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents', clientId] })
      qc.invalidateQueries({ queryKey: ['recentDocuments', clientId] })
      addToast('ok', 'Salvo', 'Documento salvo.')
    },
    onError: (e: Error) => {
      addToast('no', 'Erro ao salvar', e.message)
    },
  })

  const handleStartFromTemplate = (tpl: DocTemplate) => {
    setSelectedTemplate(tpl)
    setEditorContent(`# ${tpl.name}\n\n${tpl.description ?? ''}\n\n`)
    createDocMut.mutate(tpl.name)
  }

  const handleStartBlank = () => {
    setSelectedTemplate(null)
    setEditorContent('')
    createDocMut.mutate('Novo Documento')
  }

  const approveMut = useMutation({
    mutationFn: (id: string) => approveRequest(id, clientId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['approvals', 'estrategia', clientId] })
      qc.invalidateQueries({ queryKey: ['approvals', 'documentos', clientId] })
      qc.invalidateQueries({ queryKey: ['estrategia-history', clientId] })
      addToast('ok', 'Aprovado', 'Análise aprovada.')
    },
  })

  const rejectMut = useMutation({
    mutationFn: (id: string) => rejectRequest(id, clientId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['approvals', 'estrategia', clientId] })
      qc.invalidateQueries({ queryKey: ['approvals', 'documentos', clientId] })
      addToast('no', 'Rejeitado', 'Análise rejeitada.')
    },
  })

  const snoozeMut = useMutation({
    mutationFn: (id: string) => snoozeApproval(id, clientId!, snoozeUntil()),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['approvals', 'estrategia', clientId] })
      qc.invalidateQueries({ queryKey: ['approvals', 'documentos', clientId] })
      addToast('sn', 'Adiado', 'Lembrete em 2 horas.')
    },
  })

  const approvals: ApprovalRequest[] = approvalsQ.data ?? []
  const allApprovals: ApprovalRequest[] = [...(approvalsDocsQ.data ?? []), ...(approvalsQ.data ?? [])]
  const history: EstrategiaHistoryItem[] = historyQ.data ?? []
  const insights: ClientInsight[] = (insightsQ.data ?? []).filter(
    () => true  // room filter is server-side via p_room='estrategia'
  )
  const contextReports: ContextReport[] = contextReportsQ.data ?? []
  const contextMetrics: ContextMetricRow[] = contextMetricsQ.data ?? []

  // Recent documents from the documents table (user-created docs)
  const recentDocsQ = useQuery({
    queryKey: ['recentDocuments', clientId ?? ''],
    queryFn: () => fetchRecentDocuments(clientId!),
    enabled: !!clientId,
    staleTime: 30_000,
  })
  const recentDocuments: BluDocument[] = recentDocsQ.data ?? []

  // Group context metrics by dimension for sidebar
  const estrategiaMetrics = contextMetrics.filter((m) => m.dimension === 'estrategia')

  // ── Document list: combine recent user docs + context reports ─────────
  const strategyDocs: StrategyDoc[] = [
    ...recentDocuments.map((d): StrategyDoc => {
      const ext = d.title?.split('.').pop()?.toLowerCase() ?? 'md'
      const meta = DOC_TYPE_META[ext] ?? { type: 'DOC', typeColor: 'var(--mu)', folder: 'documentos' }
      const contentRaw = d.editor_content
      const content = typeof contentRaw === 'string' ? contentRaw
        : contentRaw && typeof contentRaw === 'object' && 'text' in (contentRaw as Record<string, unknown>)
        ? (contentRaw as Record<string, unknown>).text as string
        : `# ${d.title}`
      return {
        id: d.id,
        name: d.title,
        type: meta.type,
        typeColor: meta.typeColor,
        date: new Date(d.created_at).toLocaleDateString('pt-BR', { day: 'numeric', month: 'short' }),
        content,
        folder: d.agent_slug === 'documentos' ? 'documentos' : d.agent_slug,
      }
    }),
    ...contextReports.map((r): StrategyDoc => {
      const ext = r.storage_path?.split('.').pop()?.toLowerCase() ?? 'md'
      const meta = DOC_TYPE_META[ext] ?? DOC_TYPE_META.md
      return {
        id: `report-${r.id}`,
        name: r.title,
        type: meta.type,
        typeColor: meta.typeColor,
        date: new Date(r.created_at).toLocaleDateString('pt-BR', { day: 'numeric', month: 'short', year: 'numeric' }),
        content: '',
        folder: 'relatorios',
      }
    }),
  ]

  // Resolve selected doc object
  const selectedDoc = selectedDocId
    ? strategyDocs.find((d) => d.id === selectedDocId) ?? null
    : null

  // Diff tracking
  const diff = computeDiff(originalContent, editorContent)
  const isDirty = diff.count > 0

  // ── Report content loader ────────────────────────────────────────────────
  const [reportLoading, setReportLoading] = useState(false)

  // ── Set contentEditable innerHTML only on doc switch (avoids cursor jump) ──
  useEffect(() => {
    if (!editorRef.current || !selectedDocId) return
    if (selectedDocId.startsWith('report-') && reportLoading) return
    editorRef.current.innerHTML = renderMarkdownToHtml(editorContent)
  }, [selectedDocId, reportLoading])

  // ── Track changes: Backspace/Delete → wrap in <del> (strikethrough) ──────
  useEffect(() => {
    const el = editorRef.current
    if (!el) return

    const handler = (e: InputEvent) => {
      if (e.inputType !== 'deleteContentBackward' && e.inputType !== 'deleteContentForward') return

      const sel = window.getSelection()
      if (!sel || !sel.rangeCount) return
      const range = sel.getRangeAt(0)

      let canHandle = true

      if (range.collapsed) {
        if (e.inputType === 'deleteContentBackward' && range.startOffset > 0) {
          range.setStart(range.startContainer, range.startOffset - 1)
        } else if (e.inputType === 'deleteContentForward') {
          const len = range.startContainer.textContent?.length ?? 0
          if (range.startOffset < len) {
            range.setEnd(range.startContainer, range.startOffset + 1)
          } else {
            canHandle = false
          }
        } else {
          canHandle = false
        }
      }

      if (!canHandle) return // browser handles normally (preventDefault not called)

      e.preventDefault()

      const fragment = range.extractContents()
      if (!fragment.textContent) return

      const del = document.createElement('del')
      del.appendChild(fragment)
      range.insertNode(del)

      range.setStartAfter(del)
      range.collapse(true)
      sel.removeAllRanges()
      sel.addRange(range)

      el.dispatchEvent(new Event('input', { bubbles: true }))
    }

    el.addEventListener('beforeinput', handler as EventListener)
    return () => el.removeEventListener('beforeinput', handler as EventListener)
  }, [editorRef.current])

  useEffect(() => {
    if (!selectedDocId || !selectedDocId.startsWith('report-')) return
    const report = contextReports.find((r) => `report-${r.id}` === selectedDocId)
    if (!report) return

    setReportLoading(true)
    downloadContextReport(report.storage_path)
      .then((md) => {
        setEditorContent(md)
        setOriginalContent(md)
        setReportLoading(false)
      })
      .catch(() => {
        setEditorContent(`# ${report.title}\n\nErro ao carregar relatório.`)
        setOriginalContent(`# ${report.title}\n\nErro ao carregar relatório.`)
        setReportLoading(false)
      })
  }, [selectedDocId])

  // ── Consume pendingDocId + initialTab from store (set by DecisionCard) ────
  useEffect(() => {
    if (pendingDocId && strategyDocs.length > 0) {
      const doc = strategyDocs.find((d) => d.id === pendingDocId)
      if (doc) {
        handleSelectDoc(doc)
        setTab('documentos')
      }
      setPendingDocId(null)
    }
    if (initialTab) {
      setTab(initialTab as Tab)
      clearInitialTab()
    }
  }, [pendingDocId, initialTab, strategyDocs.length])

  // ── Handlers ─────────────────────────────────────────────────────────────
  const handleSelectDoc = (doc: StrategyDoc) => {
    setSelectedDocId(doc.id)
    setEditorContent(doc.content)
    setOriginalContent(doc.content)
  }

  const handleSaveDoc = () => {
    if (selectedDocId?.startsWith('report-')) {
      addToast('sn', 'Somente leitura', 'Relatórios gerados não podem ser editados.')
      return
    }
    setOriginalContent(editorContent)
    saveDocMut.mutate(editorContent)
  }

  const handleNewDoc = () => {
    setShowTemplatePicker(true)
  }

  const handleReportClick = (report: ContextReport) => {
    const doc: StrategyDoc = {
      id: `report-${report.id}`,
      name: report.title,
      type: 'MD',
      typeColor: 'var(--violet)',
      date: new Date(report.created_at).toLocaleDateString('pt-BR'),
      folder: 'relatorios',
      content: `# ${report.title}\n\nRelatório gerado em ${new Date(report.created_at).toLocaleDateString('pt-BR')}.`,
    }
    handleSelectDoc(doc)
    setTab('documentos')
  }

  // Folder tree for Conhecimento tab
  const visibleFolderNodes = FOLDER_TREE.filter(
    (n) => !n.parentId || expandedFolderIds.includes(n.parentId),
  )

  const filteredConhecimentoDocs = selectedFolder === 'all'
    ? strategyDocs
    : strategyDocs.filter((d) => d.folder === selectedFolder)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div className="rh">
        <div className="rav">🎯</div>
        <div>
          <div className="rn">Estratégia</div>
          <div className="rd">Análises, KPIs e planejamento</div>
        </div>
        <div className="ra">
          <button className="btn bs" style={{ fontSize: 11 }} onClick={() => go('home', 'Início')}>
            ← Início
          </button>
          <button className="btn bp" style={{ fontSize: 11 }} onClick={() => openChatWith('Quero criar uma nova análise estratégica')}>
            + Nova Análise
          </button>
        </div>
      </div>

      <div className="room-grid">
        {/* MAIN PANEL */}
        <div className="panel" style={{ gridColumn: 1, gridRow: 1 }}>
          <div className="ph">
            <span className="ph-ttl">Mesa de Trabalho</span>
          </div>
          <div className="rtabs">
            {(['objetivos', 'documentos', 'conhecimento', 'config'] as Tab[]).map((t) => (
              <div
                key={t}
                className={`rtab${tab === t ? ' on' : ''}`}
                onClick={() => setTab(t)}
              >
                {t === 'objetivos' ? (
                  <>
                    Objetivos{' '}
                    {!approvalsQ.isLoading && !approvalsDocsQ.isLoading && allApprovals.length > 0 && (
                      <span className="tbdg">{allApprovals.length}</span>
                    )}
                  </>
                ) : t === 'documentos' ? (
                  'Documentos'
                ) : t === 'conhecimento' ? (
                  'Conhecimento'
                ) : (
                  'Config'
                )}
              </div>
            ))}
          </div>

          <div className="pb">
            {/* OBJETIVOS */}
            <div className={`tc${tab === 'objetivos' ? ' on' : ''}`}>
              {approvalsQ.isLoading || approvalsDocsQ.isLoading ? (
                <div className="dc" style={{ opacity: 0.4 }}>Carregando…</div>
              ) : allApprovals.length === 0 ? (
                <div style={{ fontSize: 12, color: 'var(--mu)', padding: '16px 0', textAlign: 'center' }}>
                  Nenhuma decisão pendente.
                </div>
              ) : (
                <div className="dl">
                  {allApprovals.map((ap) => (
                    ap.agent_slug === 'documentos' ? (
                      <ApprovalCardDocs key={ap.id} ap={ap} onSign={() => approveMut.mutate(ap.id)} onSnooze={() => snoozeMut.mutate(ap.id)} />
                    ) : (
                      <ApprovalCard
                        key={ap.id}
                        ap={ap}
                        onApprove={() => approveMut.mutate(ap.id)}
                        onReject={() => rejectMut.mutate(ap.id)}
                        onSnooze={() => snoozeMut.mutate(ap.id)}
                      />
                    )
                  ))}
                </div>
              )}
            </div>

            {/* DOCUMENTOS — inline editor with diff tracking */}
            <div className={`tc${tab === 'documentos' ? ' on' : ''}`} style={tab === 'documentos' ? { display: 'flex', flex: 1, overflow: 'hidden' } : undefined}>
              <div style={{ width: 230, flexShrink: 0, borderRight: '1px solid var(--gb)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                <div style={{ padding: '9px 10px', borderBottom: '1px solid var(--gb)', flexShrink: 0 }}>
                  <button
                    className="btn bp"
                    style={{ fontSize: 11, width: '100%', justifyContent: 'center' }}
                    onClick={handleNewDoc}
                    disabled={createDocMut.isPending}
                  >
                    + Novo Documento
                  </button>
                  {/* ── Template picker modal ── */}
                  {showTemplatePicker && (
                    <div
                      style={{
                        position: 'fixed',
                        inset: 0,
                        zIndex: 9999,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        background: 'rgba(0,0,0,.6)',
                      }}
                      onClick={() => setShowTemplatePicker(false)}
                    >
                      <div
                        style={{
                          background: 'var(--bg)',
                          border: '1px solid var(--gb)',
                          borderRadius: 'var(--r)',
                          width: 560,
                          maxHeight: '80vh',
                          display: 'flex',
                          flexDirection: 'column',
                          overflow: 'hidden',
                        }}
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', borderBottom: '1px solid var(--gb)' }}>
                          <span style={{ fontWeight: 700, fontSize: 13 }}>Novo Documento</span>
                          <button className="btn bs" style={{ fontSize: 11, padding: '2px 8px' }} onClick={() => setShowTemplatePicker(false)}>✕</button>
                        </div>
                        <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--gb)', display: 'flex', gap: 8, alignItems: 'center' }}>
                          <button className="btn bs" style={{ fontSize: 10.5 }} onClick={() => { setShowTemplatePicker(false); handleStartBlank() }}>
                            + Criar em branco
                          </button>
                          <span style={{ fontSize: 10.5, color: 'var(--mu)' }}>ou escolha um template:</span>
                        </div>
                        <div style={{ flex: 1, overflowY: 'auto', padding: 12, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                          {TEMPLATE_META.map((tpl) => (
                            <div
                              key={tpl.id}
                              onClick={() => {
                                setShowTemplatePicker(false)
                                const content = DOC_TEMPLATES[tpl.id] ?? `# ${tpl.name}\n\n`
                                setEditorContent(content)
                                createDocMut.mutate(tpl.name)
                              }}
                              style={{
                                display: 'flex',
                                gap: 10,
                                padding: '10px 12px',
                                borderRadius: 'var(--r)',
                                cursor: 'pointer',
                                background: 'color-mix(in srgb,var(--fg) 4%,transparent)',
                                border: '1px solid var(--gb)',
                                transition: 'border-color 0.1s, background 0.1s',
                              }}
                              onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--ac)'; e.currentTarget.style.background = 'color-mix(in srgb,var(--ac) 8%,transparent)' }}
                              onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--gb)'; e.currentTarget.style.background = 'color-mix(in srgb,var(--fg) 4%,transparent)' }}
                            >
                              <span style={{ fontSize: 22, flexShrink: 0 }}>{tpl.icon}</span>
                              <div style={{ flex: 1, minWidth: 0 }}>
                                <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--fg)', marginBottom: 2 }}>{tpl.name}</div>
                                <div style={{ fontSize: 10, color: 'var(--mu)', lineHeight: 1.4 }}>{tpl.desc}</div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                  {docTemplatesQ.isLoading ? (
                    <div style={{ fontSize: 9.5, color: 'var(--mu)', marginTop: 5 }}>carregando templates…</div>
                  ) : docTemplates.length > 0 ? (
                    <select
                      className="ipt"
                      style={{ fontSize: 10, padding: '3px 5px', marginTop: 5, width: '100%' }}
                      value={selectedTemplate?.id ?? ''}
                      onChange={(e) => {
                        const tpl = docTemplates.find((t) => t.id === e.target.value)
                        if (tpl) handleStartFromTemplate(tpl)
                      }}
                      disabled={createDocMut.isPending}
                    >
                      <option value="">Usar template…</option>
                      {docTemplates.map((tpl) => (
                        <option key={tpl.id} value={tpl.id}>
                          {tpl.name}
                        </option>
                      ))}
                    </select>
                  ) : null}
                </div>
                <div style={{ flex: 1, overflowY: 'auto', padding: 4 }}>
                  {strategyDocs.map((d) => {
                    const isSelected = d.id === selectedDocId
                    return (
                      <div
                        key={d.id}
                        onClick={() => handleSelectDoc(d)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 8,
                          padding: '6px 8px',
                          cursor: 'pointer',
                          borderRadius: 5,
                          marginBottom: 1,
                          background: isSelected ? 'var(--adim)' : 'transparent',
                          borderLeft: `2px solid ${isSelected ? 'var(--ac)' : 'transparent'}`,
                          transition: 'background 0.1s',
                        }}
                      >
                        <div
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            width: 28,
                            height: 28,
                            borderRadius: 5,
                            flexShrink: 0,
                            background: `${d.typeColor}18`,
                            border: `1px solid ${d.typeColor}30`,
                          }}
                        >
                          <span style={{ fontSize: 8, fontWeight: 800, letterSpacing: '0.04em', color: d.typeColor, fontFamily: 'var(--mono)' }}>
                            {d.type}
                          </span>
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div
                            style={{
                              fontSize: 11.5,
                              fontWeight: isSelected ? 600 : 400,
                              color: isSelected ? 'var(--fg)' : 'var(--mu2)',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            {d.name}
                          </div>
                          <div style={{ fontSize: 9.5, color: 'var(--mu)' }}>{d.date}</div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minHeight: 0 }}>
                {!selectedDoc && !selectedDocId?.startsWith('report-') ? (
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10, opacity: 0.4 }}>
                    <span style={{ fontSize: 32 }}>📄</span>
                    <span style={{ fontSize: 12, color: 'var(--mu)' }}>Selecione um documento para visualizar e editar</span>
                  </div>
                ) : reportLoading ? (
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10, opacity: 0.6 }}>
                    <span style={{ fontSize: 28 }}>⏳</span>
                    <span style={{ fontSize: 12, color: 'var(--mu)' }}>Carregando relatório…</span>
                  </div>
                ) : (
                  <>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '7px 12px', borderBottom: '1px solid var(--gb)', background: 'rgba(0,0,0,.15)', flexShrink: 0 }}>
                      <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--fg)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {selectedDoc?.name ?? ''}
                      </span>
                      <span
                        style={{
                          fontSize: 9.5,
                          fontWeight: 600,
                          padding: '2px 7px',
                          borderRadius: 3,
                          background: diff.count > 0 ? 'var(--adim)' : 'rgba(255,255,255,.06)',
                          color: diff.count > 0 ? 'var(--ac)' : 'var(--mu)',
                        }}
                      >
                        {diff.count} {diff.count === 1 ? 'alteração' : 'alterações'}
                      </span>
                      <button
                        className="btn bs"
                        style={{ fontSize: 11 }}
                        onClick={handleSaveDoc}
                        disabled={!isDirty || saveDocMut.isPending}
                        title={isDirty ? 'Salvar alterações' : 'Sem alterações'}
                      >
                        💾 Salvar
                      </button>
                      <button className="btn bp" style={{ fontSize: 11 }} onClick={() => addToast('sn', 'Em breve', 'Fluxo de assinatura em desenvolvimento.')}>
                        ✍️ Assinar
                      </button>
                    </div>

                    <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
                      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                        <div style={{ flex: 1, overflowY: 'auto', padding: '14px 16px' }}>
                          <style>{`
                            [contenteditable] del {
                              text-decoration: line-through;
                              color: rgba(239,68,68,.7);
                              background: rgba(239,68,68,.08);
                              border-radius: 2px;
                            }
                          `}</style>
                          <div
                            ref={editorRef}
                            contentEditable
                            suppressContentEditableWarning
                            style={{ outline: 'none', minHeight: '100%', lineHeight: 1.75, fontSize: 13 }}
                            onInput={(e) => {
                              const html = (e.target as HTMLElement).innerHTML
                              setEditorContent(htmlToMarkdown(html))
                            }}
                          />
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 12px', borderTop: '1px solid var(--gb)', background: 'rgba(0,0,0,.12)', flexShrink: 0 }}>
                      <span style={{ fontSize: 11, color: 'var(--mu)', flex: 1 }}>
                        {isDirty ? 'Alterações não salvas' : 'Sem alterações'}
                      </span>
                      <span
                        style={{
                          fontSize: 9.5,
                          fontWeight: 600,
                          padding: '2px 7px',
                          borderRadius: 3,
                          background: diff.count > 0 ? 'var(--adim)' : 'rgba(255,255,255,.06)',
                          color: diff.count > 0 ? 'var(--ac)' : 'var(--mu)',
                        }}
                      >
                        {diff.count} {diff.count === 1 ? 'alteração' : 'alterações'}
                      </span>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* CONHECIMENTO — folder tree + card grid */}
            <div className={`tc${tab === 'conhecimento' ? ' on' : ''}`} style={tab === 'conhecimento' ? { display: 'flex', flex: 1, overflow: 'hidden' } : undefined}>
              <div style={{ width: 216, flexShrink: 0, borderRight: '1px solid var(--gb)', display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'rgba(0,0,0,.1)' }}>
                <div style={{ padding: '9px 10px 7px', borderBottom: '1px solid var(--gb)', flexShrink: 0 }}>
                  <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--mu)' }}>
                    Pastas
                  </span>
                </div>
                <div style={{ flex: 1, overflowY: 'auto', padding: '5px 4px' }}>
                  {visibleFolderNodes.map((node) => {
                    const isSelected = selectedFolder === node.id
                    const isExpanded = expandedFolderIds.includes(node.id)
                    const docCount = node.id === 'all'
                      ? strategyDocs.length
                      : strategyDocs.filter((d) => d.folder === node.id).length
                    return (
                      <div
                        key={node.id}
                        onClick={() => {
                          if (node.hasChildren) {
                            setExpandedFolderIds((prev) =>
                              prev.includes(node.id)
                                ? prev.filter((id) => id !== node.id)
                                : [...prev, node.id]
                            )
                            setSelectedFolder(node.id)
                          } else {
                            setSelectedFolder(node.id)
                          }
                        }}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 6,
                          padding: `5px 8px 5px ${8 + node.depth * 14}px`,
                          cursor: 'pointer',
                          borderRadius: 4,
                          userSelect: 'none',
                          background: isSelected ? 'var(--adim)' : 'transparent',
                          borderLeft: `2px solid ${isSelected ? 'var(--ac)' : 'transparent'}`,
                          color: isSelected ? 'var(--fg)' : 'var(--mu2)',
                          transition: 'background 0.1s',
                        }}
                      >
                        <span style={{ fontSize: 13, flexShrink: 0 }}>{node.icon}</span>
                        <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 11.5 }}>
                          {node.label}
                        </span>
                        <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--mu)', flexShrink: 0 }}>
                          {docCount}
                        </span>
                        {node.hasChildren && (
                          <span
                            style={{
                              fontSize: 9,
                              color: 'var(--mu)',
                              flexShrink: 0,
                              transition: 'transform 0.15s',
                              transform: isExpanded ? 'rotate(90deg)' : 'none',
                            }}
                          >
                            ▶
                          </span>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>

              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                <div style={{ padding: '7px 12px', borderBottom: '1px solid var(--gb)', flexShrink: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 9.5, color: 'var(--mu)', flex: 1 }}>
                    {filteredConhecimentoDocs.length} {filteredConhecimentoDocs.length === 1 ? 'documento' : 'documentos'} — {FOLDER_LABELS[selectedFolder] ?? selectedFolder}
                  </span>
                  <button
                    className="btn bs"
                    style={{ fontSize: 10.5, padding: '3px 8px' }}
                    onClick={() => addToast('sn', 'Em breve', 'Upload de arquivos em desenvolvimento.')}
                  >
                    + Adicionar
                  </button>
                </div>
                <div style={{ margin: '8px 12px 2px', border: '1px dashed var(--gb)', borderRadius: 'var(--r)', padding: '6px 12px', textAlign: 'center', fontSize: 10.5, color: 'var(--mu)', flexShrink: 0 }}>
                  Arraste arquivos aqui (PDF, DOCX, CSV, XLSX, TXT)
                </div>
                <div style={{ flex: 1, overflowY: 'auto', padding: '8px 12px' }}>
                  {filteredConhecimentoDocs.length === 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 0', gap: 10, opacity: 0.4 }}>
                      <span style={{ fontSize: 28 }}>📂</span>
                      <span style={{ fontSize: 12, color: 'var(--mu)' }}>Nenhum documento nesta pasta</span>
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(175px, 1fr))', gap: 8 }}>
                      {filteredConhecimentoDocs.map((d) => (
                        <div
                          key={d.id}
                          onClick={() => {
                            handleSelectDoc(d)
                            setTab('documentos')
                          }}
                          style={{
                            display: 'flex',
                            flexDirection: 'column',
                            gap: 7,
                            padding: '11px 11px 9px',
                            background: 'rgba(0,0,0,.18)',
                            border: '1px solid var(--gb)',
                            borderRadius: 'var(--r)',
                            cursor: 'pointer',
                            transition: 'border-color 0.1s',
                          }}
                          onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--ac)' }}
                          onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--gb)' }}
                        >
                          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 6 }}>
                            <div
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                width: 36,
                                height: 36,
                                borderRadius: 7,
                                flexShrink: 0,
                                background: `${d.typeColor}18`,
                                border: `1px solid ${d.typeColor}30`,
                              }}
                            >
                              <span style={{ fontSize: 8.5, fontWeight: 800, letterSpacing: '0.04em', color: d.typeColor, fontFamily: 'var(--mono)' }}>
                                {d.type}
                              </span>
                            </div>
                            <span style={{ fontSize: 8.5, fontWeight: 700, padding: '2px 6px', borderRadius: 3, background: 'rgba(16,185,129,.15)', color: 'var(--ok)', alignSelf: 'flex-start', whiteSpace: 'nowrap' }}>
                              Pronto
                            </span>
                          </div>
                          <div
                            style={{
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
                            }}
                          >
                            {d.name}
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 5, flexWrap: 'wrap' }}>
                            <span style={{ fontSize: 9, padding: '1px 5px', borderRadius: 3, background: 'var(--glass)', color: 'var(--mu2)', border: '1px solid var(--gb)' }}>
                              {FOLDER_LABELS[d.folder] ?? d.folder}
                            </span>
                            <span style={{ fontSize: 9.5, color: 'var(--mu)', marginLeft: 'auto' }}>{d.date}</span>
                          </div>
                          <div style={{ fontSize: 10, color: 'var(--ac)', opacity: 0.8 }}>Abrir no editor</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* CONFIG */}
            <div className={`tc${tab === 'config' ? ' on' : ''}`}>
              <RoutineConfigSection domain="estrategia" />
              <RoutineConfigSection domain="documentos" />
            </div>
          </div>

          {/* ANALYTICS CARD — pinned at panel bottom */}
          <div className="anl-card">
            <div className="anl-hd" onClick={() => setAnalyticsOpen(o => !o)}>
              <span className="anl-ttl">📊 Analytics Estratégia</span>
              <div className="anl-nums">
                <div className="anl-kpi">
                  <span className="anl-v">{approvalsQ.isLoading ? '…' : approvals.length}</span>
                  <span className="anl-l">Pendentes</span>
                </div>
                <div className="anl-kpi">
                  <span className="anl-v" style={{ color: 'var(--ok)' }}>{historyQ.isLoading ? '…' : history.filter((h) => h.action === 'approved').length}</span>
                  <span className="anl-l">Aprovadas</span>
                </div>
              </div>
              <span className={`anl-chev${analyticsOpen ? ' open' : ''}`}>▶</span>
            </div>
            <div className={`anl-body${analyticsOpen ? ' open' : ''}`}>
              {estrategiaMetrics.length > 0 ? (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                  {estrategiaMetrics.map((m) => (
                    <div key={m.kpi} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10.5, background: 'color-mix(in srgb,var(--fg) 5%,transparent)', border: '1px solid color-mix(in srgb,var(--fg) 10%,transparent)', borderRadius: 4, padding: '3px 6px', overflow: 'hidden' }}>
                      <span style={{ color: 'var(--mu)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', minWidth: 0, flexShrink: 1 }}>{m.label}</span>
                      {m.current_value != null && (
                        <span style={{ fontFamily: 'var(--mono)', color: 'var(--fg)', fontWeight: 600, whiteSpace: 'nowrap', flexShrink: 0 }}>
                          {m.unit === 'R$'
                            ? formatCompactBRL(m.current_value)
                            : m.unit === '%'
                            ? `${m.current_value.toFixed(1)}%`
                            : m.current_value.toLocaleString('pt-BR')}
                        </span>
                      )}
                      {m.mom_pct != null && (
                        <span style={{ fontSize: 9, fontFamily: 'var(--mono)', color: m.mom_pct >= 0 ? 'var(--ok)' : 'var(--urg)', background: m.mom_pct >= 0 ? 'color-mix(in srgb,var(--ok) 12%,transparent)' : 'color-mix(in srgb,var(--urg) 12%,transparent)', padding: '1px 3px', borderRadius: 3, whiteSpace: 'nowrap', flexShrink: 0 }}>
                          {m.mom_pct >= 0 ? '↑' : '↓'}{Math.abs(m.mom_pct).toFixed(1)}%
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ fontSize: 11, color: 'var(--mu)' }}>Disponível após a primeira sincronização.</div>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN */}
        <div className="rcol">
          <RColResizeHandle />

          <CollapsiblePanel id="est-analises" icon="📊" title="Análises" badge={contextReports.length > 0 ? <span className="ph-cnt">{contextReports.length}</span> : null}>
              {contextReportsQ.isLoading ? (
                <div style={{ fontSize: 11, color: 'var(--mu)' }}>…</div>
              ) : contextReports.length === 0 ? (
                <div style={{ fontSize: 11, color: 'var(--mu)', padding: '8px 0', textAlign: 'center', lineHeight: 1.5 }}>
                  Nenhum relatório gerado ainda.<br />
                  <span style={{ fontSize: 10 }}>Disponível após a primeira sincronização.</span>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {contextReports.map((report) => {
                    const isSelected = selectedDocId === `report-${report.id}`
                    const date = new Date(report.created_at).toLocaleDateString('pt-BR', { month: 'short', year: 'numeric' })
                    return (
                      <div
                        key={report.id}
                        onClick={() => handleReportClick(report)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 8,
                          padding: '6px 8px',
                          borderRadius: 6,
                          cursor: 'pointer',
                          background: isSelected ? 'var(--gb)' : 'transparent',
                          borderLeft: isSelected ? '2px solid var(--ac)' : '2px solid transparent',
                          transition: 'background 0.1s',
                        }}
                      >
                        <span style={{ fontSize: 14, flexShrink: 0 }}>📄</span>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 11.5, fontWeight: isSelected ? 500 : 400, color: isSelected ? 'var(--fg)' : 'var(--mu2)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {report.title}
                          </div>
                          <div style={{ fontSize: 10, color: 'var(--mu)' }}>{date}</div>
                        </div>
                        {report.status === 'pending' && (
                          <span style={{ fontSize: 9, color: 'var(--mu)', background: 'var(--gb)', padding: '1px 4px', borderRadius: 3 }}>indexando</span>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
          </CollapsiblePanel>

          <div className="panel" style={{ flexShrink: 0 }}>
            <div className="ph">
              <span className="ph-ico">📈</span>
              <span className="ph-ttl">KPIs Estratégicos</span>
            </div>
            <div className="pb">
              {contextMetricsQ.isLoading ? (
                <div style={{ padding: 10, textAlign: 'center', fontSize: 11, color: 'var(--mu)' }}>Carregando KPIs…</div>
              ) : estrategiaMetrics.length === 0 ? (
                <div style={{ padding: 10, textAlign: 'center', fontSize: 11, color: 'var(--mu)' }}>Disponível após sincronização.</div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, padding: 10 }}>
                  {estrategiaMetrics.map((m) => {
                    const val = m.current_value != null
                      ? m.unit === 'R$'
                        ? formatCompactBRL(m.current_value)
                        : m.unit === '%'
                        ? `${m.current_value.toFixed(1)}%`
                        : m.current_value.toLocaleString('pt-BR')
                      : '—'
                    const delta = m.mom_pct != null
                      ? `${m.mom_pct >= 0 ? '+' : ''}${m.mom_pct.toFixed(1)}${m.unit === '%' ? 'pp' : '%'}`
                      : null
                    const deltaColor = m.mom_pct != null
                      ? m.mom_pct > 0 && m.kpi === 'churn' ? 'var(--urg)'
                        : m.mom_pct < 0 && m.kpi === 'churn' ? 'var(--ok)'
                        : m.mom_pct >= 0 ? 'var(--ok)' : 'var(--urg)'
                      : 'var(--mu)'
                    return (
                      <div key={m.kpi} className="kpi-cell">
                        <div className="kpi-lbl">{m.label}</div>
                        <div className="kpi-val" style={{ fontSize: 15 }}>{val}</div>
                        {delta != null && (
                          <div className="kpi-d" style={{ color: deltaColor }}>{delta} mês</div>
                        )}
                        <Sparkline
                          data={[30, 45, 38, 52, 48, 61, 55, 68, 72, 65, 78, 84]}
                          width={100} height={24}
                          color={deltaColor}
                        />
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* BOTTOM STRIP */}
        <div className="bstrip">
          {insights.slice(0, 3).map((ins) => (
            <div key={ins.id} className="ich">
              <span className="ich-em">📈</span>
              <div className="ich-body">
                <span className="ich-tag tg-e">Estratégia</span>
                <div className="ich-txt">{ins.title}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Approval card ──────────────────────────────────────────────
function ApprovalCard({
  ap,
  onApprove,
  onReject,
  onSnooze,
}: {
  ap: ApprovalRequest
  onApprove: () => void
  onReject: () => void
  onSnooze: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const priorityColor = ap.priority === 'urgent' ? '#f87171' : ap.priority === 'high' ? 'var(--orange)' : 'var(--yellow)'

  return (
    <div className={`dc warn${expanded ? ' expanded' : ''}`}>
      <div className="dc-row" onClick={() => setExpanded(!expanded)}>
        <div className="ag">
          <div className="agd" style={{ background: priorityColor }} />
          Estratégia
        </div>
        <span className="bdg bw">
          {ap.priority === 'urgent' ? 'Urgente' : ap.priority === 'high' ? 'Atenção' : 'Alerta'}
        </span>
        <span className="dc-row-summary">{ap.title}</span>
        <span className="dt">
          {new Date(ap.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
        </span>
        <span className="dc-chev">{expanded ? '▼' : '▶'}</span>
      </div>
      {expanded && (
        <div className="dc-expand">
          {ap.body && <div className="db">{ap.body}</div>}
          <div className="dc-act">
            <button className="btn bp" onClick={onApprove}>👍 Aprovar</button>
            <button className="btn bs" onClick={onSnooze}>⏰ Depois</button>
            <button className="btn bg" onClick={onReject}>Ignorar</button>
          </div>
        </div>
      )}
    </div>
  )
}

function ApprovalCardDocs({ ap, onSign, onSnooze }: { ap: ApprovalRequest; onSign: () => void; onSnooze: () => void }) {
  const [expanded, setExpanded] = useState(false)
  const priorityColor = ap.priority === 'urgent' ? '#f87171' : ap.priority === 'high' ? 'var(--orange)' : 'var(--yellow)'
  return (
    <div className={`dc warn${expanded ? ' expanded' : ''}`}>
      <div className="dc-row" onClick={() => setExpanded(!expanded)}>
        <div className="ag"><div className="agd" style={{ background: priorityColor }} />Documentos</div>
        <span className="bdg bw">{ap.priority === 'urgent' ? 'Urgente' : ap.priority === 'high' ? 'Atencao' : 'Alerta'}</span>
        <span className="dc-row-summary">{ap.title}</span>
        <span className="dt">{new Date(ap.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</span>
        <span className="dc-chev">{expanded ? 'v' : '>'}</span>
      </div>
      {expanded && (
        <div className="dc-expand">
          {ap.body && <div className="db">{ap.body}</div>}
          <div className="dc-act">
            <button className="btn bp" onClick={onSign}>Assinar</button>
            <button className="btn bs" onClick={onSnooze}>Depois</button>
          </div>
        </div>
      )}
    </div>
  )
}
