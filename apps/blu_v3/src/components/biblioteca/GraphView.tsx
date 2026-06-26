/**
 * GraphView — BKL-032 (Modo Grafo da Biblioteca)
 *
 * Renderiza um grafo de conhecimento estatico (SVG) mostrando as
 * relacoes entre documentos, categorias e entidades inferidas a partir
 * do nome/descricao do arquivo.
 *
 * Layout: categorias como nos quadrados maiores ao redor; documentos
 * distribuidos em orbital; entidades como nos menores ligados aos
 * documentos que as referenciam.
 *
 * NAO usa libs externas de grafo (react-flow, d3) — apenas SVG puro
 * para manter a dependencia minima e funcionar offline.
 */

import { useMemo } from 'react'
import type { KBDocument } from '../../services/knowledgeBaseService'
import { KB_CATEGORIES } from '../../services/knowledgeBaseService'

// ── Types ──────────────────────────────────────────────────────

export interface GraphViewProps {
  documents: KBDocument[]
  onSelectDocument?: (docId: string) => void
}

interface DocNode {
  id: string
  label: string
  category: string | null
  x: number
  y: number
  kind: 'doc'
  status: KBDocument['status']
}

interface CatNode {
  id: string
  label: string
  x: number
  y: number
  kind: 'cat'
}

interface EntityNode {
  id: string
  label: string
  x: number
  y: number
  kind: 'entity'
}

type AnyNode = DocNode | CatNode | EntityNode

interface Edge {
  from: string
  to: string
}

// ── Constants ──────────────────────────────────────────────────

const W = 800
const H = 520
const CAT_RADIUS = 200

// Stopwords PT-BR minimas para extrair "entidades" do nome do arquivo.
const STOPWORDS = new Set([
  'a', 'o', 'as', 'os', 'de', 'do', 'da', 'dos', 'das', 'e', 'em', 'no',
  'na', 'nos', 'nas', 'para', 'por', 'com', 'sem', 'um', 'uma', 'uns',
  'umas', 'ao', 'aos', 'à', 'às', 'ou', 'se', 'que', 'é', 'são', 'pdf',
  'doc', 'docx', 'xls', 'xlsx', 'csv', 'txt', 'md', 'json', 'pptx',
])

// ── Helpers ────────────────────────────────────────────────────

function extractEntities(doc: KBDocument, max = 3): string[] {
  const text = [doc.file_name, doc.description ?? ''].join(' ')
  const tokens = text
    .toLowerCase()
    .replace(/\.[a-z0-9]+$/i, '')
    .split(/[^a-zà-ú0-9]+/i)
    .filter(t => t.length >= 4 && !STOPWORDS.has(t))
  const unique: string[] = []
  for (const t of tokens) {
    if (!unique.includes(t) && unique.length < max) unique.push(t)
  }
  return unique
}

function statusColor(status: KBDocument['status']): string {
  switch (status) {
    case 'completed':        return '#22c55e'
    case 'processing':       return '#f59e0b'
    case 'pending':          return '#94a3b8'
    case 'failed':           return '#ef4444'
    case 'partially_failed': return '#f97316'
    default:                 return '#94a3b8'
  }
}

// ── Component ──────────────────────────────────────────────────

export default function GraphView({ documents, onSelectDocument }: GraphViewProps) {
  const { nodes, edges, usedCategories } = useMemo(() => {
    const cats = new Set<string>()
    for (const d of documents) {
      if (d.category) cats.add(d.category)
    }
    const catList = KB_CATEGORIES.filter(c => cats.has(c.value))

    const catNodes: CatNode[] = catList.map((c, i) => {
      const angle = (i / Math.max(1, catList.length)) * Math.PI * 2 - Math.PI / 2
      return {
        id: `cat:${c.value}`,
        label: c.label,
        x: W / 2 + Math.cos(angle) * CAT_RADIUS,
        y: H / 2 + Math.sin(angle) * CAT_RADIUS,
        kind: 'cat',
      }
    })

    const docNodes: DocNode[] = documents.map((d, i) => {
      const angle = (i / Math.max(1, documents.length)) * Math.PI * 2
      const r = 110 + (i % 3) * 30
      return {
        id: `doc:${d.id}`,
        label: d.file_name,
        category: d.category,
        x: W / 2 + Math.cos(angle) * r,
        y: H / 2 + Math.sin(angle) * r,
        kind: 'doc',
        status: d.status,
      }
    })

    const entityMap = new Map<string, EntityNode>()
    const entityIndexByDoc = new Map<string, string[]>()
    documents.forEach((d, idx) => {
      const ents = extractEntities(d)
      entityIndexByDoc.set(d.id, ents)
      ents.forEach((ent, j) => {
        if (entityMap.has(ent)) return
        const angle = (idx / Math.max(1, documents.length)) * Math.PI * 2 + (j * 0.4)
        const r = 250 + (j * 18)
        entityMap.set(ent, {
          id: `ent:${ent}`,
          label: ent,
          x: W / 2 + Math.cos(angle) * r,
          y: H / 2 + Math.sin(angle) * r,
          kind: 'entity',
        })
      })
    })
    const entNodes: EntityNode[] = Array.from(entityMap.values())

    const e: Edge[] = []
    for (const d of docNodes) {
      if (d.category) {
        e.push({ from: `doc:${d.id.split(':')[1]}`, to: `cat:${d.category}` })
      }
    }
    for (const [docId, ents] of entityIndexByDoc.entries()) {
      for (const ent of ents) {
        e.push({ from: `doc:${docId}`, to: `ent:${ent}` })
      }
    }

    return {
      nodes: [...catNodes, ...docNodes, ...entNodes] as AnyNode[],
      edges: e,
      usedCategories: catList,
    }
  }, [documents])

  if (documents.length === 0) {
    return (
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        color: 'var(--mu)',
        fontSize: 12,
        padding: 40,
      }}>
        <div style={{ fontSize: 32, opacity: 0.4 }}>🕸️</div>
        <div style={{ fontWeight: 600, color: 'var(--mu2)' }}>Grafo vazio</div>
        <div style={{ fontSize: 10.5, textAlign: 'center', maxWidth: 320 }}>
          Adicione documentos a Biblioteca para visualizar as relacoes entre arquivos, categorias e entidades.
        </div>
      </div>
    )
  }

  return (
    <div style={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      gap: 8,
      padding: '8px 14px 14px',
      minHeight: 0,
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        fontSize: 10.5,
        color: 'var(--mu2)',
        flexWrap: 'wrap',
      }}>
        <span style={{ fontWeight: 600, color: 'var(--fg)' }}>🕸️ Grafo de conhecimento</span>
        <span>{documents.length} documento{documents.length !== 1 ? 's' : ''}</span>
        <span>•</span>
        <span>{usedCategories.length} categoria{usedCategories.length !== 1 ? 's' : ''}</span>
        <span style={{ marginLeft: 'auto', display: 'flex', gap: 10, alignItems: 'center' }}>
          <Legend swatch="#3b82f6" label="Documento" />
          <Legend swatch="#FF5701" label="Categoria" />
          <Legend swatch="#8b5cf6" label="Entidade" />
        </span>
      </div>

      <div style={{
        flex: 1,
        minHeight: 0,
        background: 'rgba(0,0,0,0.18)',
        border: '1px solid var(--gb)',
        borderRadius: 'var(--r)',
        overflow: 'hidden',
        position: 'relative',
      }}>
        <svg
          viewBox={`0 0 ${W} ${H}`}
          width="100%"
          height="100%"
          preserveAspectRatio="xMidYMid meet"
          style={{ display: 'block' }}
        >
          {/* edges */}
          {edges.map((edge, i) => {
            const a = nodes.find(n => n.id === edge.from)
            const b = nodes.find(n => n.id === edge.to)
            if (!a || !b) return null
            return (
              <line
                key={`e-${i}`}
                x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                stroke="rgba(255,255,255,0.10)"
                strokeWidth={1}
              />
            )
          })}

          {/* nodes */}
          {nodes.map(node => {
            if (node.kind === 'cat') {
              return (
                <g key={node.id} transform={`translate(${node.x},${node.y})`}>
                  <rect
                    x={-48} y={-16} width={96} height={32}
                    rx={6}
                    fill="rgba(255,87,1,0.18)"
                    stroke="#FF5701"
                    strokeWidth={1.2}
                  />
                  <text
                    x={0} y={4}
                    textAnchor="middle"
                    fontSize={10.5}
                    fontWeight={700}
                    fill="#FF5701"
                    style={{ fontFamily: 'var(--mono)' }}
                  >
                    {node.label.length > 14 ? node.label.slice(0, 13) + '…' : node.label}
                  </text>
                </g>
              )
            }
            if (node.kind === 'entity') {
              return (
                <g key={node.id} transform={`translate(${node.x},${node.y})`}>
                  <circle r={4} fill="#8b5cf6" stroke="rgba(255,255,255,0.2)" strokeWidth={0.5} />
                  <text
                    x={6} y={3}
                    fontSize={8.5}
                    fill="rgba(139,92,246,0.85)"
                    style={{ fontFamily: 'var(--mono)' }}
                  >
                    {node.label}
                  </text>
                </g>
              )
            }
            // doc
            const fill = statusColor(node.status)
            return (
              <g
                key={node.id}
                transform={`translate(${node.x},${node.y})`}
                style={{ cursor: onSelectDocument ? 'pointer' : 'default' }}
                onClick={() => onSelectDocument?.(node.id.split(':')[1])}
              >
                <circle r={7} fill={`${fill}33`} stroke={fill} strokeWidth={1.2} />
                <circle r={2.5} fill={fill} />
                <title>{node.label}</title>
              </g>
            )
          })}
        </svg>
      </div>
    </div>
  )
}

function Legend({ swatch, label }: { swatch: string; label: string }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
      <span style={{
        width: 9, height: 9, borderRadius: 4,
        background: swatch, display: 'inline-block',
      }} />
      <span>{label}</span>
    </span>
  )
}
