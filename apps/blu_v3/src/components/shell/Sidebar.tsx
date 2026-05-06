import { useAppStore, Screen } from '../../store/appStore'

interface NavItem {
  s: Screen
  icon: string
  label: string
  badge?: string
}

const NAV_ITEMS: NavItem[] = [
  { s: 'home',       icon: '🏠', label: 'Início' },
  { s: 'compras',    icon: '🛒', label: 'Compras',    badge: '' },
  { s: 'financeiro', icon: '📊', label: 'Financeiro', badge: 'y' },
  { s: 'agenda',     icon: '📅', label: 'Agenda' },
  { s: 'documentos', icon: '✍️', label: 'Documentos' },
  { s: 'estrategia', icon: '🎯', label: 'Estratégia' },
  { s: 'clientes',   icon: '👥', label: 'Clientes' },
]

const FOOT_ITEMS: NavItem[] = [
  { s: 'atividade', icon: '🔔', label: 'Atividade' },
  { s: 'admin',     icon: '⚙️', label: 'Admin' },
]

export default function Sidebar() {
  const { screen, go } = useAppStore()

  const renderItem = (item: NavItem) => (
    <div
      key={item.s}
      className={`ni${screen === item.s ? ' on' : ''}`}
      data-s={item.s}
      data-tip={item.label}
      onClick={() => go(item.s, item.label)}
    >
      <span className="ni-icon">{item.icon}</span>
      {item.badge !== undefined && <span className={`nb${item.badge ? ' ' + item.badge : ''}`} />}
    </div>
  )

  return (
    <aside className="sidebar">
      {NAV_ITEMS.map(renderItem)}
      <div className="sb-foot">
        {FOOT_ITEMS.map(renderItem)}
      </div>
    </aside>
  )
}
