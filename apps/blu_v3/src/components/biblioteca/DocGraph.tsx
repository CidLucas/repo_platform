/**
 * DocGraph — BKL-032 (Modo Grafo da Biblioteca)
 *
 * Variante focada do grafo de conhecimento: mostra apenas documentos
 * e suas conexoes com a categoria correspondente, com layout em grid
 * concentrico por categoria. Foi separado do GraphView para oferecer
 * uma visualizacao mais densa e minimalista quando o usuario quiser
 * ver apenas as relacoes doc->categoria (sem o ruido das entidades
 * inferidas).
 */

import { useMemo } from 'react'
import type { KBDocument } from '../../services/knowledgeBaseService'
import { KB_CATEGORIES } from '../../services/knowledgeBaseService'

// ── Types ──────────────────────────────────────────────────────

export interface DocGraphProps {
  documents: KBDocument[]
  onSelectDocument?: (docId: string) => void
}

interface DocNode {
  id: string
  label: string
  category: string | null
  x: number
  y: number
  status: KBDocument['status']
}

interface CatNode {
  id: string
  label: string
  x: number
  y: number
  count: number
}

// ── Constants ──────────────────────────────────────────────────

const W = 800
const H = 520

// ── Helpers ────────────────────────────────────────────────────

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

export default function DocGraph({ documents, onSelectDocument }: DocGraphProps) {
  const { docNodes, catNodes, edges, usedCategories } = useMemo(() => {
    const grouped = new Map<string | null, KBDocument[]>()
    for (const d of documents) {
      const key = d.category ?? null
      const arr = grouped.get(key) ?? []
      arr.push(d)
      grouped.set(key, arr)
    }

    const catList = KB_CATEGORIES.filter(c => grouped.has(c.value))
    if (grouped.has(null)) {
      // Categoria "sem categoria" exibida no canto inferior direito.
      catList.push({ value: '__sem_cat__', label: 'Sem categoria' } as typeof catList[number])
    }

    const cats: CatNode[] = catList.map((c, i) => {
      const angle = (i / Math.max(1, catList.length)) * Math.PI * 2 - Math.PI / 2
      const radius = 170
      const count = grouped.get(c.value === '__sem_cat__' ? null : c.value)?.length ?? 0
      return {
        id: `cat:${c.value}`,
        label: c.label,
        x: W / 2 + Math.cos(angle) * radius,
        y: H / 2 + Math.sin(angle) * radius,
        count,
      }
    })

    const docs: DocNode[] = []
    catList.forEach((c, ci) => {
      const catKey = c.value === '__sem_cat__' ? null : c.value
      const list = grouped.get(catKey) ?? []
      const center = cats[ci]
      list.forEach((d, di) => {
        const angle = (di / Math.max(1, list.length)) * Math.PI * 2
        const r = 50 + (di % 2) * 14
        docs.push({
          id: `doc:${d.id}`,
          label: d.file_name,
          category: d.category,
          x: center.x + Math.cos(angle) * r,
          y: center.y + Math.sin(angle) * r,
          status: d.status,
        })
      })
    })

    const e = docs
      .filter(d => d.category)
      .map(d => ({ from: d.id, to: `cat:${d.category}` }))

    return {
      docNodes: docs,
      catNodes: cats,
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
          O grafo aparecera aqui assim que voce adicionar documentos a Biblioteca.
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
        <span style={{ fontWeight: 600, color: 'var(--fg)' }}>🕸️ DocGraph</span>
        <span>{documents.length} documento{documents.length !== 1 ? 's' : ''}</span>
        <span>•</span>
        <span>{usedCategories.length} categoria{usedCategories.length !== 1 ? 's' : ''}</span>
        <span style={{ marginLeft: 'auto', fontSize: 9.5, color: 'var(--mu)' }}>
          Clique em um documento para seleciona-lo
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
            const a = docNodes.find(n => n.id === edge.from)
            const b = catNodes.find(n => n.id === edge.to)
            if (!a || !b) return null
            return (
              <line
                key={`edge-${i}`}
                x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                stroke="rgba(255,87,255,0.10)"
                strokeWidth={0.8}
              />
            )
          })}

          {/* category nodes */}
          {catNodes.map(c => (
            <g key={c.id} transform={`translate(${c.x},${c.y})`}>
              <rect
                x={-52} y={-18} width={104} height={36}
                rx={6}
                fill="rgba(255,87,1,0.20)"
                stroke="#FF5701"
                strokeWidth={1.4}
              />
              <text
                x={0} y={-2}
                textAnchor="middle"
                fontSize={10.5}
                fontWeight={700}
                fill="#FF5701"
                style={{ fontFamily: 'var(--mono)' }}
              >
                {c.label.length > 16 ? c.label.slice(0, 15) + '…' : c.label}
              </text>
              <text
                x={0} y={11}
                textAnchor="middle"
                fontSize={9}
                fill="rgba(255,87,1,0.7)"
                style={{ fontFamily: 'var(--mono)' }}
              >
                {c.count} doc{c.count !== 1 ? 's' : ''}
              </text>
            </g>
          ))}

          {/* document nodes */}
          {docNodes.map(d => {
            const fill = statusColor(d.status)
            return (
              <g
                key={d.id}
                transform={`translate(${d.x},${d.y})`}
                style={{ cursor: onSelectDocument ? 'pointer' : 'default' }}
                onClick={() => onSelectDocument?.(d.id.split(':')[1])}
              >
                <circle r={6} fill={`${fill}33`} stroke={fill} strokeWidth={1.2} />
                <circle r={2.4} fill={fill} />
                <title>{d.label}</title>
              </g>
            )
          })}
        </svg>
      </div>
    </div>
  )
}
