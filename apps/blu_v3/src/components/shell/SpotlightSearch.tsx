import { useState, useEffect, useRef, useCallback } from 'react'
import { useAppStore, type Screen } from '../../store/appStore'
import { useAuth } from '../../hooks/useAuth'
import { useMyRole } from '../../hooks/useAdmin'
import { IconSearch } from '../shared/Icons'

interface SpotlightItem {
  s: Screen
  label: string
  desc: string
  icon: string
}

const BASE_ITEMS: SpotlightItem[] = [
  { s: 'home',       label: 'Início',      desc: 'Visão geral e decisões do dia',               icon: '🏠' },
  { s: 'compras',    label: 'Compras',     desc: 'Aprovações, fornecedores e tarefas',           icon: '🛒' },
  { s: 'financeiro', label: 'Financeiro',  desc: 'Fluxo de caixa, pagamentos e relatórios',      icon: '📊' },
  { s: 'agenda',     label: 'Agenda',      desc: 'Reuniões, rotinas e planejamento semanal',     icon: '📅' },
  { s: 'estrategia', label: 'Estratégia',  desc: 'Metas, OKRs e planos de ação',                icon: '🎯' },
  { s: 'clientes',   label: 'Clientes',    desc: 'Base de clientes e relacionamento',            icon: '👥' },
  { s: 'biblioteca', label: 'Biblioteca', desc: 'Propostas, contratos e memória de negócio',     icon: '📚' },
  { s: 'atividade',  label: 'Atividade',   desc: 'Notificações e histórico de ações',            icon: '🔔' },
]

interface Props {
  open: boolean
  onClose: () => void
}

function normalize(s: string) {
  return s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
}

export default function SpotlightSearch({ open, onClose }: Props) {
  const { go } = useAppStore()
  const { tier } = useAuth()
  const { data: myRole } = useMyRole()

  const [query, setQuery] = useState('')
  const [activeIdx, setActiveIdx] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  const items = BASE_ITEMS.concat([
    ...(myRole === 'owner' ? [{ s: 'admin' as Screen, label: 'Admin', desc: 'Configurações, integrações e controles', icon: '⚙️' }] : []),
    ...(tier === 'ADMIN'   ? [{ s: 'blu_ops' as Screen, label: 'AgentOps', desc: 'Monitoramento de agentes e operações internas', icon: '🖥️' }] : []),
  ])

  const filtered = query.trim()
    ? items.filter(it => {
        const q = normalize(query)
        return normalize(it.label).includes(q) || normalize(it.desc).includes(q)
      })
    : items

  useEffect(() => {
    if (open) {
      setQuery('')
      setActiveIdx(0)
      setTimeout(() => inputRef.current?.focus(), 30)
    }
  }, [open])

  useEffect(() => { setActiveIdx(0) }, [query])

  const navigate = useCallback((item: SpotlightItem) => {
    go(item.s, item.label)
    onClose()
  }, [go, onClose])

  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { onClose(); return }
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setActiveIdx(i => Math.min(i + 1, filtered.length - 1))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setActiveIdx(i => Math.max(i - 1, 0))
      } else if (e.key === 'Enter' && filtered[activeIdx]) {
        navigate(filtered[activeIdx])
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, filtered, activeIdx, navigate, onClose])

  // Scroll active item into view
  useEffect(() => {
    const el = listRef.current?.children[activeIdx] as HTMLElement | undefined
    el?.scrollIntoView({ block: 'nearest' })
  }, [activeIdx])

  if (!open) return null

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 500,
        background: 'rgba(0,0,0,0.45)',
        backdropFilter: 'blur(4px)',
        display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
        paddingTop: 120,
      }}
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div style={{
        width: '100%', maxWidth: 520,
        background: 'var(--surface, rgba(8,18,48,0.95))',
        border: '1px solid var(--gb)',
        borderRadius: 'var(--rl)',
        boxShadow: '0 24px 64px rgba(0,0,0,0.55)',
        overflow: 'hidden',
      }}>
        {/* Search input row */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '12px 16px',
          borderBottom: '1px solid var(--gb)',
        }}>
          <IconSearch size={15} />
          <input
            ref={inputRef}
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Ir para…"
            style={{
              flex: 1, background: 'none', border: 'none', outline: 'none',
              color: 'var(--fg)', fontSize: 14, fontFamily: 'var(--body)',
            }}
          />
          <kbd style={{
            fontSize: 10, color: 'var(--mu)', border: '1px solid var(--gb)',
            borderRadius: 4, padding: '2px 5px', flexShrink: 0,
          }}>esc</kbd>
        </div>

        {/* Results list */}
        <div ref={listRef} style={{ maxHeight: 360, overflowY: 'auto', padding: '6px' }}>
          {filtered.length === 0 && (
            <div style={{ padding: '16px', color: 'var(--mu)', fontSize: 13, textAlign: 'center' }}>
              Nenhum resultado
            </div>
          )}
          {filtered.map((item, i) => (
            <div
              key={item.s}
              onMouseDown={() => navigate(item)}
              onMouseEnter={() => setActiveIdx(i)}
              style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '9px 12px', borderRadius: 8, cursor: 'pointer',
                background: i === activeIdx ? 'var(--gb)' : 'transparent',
                transition: 'background 100ms',
              }}
            >
              <span style={{ fontSize: 18, width: 24, textAlign: 'center', flexShrink: 0 }}>{item.icon}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, color: 'var(--fg)', fontWeight: 500 }}>{item.label}</div>
                <div style={{ fontSize: 11, color: 'var(--mu)', marginTop: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.desc}</div>
              </div>
              {i === activeIdx && (
                <kbd style={{ fontSize: 10, color: 'var(--mu)', border: '1px solid var(--gb)', borderRadius: 4, padding: '2px 5px', flexShrink: 0 }}>↵</kbd>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
