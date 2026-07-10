import { useState, useMemo } from 'react'
import {
  House, ShoppingCart, ChartBar, CalendarDots,
  Target, UsersThree,
  Bell, Gear, Monitor, Books,
} from '@phosphor-icons/react'
import { useAppStore, Screen } from '../../store/appStore'
import { usePendingApprovals } from '../../hooks/useApprovals'
import { useMyRole } from '../../hooks/useAdmin'
import { useAuth } from '../../hooks/useAuth'
import { IconX, IconList } from '../shared/Icons'

interface NavItem {
  s: Screen
  icon: React.ReactNode
  label: string
}

const ICON_SIZE = 22
const ICON_WEIGHT = 'regular' as const

const NAV_ITEMS: NavItem[] = [
  { s: 'home',       icon: <House         size="22" weight="regular" />, label: 'Início' },
  { s: 'compras',    icon: <ShoppingCart  size="22" weight="regular" />, label: 'Compras' },
  { s: 'financeiro', icon: <ChartBar      size="22" weight="regular" />, label: 'Financeiro' },
  { s: 'agenda',     icon: <CalendarDots  size="22" weight="regular" />, label: 'Agenda' },
  { s: 'estrategia', icon: <Target        size="22" weight="regular" />, label: 'Estratégia' },
  { s: 'clientes',   icon: <UsersThree    size="22" weight="regular" />, label: 'Clientes' },
  { s: 'biblioteca', icon: <Books         size="22" weight="regular" />, label: 'Biblioteca' },
  { s: 'atividade',  icon: <Bell          size="22" weight="regular" />, label: 'Atividade' },
  { s: 'admin',      icon: <Gear          size="22" weight="regular" />, label: 'Admin' },
  { s: 'blu_ops',    icon: <Monitor       size="22" weight="regular" />, label: 'AgentOps' },
];

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

  const visibleFootSlugs = new Set(visibleFootItems.map(item => item.s))
  const desktopMainItems = NAV_ITEMS.filter(item => !visibleFootSlugs.has(item.s))

  const allItems = [...desktopMainItems, ...visibleFootItems]

  return (
    <>
      <aside className="sidebar" data-spotlight-target="sidebar">
        {desktopMainItems.map(renderDesktopItem)}
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
            <IconX size={18} />
          ) : (
            <IconList size={18} />
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

