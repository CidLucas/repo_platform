import { useState, useRef, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { Menu, LogOut, User } from 'lucide-react'
import { cn } from '@/utils/cn'
import { GlobalSearch } from '@/components/navigation/GlobalSearch'
import { NotificationBell } from '@/components/navigation/NotificationBell'
import { useAuth } from '@/hooks/useAuth'

const ROOM_NAMES: Record<string, string> = {
  '/': 'Início',
  '/compras': 'Compras',
  '/financeiro': 'Financeiro',
  '/agenda': 'Agenda',
  '/documentos': 'Documentos',
  '/estrategia': 'Estratégia',
  '/clientes': 'Clientes',
  '/admin': 'Admin',
  '/onboarding': 'Personalizar Agente',
}

interface NavBarProps {
  onMenuToggle: () => void
  className?: string
}

export function NavBar({ onMenuToggle, className }: NavBarProps) {
  const { pathname } = useLocation()
  const { user, signOut } = useAuth()
  const [avatarOpen, setAvatarOpen] = useState(false)
  const avatarRef = useRef<HTMLDivElement>(null)

  const roomName = ROOM_NAMES[pathname] ?? ''
  const initials = user?.email?.slice(0, 2).toUpperCase() ?? 'BL'

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (avatarRef.current && !avatarRef.current.contains(e.target as Node)) {
        setAvatarOpen(false)
      }
    }
    if (avatarOpen) document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [avatarOpen])

  return (
    <header
      className={cn(
        'fixed top-4 left-4 right-4 z-sticky',
        'flex items-center justify-between',
        'bg-surface/80 backdrop-blur-md',
        'border border-border rounded-md',
        'px-4 h-12 shadow-md',
        className
      )}
    >
      {/* Left — hamburger (mobile) + logo + room name */}
      <div className="flex items-center gap-3">
        {/* Hamburger — only visible on mobile */}
        <button
          onClick={onMenuToggle}
          aria-label="Abrir navegação"
          className={cn(
            'lg:hidden flex items-center justify-center w-8 h-8 rounded',
            'text-gray-300 hover:text-white hover:bg-elevated',
            'transition-colors duration-normal cursor-pointer',
            'focus-visible:ring-2 focus-visible:ring-blu-500 focus-visible:outline-none'
          )}
        >
          <Menu size={18} strokeWidth={1.5} />
        </button>

        {/* Logo wordmark */}
        <span className="font-display text-heading-md font-bold text-white tracking-tight select-none">
          blu
        </span>

        {/* Room name separator + label */}
        {roomName && (
          <>
            <span className="text-gray-600 text-body-sm select-none hidden sm:inline">/</span>
            <span className="text-gray-300 text-body-sm hidden sm:inline">{roomName}</span>
          </>
        )}
      </div>

      {/* Right — search, bell, avatar */}
      <div className="flex items-center gap-1">
        <GlobalSearch />
        <NotificationBell />

        {/* Avatar + dropdown */}
        <div ref={avatarRef} className="relative ml-1">
          <button
            onClick={() => setAvatarOpen((v) => !v)}
            aria-label="Menu do usuário"
            aria-expanded={avatarOpen}
            className={cn(
              'flex items-center justify-center w-7 h-7 rounded-full',
              'bg-blu-800 border border-blu-600',
              'text-caption-sm font-medium text-blu-200 select-none',
              'hover:border-blu-400 transition-colors cursor-pointer',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blu-500'
            )}
          >
            {initials}
          </button>

          {avatarOpen && (
            <div
              className={cn(
                'absolute right-0 top-full mt-2 w-52 z-modal',
                'bg-surface border border-border rounded-md shadow-lg',
                'py-1 animate-slide-up'
              )}
            >
              <div className="px-3 py-2 border-b border-border">
                <div className="flex items-center gap-2 mb-0.5">
                  <User size={13} strokeWidth={1.5} className="text-gray-400 shrink-0" />
                  <p className="text-caption text-gray-300 truncate">{user?.email}</p>
                </div>
              </div>
              <button
                onClick={() => { setAvatarOpen(false); void signOut() }}
                className={cn(
                  'w-full flex items-center gap-2 px-3 py-2 text-left',
                  'text-body-sm text-gray-300 hover:text-white hover:bg-elevated',
                  'transition-colors cursor-pointer'
                )}
              >
                <LogOut size={14} strokeWidth={1.5} />
                Sair
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
