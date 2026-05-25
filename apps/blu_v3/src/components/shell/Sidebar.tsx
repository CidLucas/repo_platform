import { useState, useMemo } from 'react'
import {
  House, ShoppingCart, ChartBar, CalendarDots,
  PencilSimpleLine, Target, UsersThree,
  Bell, Gear, Monitor,
} from '@phosphor-icons/react'
import { useAppStore, Screen } from '../../store/appStore'
import { usePendingApprovals } from '../../hooks/useApprovals'
import { useMyRole } from '../../hooks/useAdmin'
import { useAuth } from '../../hooks/useAuth'

interface NavItem {
  s: Screen
  icon: React.ReactNode
  label: string
}

const ICON_SIZE = 22
const ICON_WEIGHT = 'regular' as const

const NAV_ITEMS: NavItem[] = [
  { s: 'home',       icon: <House       size={ICON_SIZE} weight={ICON_WEIGHT} />, label: 'Início' },
  { s: 'compras',    icon: <ShoppingCart size={ICON_SIZE} weight={ICON_WEIGHT} />, label: 'Compras' },
  { s: 'financeiro', icon: <ChartBar    size={ICON_SIZE} weight={ICON_WEIGHT} />, label: 'Financeiro' },
  { s: 'agenda',     icon: <CalendarDots size={ICON_SIZE} weight={ICON_WEIGHT} />, label: 'Agenda' },
  { s: 'documentos', icon: <PencilSimpleLine size={ICON_SIZE} weight={ICON_WEIGHT} />, label: 'Documentos' },
  { s: 'estrategia', icon: <Target      size={ICON_SIZE} weight={ICON_WEIGHT} />, label: 'Estratégia' },
  { s: 'clientes',   icon: <UsersThree  size={ICON_SIZE} weight={ICON_WEIGHT} />, label: 'Clientes' },
]

const FOOT_ITEMS: NavItem[] = [
  { s: 'atividade', icon: <Bell    size={ICON_SIZE} weight={ICON_WEIGHT} />, label: 'Atividade' },
  { s: 'admin',     icon: <Gear    size={ICON_SIZE} weight={ICON_WEIGHT} />, label: 'Admin' },
  { s: 'blu_ops',   icon: <Monitor size={ICON_SIZE} weight={ICON_WEIGHT} />, label: 'AgentOps' },
]

export default function Sidebar() {
  const { screen, go } = useAppStore()
  const [menuOpen, setMenuOpen] = useState(false)
  const { data: pendingApprovals = [] } = usePendingApprovals()
  const { tier } = useAuth()
  const { data: myRole } = useMyRole()

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

  const visibleFootItems = FOOT_ITEMS.filter(item => {
    if (item.s === 'admin') return myRole === 'owner'
    if (item.s === 'blu_ops') return tier === 'ADMIN'
    return true
  })

  const allItems = [...NAV_ITEMS, ...visibleFootItems]

  return (
    <>
      <aside className="sidebar" data-spotlight-target="sidebar">
        {NAV_ITEMS.map(renderDesktopItem)}
        <div className="sb-foot">
          {visibleFootItems.map(renderDesktopItem)}
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
