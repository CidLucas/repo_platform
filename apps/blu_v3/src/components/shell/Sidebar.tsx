import { useState, useMemo } from 'react'
import { useAppStore, Screen } from '../../store/appStore'
import { usePendingApprovals } from '../../hooks/useApprovals'

interface NavItem {
  s: Screen
  icon: string
  label: string
}

const NAV_ITEMS: NavItem[] = [
  { s: 'home',       icon: '🏠', label: 'Início' },
  { s: 'compras',    icon: '🛒', label: 'Compras' },
  { s: 'financeiro', icon: '📊', label: 'Financeiro' },
  { s: 'agenda',     icon: '📅', label: 'Agenda' },
  { s: 'documentos', icon: '✍️', label: 'Documentos' },
  { s: 'estrategia', icon: '🎯', label: 'Estratégia' },
  { s: 'agentes',    icon: '🤖', label: 'Agentes' },
  { s: 'clientes',   icon: '👥', label: 'Clientes' },
  { s: 'biblioteca', icon: '📚', label: 'Biblioteca' },
]

const FOOT_ITEMS: NavItem[] = [
  { s: 'atividade', icon: '🔔', label: 'Atividade' },
  { s: 'admin',     icon: '⚙️', label: 'Admin' },
  { s: 'blu_ops',   icon: '🖥️', label: 'AgentOps' },
]

export default function Sidebar() {
  const { screen, go } = useAppStore()
  const [menuOpen, setMenuOpen] = useState(false)
  const { data: pendingApprovals = [] } = usePendingApprovals()

  const badgeCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const a of pendingApprovals) {
      if (a.agent_slug) {
        counts[a.agent_slug] = (counts[a.agent_slug] ?? 0) + 1
      }
    }
    return counts
  }, [pendingApprovals])

  const renderDesktopItem = (item: NavItem) => {
    const count = badgeCounts[item.s] ?? 0
    return (
      <div
        key={item.s}
        className={`ni${screen === item.s ? ' on' : ''}`}
        data-s={item.s}
        data-tip={item.label}
        onClick={() => go(item.s, item.label)}
      >
        <span className="ni-icon">{item.icon}</span>
        {count > 0 && <span className="nb y">{count}</span>}
      </div>
    )
  }

  const allItems = [...NAV_ITEMS, ...FOOT_ITEMS]

  return (
    <>
      <aside className="sidebar">
        {NAV_ITEMS.map(renderDesktopItem)}
        <div className="sb-foot">
          {FOOT_ITEMS.map(renderDesktopItem)}
        </div>
      </aside>

      {/* Mobile bottom nav — hidden on desktop via CSS */}
      <div className="mobile-nav">
        <button
          className="mobile-burger"
          onClick={() => setMenuOpen(o => !o)}
          aria-label="Menu"
        >
          {menuOpen ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
            </svg>
          )}
        </button>
      </div>

      {menuOpen && (
        <div className="mobile-overlay" onClick={() => setMenuOpen(false)}>
          <div className="mobile-menu" onClick={e => e.stopPropagation()}>
            <div className="mobile-menu-handle" />
            <div className="mobile-menu-grid">
              {allItems.map(item => {
                const count = badgeCounts[item.s] ?? 0
                return (
                  <div
                    key={item.s}
                    className={`mobile-mi${screen === item.s ? ' on' : ''}`}
                    onClick={() => { go(item.s, item.label); setMenuOpen(false) }}
                  >
                    <span className="mobile-mi-icon">{item.icon}</span>
                    <span className="mobile-mi-label">{item.label}</span>
                    {count > 0 && <span className="nb y">{count}</span>}
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
