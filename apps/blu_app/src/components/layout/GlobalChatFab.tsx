import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { MessageCircle } from 'lucide-react'
import { cn } from '@/utils/cn'
import { ChatOverlay } from '@/components/interactions/ChatOverlay'
import { AGENTS } from '@/utils/constants'

function agentColorForPath(pathname: string) {
  const base = '/' + pathname.split('/')[1]
  const agent = AGENTS.find((a) => a.route === base)
  return {
    color: agent?.color ?? '#3b82f6',
    glowColor: agent?.glowColor ?? 'rgba(59,130,246,0.4)',
  }
}

export function GlobalChatFab() {
  const { pathname } = useLocation()
  const { color, glowColor } = agentColorForPath(pathname)
  const [open, setOpen] = useState(false)

  // Keyboard shortcut: Cmd+\ or Ctrl+\
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (!(e.metaKey || e.ctrlKey) || e.code !== 'Backslash') return
      const target = e.target as HTMLElement | null
      const tag = target?.tagName?.toLowerCase()
      if (tag === 'input' || tag === 'textarea' || target?.isContentEditable) return
      e.preventDefault()
      setOpen((v) => !v)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  const isMac =
    typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform)
  const shortcutLabel = isMac ? '⌘\\' : 'Ctrl+\\'

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        aria-label="Abrir assistente"
        title={`Assistente · ${shortcutLabel}`}
        className={cn(
          'fixed bottom-6 right-6 z-30',
          open && 'hidden',
          'w-14 h-14 rounded-full',
          'flex items-center justify-center',
          'transition-transform duration-fast cursor-pointer',
          'hover:scale-110 active:scale-95',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-base',
        )}
        style={{
          backgroundColor: color,
          boxShadow: `0 8px 24px ${glowColor}`,
          ['--tw-ring-color' as string]: color,
        }}
      >
        <MessageCircle size={22} className="text-white" strokeWidth={1.75} />
      </button>

      <ChatOverlay
        open={open}
        onClose={() => setOpen(false)}
        currentPage={pathname}
      />
    </>
  )
}
