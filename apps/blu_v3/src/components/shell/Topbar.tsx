import { useRef, useState, useEffect } from 'react'
import { useAuth } from '@blu/auth'
import { useAppStore } from '../../store/appStore'
import { IconSearch, IconBell, IconSignOut } from '../shared/Icons'

interface TopbarProps {
  onToggleTheme: () => void
  lightMode: boolean
  onOpenSearch: () => void
}

export default function Topbar({ onToggleTheme, lightMode, onOpenSearch }: TopbarProps) {
  const { breadcrumb, go } = useAppStore()
  const { user, signOut } = useAuth()
  const isHome = breadcrumb === 'Bom dia ☀️'

  const rawName: string =
    (user?.user_metadata?.full_name as string | undefined) ??
    (user?.user_metadata?.name as string | undefined) ??
    ''
  const firstName = rawName.split(' ')[0] ?? ''
  const greeting = firstName ? `Bom dia, ${firstName} ☀️` : 'Bom dia ☀️'

  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // Close menu on outside click
  useEffect(() => {
    if (!menuOpen) return
    const handler = (e: MouseEvent) => {
      if (!menuRef.current?.contains(e.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [menuOpen])

  const initials = user?.email
    ? user.email.slice(0, 2).toUpperCase()
    : 'BL'

  return (
    <header className="topbar">
      <div className="logo">
        <svg className="logo-bubble-svg" width="54" height="48" viewBox="0 0 80 72" fill="none" aria-hidden="true">
          <defs>
            <linearGradient id="bluGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--ac)"/>
              <stop offset="100%" stopColor="var(--blue2)"/>
            </linearGradient>
            <clipPath id="bluClip">
              <path d="M12,0 H68 Q80,0 80,12 V48 Q80,60 68,60 H26 L12,72 L18,60 H12 Q0,60 0,48 V12 Q0,0 12,0 Z"/>
            </clipPath>
          </defs>
          <path d="M12,0 H68 Q80,0 80,12 V48 Q80,60 68,60 H26 L12,72 L18,60 H12 Q0,60 0,48 V12 Q0,0 12,0 Z" fill="url(#bluGrad)"/>
          <ellipse cx="38" cy="10" rx="26" ry="6" fill="rgba(255,255,255,0.18)"/>
          <g clipPath="url(#bluClip)">
            <path d="M-2,40 Q20,32 40,40 Q60,48 82,40 L82,74 L-2,74 Z" fill="rgba(255,255,255,0.22)"/>
            <path d="M-2,50 Q20,42 40,50 Q60,58 82,50 L82,74 L-2,74 Z" fill="var(--gb2)"/>
          </g>
          <text x="40" y="38" textAnchor="middle"
            fontFamily="'Nunito',-apple-system,BlinkMacSystemFont,system-ui,sans-serif"
            fontSize="22" fontWeight="900" fill="white" letterSpacing="-0.5">blu</text>
        </svg>
      </div>
      <div className="topbar-mid">
        {isHome ? (
          <span id="bc">{greeting}</span>
        ) : (
          <span id="bc">
            <span
              style={{ cursor: 'pointer', color: 'var(--mu)' }}
              onClick={() => go('home', 'Início')}
            >
              Início
            </span>
            {' '}
            <span style={{ color: 'var(--mu)', opacity: 0.5 }}>/</span>
            {' '}
            {breadcrumb}
          </span>
        )}
      </div>
      <div className="topbar-end">
        {/* Theme toggle */}
        <button
          className="ibtn"
          onClick={onToggleTheme}
          title={lightMode ? 'Modo escuro' : 'Modo claro'}
          style={{ fontSize: 13 }}
        >
          {lightMode ? '🌙' : '☀️'}
        </button>
        <button className="ibtn" onClick={onOpenSearch} title="Buscar (⌘K)">
          <IconSearch size={14} />
        </button>
        <button className="ibtn" onClick={() => go('atividade', 'Atividade')}>
          <IconBell size={14} />
          <span className="rdot" />
        </button>

        {/* User menu */}
        <div ref={menuRef} style={{ position: 'relative' }}>
          <div className="av" onClick={() => setMenuOpen(o => !o)} title={user?.email ?? ''}>
            {initials}
          </div>
          {menuOpen && (
            <div style={{
              position: 'absolute', top: 'calc(100% + 8px)', right: 0,
              background: 'var(--glass)', backdropFilter: 'blur(20px)',
              border: '1px solid var(--gb)', borderRadius: 'var(--rl)',
              minWidth: 180, padding: '6px', zIndex: 200,
            }}>
              {user?.email && (
                <div style={{
                  padding: '6px 10px 8px', fontSize: 11,
                  color: 'var(--mu)', borderBottom: '1px solid var(--gb)', marginBottom: 4,
                }}>
                  {user.email}
                </div>
              )}
              <button
                onClick={() => { setMenuOpen(false); void signOut() }}
                style={{
                  width: '100%', textAlign: 'left', padding: '7px 10px',
                  background: 'none', border: 'none', borderRadius: 6,
                  color: 'var(--fg)', fontSize: 12, cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: 8,
                }}
                onMouseEnter={e => (e.currentTarget.style.background = 'var(--gb)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'none')}
              >
                <IconSignOut size={13} />
                Sair
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
