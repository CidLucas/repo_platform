import { useLocation, useNavigate } from 'react-router-dom'
import { Home, Settings, X, Wand2, Lock } from 'lucide-react'
import { cn } from '@/utils/cn'
import { AgentBadge } from '@/components/navigation/AgentBadge'
import { AGENTS } from '@/utils/constants'
import { useAgents, useAgentReadinessMap } from '@/hooks/useAgent'
import type { AgentSlug } from '@/types/agent'
import type { ReactNode } from 'react'

const ACCENT = '#8C5FDB'

const STATIC_NAV = [
  { label: 'Início', route: '/', icon: Home },
] as const

const BOTTOM_NAV = [
  { label: 'Personalizar Agente', route: '/onboarding', icon: Wand2 },
  { label: 'Admin', route: '/admin', icon: Settings },
] as const

interface AgentNavProps {
  open: boolean
  onClose: () => void
}

export function AgentNav({ open, onClose }: AgentNavProps) {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { data: enabledAgents = [] } = useAgents()
  const readinessMap = useAgentReadinessMap()

  const pendingMap = Object.fromEntries(
    enabledAgents.map((a) => [a.agent_slug, a.pending_count])
  )
  const statusMap = Object.fromEntries(
    enabledAgents.map((a) => [a.agent_slug, a.current_status])
  )

  const handleNav = (route: string) => {
    navigate(route)
    onClose()
  }

  const isActive = (route: string) =>
    route === '/' ? pathname === '/' : pathname.startsWith(route)

  return (
    <>
      {/* Mobile backdrop */}
      {open && (
        <div
          className="fixed inset-0 bg-base/60 backdrop-blur-sm z-overlay lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar panel */}
      <nav
        aria-label="Navegação principal"
        className={cn(
          'fixed top-0 left-0 h-dvh z-modal border-r border-border',
          'flex flex-col py-4',
          // Mobile: full width slides in/out
          'w-60',
          // Desktop: icon-only 48px, always visible, renders above main content
          'lg:w-12 lg:z-raised lg:translate-x-0',
          'transition-transform duration-slow ease-out',
          open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
        )}
        style={{ background: 'linear-gradient(180deg, #0d1425 0%, #0e1a2e 100%)' }}
      >
        {/* Mobile close button */}
        <div className="flex items-center justify-between px-4 mb-4 lg:hidden">
          <span className="font-display text-heading-md font-bold text-white">blu</span>
          <button
            onClick={onClose}
            aria-label="Fechar menu"
            className="text-gray-400 hover:text-white cursor-pointer transition-colors duration-fast
              w-8 h-8 flex items-center justify-center rounded hover:bg-elevated"
          >
            <X size={16} />
          </button>
        </div>

        {/* Desktop: "B" logo mark — no wordmark */}
        <div className="hidden lg:flex items-center justify-center mb-5 h-10">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center text-white text-xs font-bold"
            style={{ background: ACCENT }}
          >
            B
          </div>
        </div>

        {/* Static nav items */}
        <div className="px-2 mb-1">
          {STATIC_NAV.map(({ label, route, icon: Icon }) => (
            <NavItem
              key={route}
              label={label}
              active={isActive(route)}
              onClick={() => handleNav(route)}
              icon={<Icon size={16} strokeWidth={1.75} />}
              accentColor={ACCENT}
            />
          ))}
        </div>

        <div className="mx-2 mb-2 border-t border-border" />

        {/* Agent rooms */}
        <div className="px-2 flex-1 overflow-y-auto scroll-container">
          {/* Section label hidden on desktop (icon-only) */}
          <p className="text-section-label px-3 mb-2 lg:hidden">Agentes</p>
          {AGENTS.map((def) => {
            const pending = pendingMap[def.slug] ?? 0
            const status = statusMap[def.slug as AgentSlug] ?? 'idle'
            const readiness = readinessMap[def.slug]
            const isBlocked = readiness?.status === 'blocked'
            const isPartial = readiness?.status === 'partial'
            const badgeStatus = isBlocked ? 'offline' : isPartial ? 'attention' : status
            const missingDocs = readiness?.missing_docs ?? []

            return (
              <AgentNavItem
                key={def.slug}
                label={def.name}
                active={isActive(def.route)}
                onClick={isBlocked ? undefined : () => handleNav(def.route)}
                pendingCount={isBlocked ? 0 : pending}
                agentColor={def.color}
                agentGlow={def.glowColor}
                isBlocked={isBlocked}
                isPartial={isPartial}
                missingDocs={missingDocs}
                icon={
                  <AgentBadge
                    shape={def.shape}
                    color={def.color}
                    glowColor={def.glowColor}
                    status={badgeStatus}
                    size={18}
                  />
                }
              />
            )
          })}
        </div>

        <div className="mx-2 my-2 border-t border-border" />

        {/* Bottom nav */}
        <div className="px-2">
          {BOTTOM_NAV.map(({ label, route, icon: Icon }) => (
            <NavItem
              key={route}
              label={label}
              active={isActive(route)}
              onClick={() => handleNav(route)}
              icon={<Icon size={16} strokeWidth={1.75} />}
              accentColor={ACCENT}
            />
          ))}
        </div>
      </nav>
    </>
  )
}

interface NavItemProps {
  label: string
  active: boolean
  onClick: () => void
  icon: ReactNode
  accentColor?: string
  pendingCount?: number
}

/** Generic nav item (Início, Admin, Personalizar) */
function NavItem({ label, active, onClick, icon, accentColor = ACCENT }: NavItemProps) {
  return (
    <button
      onClick={onClick}
      title={label}
      className={cn(
        'w-full flex items-center gap-3 px-3 py-2 rounded-md',
        // Desktop: center the icon, hide label
        'lg:justify-center lg:px-0 lg:py-2.5',
        'text-body-sm transition-all duration-normal cursor-pointer',
        'focus-visible:ring-2 focus-visible:ring-offset-1 focus-visible:outline-none',
        active ? 'text-white' : 'text-gray-400 hover:text-white hover:bg-white/5'
      )}
      style={active ? {
        background: `${accentColor}18`,
        borderLeft: `2px solid ${accentColor}`,
      } : undefined}
    >
      <span
        className={cn(
          'shrink-0 inline-flex items-center justify-center w-7 h-7 rounded-lg',
          active ? '' : 'text-gray-500'
        )}
        style={active ? { background: `${accentColor}25`, color: accentColor } : undefined}
      >
        {icon}
      </span>
      {/* Label visible on mobile, hidden on desktop */}
      <span className="flex-1 truncate lg:hidden">{label}</span>
    </button>
  )
}

interface AgentNavItemProps extends NavItemProps {
  agentColor: string
  agentGlow: string
  isBlocked?: boolean
  isPartial?: boolean
  missingDocs?: string[]
}

/** Agent room nav item — uses agent's own color for active glow */
function AgentNavItem({
  label,
  active,
  onClick,
  icon,
  pendingCount,
  agentColor,
  isBlocked = false,
  isPartial = false,
  missingDocs = [],
}: AgentNavItemProps) {
  const tooltipText = isBlocked && missingDocs.length > 0
    ? `Documentos necessários: ${missingDocs.slice(0, 3).join(', ')}${missingDocs.length > 3 ? ` +${missingDocs.length - 3}` : ''}`
    : label

  const inner = (
    <span className="w-full flex items-center gap-3 px-3 py-2 rounded-md lg:justify-center lg:px-0 lg:py-2.5">
      <span className="shrink-0 w-7 h-7 flex items-center justify-center relative">
        {icon}
        {/* Desktop pending dot — sits on the icon corner */}
        {!isBlocked && pendingCount != null && pendingCount > 0 && (
          <span
            className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full border border-[#0d1425] hidden lg:block"
            style={{ background: agentColor }}
          />
        )}
      </span>
      {/* Mobile: label + badges */}
      <span className={cn('flex-1 truncate lg:hidden', isBlocked ? 'text-gray-600' : '')}>{label}</span>
      {isBlocked && <Lock size={11} className="shrink-0 text-gray-600 lg:hidden" />}
      {isPartial && !isBlocked && (
        <span className="shrink-0 w-1.5 h-1.5 rounded-full bg-amber-400 lg:hidden" />
      )}
      {!isBlocked && pendingCount != null && pendingCount > 0 && (
        <span
          className="flex items-center justify-center min-w-[18px] h-[18px]
            rounded-full px-1 text-caption-sm font-medium text-white leading-none lg:hidden"
          style={{ background: agentColor }}
        >
          {pendingCount > 99 ? '99+' : pendingCount}
        </span>
      )}
    </span>
  )

  if (isBlocked) {
    return (
      <div
        title={tooltipText}
        className={cn(
          'w-full text-body-sm rounded-md select-none',
          'text-gray-600 cursor-not-allowed opacity-60',
        )}
      >
        {inner}
      </div>
    )
  }

  return (
    <button
      onClick={onClick}
      title={tooltipText}
      className={cn(
        'w-full text-body-sm transition-all duration-normal cursor-pointer rounded-md',
        'focus-visible:ring-2 focus-visible:ring-blu-500 focus-visible:outline-none',
        active ? 'text-white' : 'text-gray-400 hover:text-white hover:bg-white/5'
      )}
      style={active ? {
        background: `${agentColor}15`,
        borderLeft: `2px solid ${agentColor}`,
        boxShadow: `inset 0 0 20px ${agentColor}08`,
      } : undefined}
    >
      {inner}
    </button>
  )
}
