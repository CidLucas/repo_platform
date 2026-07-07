import { useState, useEffect, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useAppStore } from '../../store/appStore'
import type { Screen } from '../../store/appStore'
import Topbar from './Topbar'
import Sidebar from './Sidebar'
import ToastContainer from '../shared/Toast'
import EditorOverlay from '../shared/EditorOverlay'
import ChatPanel from '../chat/ChatPanel'
import FirstRunOverlay from '../onboarding/FirstRunOverlay'
import ConnectionsModal from '../onboarding/ConnectionsModal'
import ErrorBoundary from '../shared/ErrorBoundary'
import ErrorFallback from '../shared/ErrorFallback'
import HomePage from '../../pages/app/HomePage'
import ComprasRoom from '../../pages/app/ComprasRoom'
import FinanceiroRoom from '../../pages/app/FinanceiroRoom'
import AgendaRoom from '../../pages/app/AgendaRoom'
import EstrategiaRoom from '../../pages/app/EstrategiaRoom'
import ClientesRoom from '../../pages/app/ClientesRoom'
import AtividadeScreen from '../../pages/app/AtividadeScreen'
import AdminScreen from '../../pages/app/AdminScreen'
import AgentOpsRoom from '../../pages/app/AgentOpsRoom'
import BusinessMemoryPage from '../../pages/app/BusinessMemoryPage'
import SpotlightSearch from './SpotlightSearch'
import { useAuth } from '../../hooks/useAuth'
import { useMyRole } from '../../hooks/useAdmin'

export default function AppShell() {
  const screen = useAppStore(s => s.screen)
  const firstRun = useAppStore(s => s.firstRun)
  const initFirstRun = useAppStore(s => s.initFirstRun)
  const qc = useQueryClient()
  const { clientId, tier } = useAuth()
  const { data: myRole } = useMyRole()
  const [editorOpen, setEditorOpen] = useState(false)
  const [connectionsOpen, setConnectionsOpen] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  // Initialize from unscoped key for instant first paint; useEffect below re-reads the scoped key
  const [lightMode, setLightMode] = useState(() => {
    try { return localStorage.getItem('blu-theme') === 'light' } catch { return false }
  })

  // Track which screens have been visited so we only mount them on first activation.
  // Once mounted, screens stay mounted (preserving React Query cache and scroll state).
  // Seed with the store's initial screen so a refresh to e.g. #room/financeiro mounts it immediately.
  const [visited, setVisited] = useState<Set<Screen>>(() => new Set([useAppStore.getState().screen]))

  useEffect(() => {
    setVisited(prev => {
      if (prev.has(screen)) return prev
      const next = new Set(prev)
      next.add(screen)
      return next
    })
  }, [screen])

  // Invalidate analytics indicator queries when switching rooms so stale error
  // states (e.g. from a prior schema misconfiguration) are recovered automatically.
  // Rooms stay mounted forever, so refetchOnMount never fires after first visit.
  useEffect(() => {
    if (screen === 'financeiro') {
      void qc.invalidateQueries({ queryKey: ['finance-indicators'] })
    } else if (screen === 'clientes' || screen === 'compras') {
      void qc.invalidateQueries({ queryKey: ['analytics'] })
    }
  }, [screen, qc])

  // After Google Calendar OAuth redirect, invalidate calendar queries
  useEffect(() => {
    if (sessionStorage.getItem('cal_oauth_done') !== '1') return
    sessionStorage.removeItem('cal_oauth_done')
    void qc.invalidateQueries({ queryKey: ['analytics', 'agendaEvents'] })
    void qc.invalidateQueries({ queryKey: ['calendar-settings'] })
    void qc.invalidateQueries({ queryKey: ['agenda-schedule'] })
  }, [qc])

  useEffect(() => {
    document.body.classList.toggle('light', lightMode)
  }, [lightMode])

  // Once clientId is known: read scoped theme preference, then init first-run flag
  useEffect(() => {
    if (!clientId) return
    try {
      const scoped = localStorage.getItem(`blu-theme:${clientId}`)
      if (scoped !== null) setLightMode(scoped === 'light')
    } catch {
      // localStorage may be unavailable; default theme applies
    }
    initFirstRun(clientId)
  }, [clientId]) // eslint-disable-line react-hooks/exhaustive-deps

  function toggleTheme() {
    setLightMode(prev => {
      const next = !prev
      try {
        if (clientId) localStorage.setItem(`blu-theme:${clientId}`, next ? 'light' : 'dark')
        else localStorage.setItem('blu-theme', next ? 'light' : 'dark')
      } catch {
        // localStorage may be unavailable; theme toggle is still reflected in state
      }
      return next
    })
  }

  const on = (s: Screen) => screen === s ? ' on' : ''
  const show = (s: Screen) => visited.has(s)

  const openSearch = useCallback(() => setSearchOpen(true), [])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setSearchOpen(s => !s)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])
  // Only pop the onboarding overlay if user has no ingested data yet
  const hasNoData = !!clientId && !localStorage.getItem(`blu_has_data:${clientId}`)

  return (
    <div className="shell">
      <Topbar onToggleTheme={toggleTheme} lightMode={lightMode} onOpenSearch={openSearch} />
      <Sidebar />
      <main className="main">
        <div className={`screen${on('home')}`} id="s-home">
          {show('home') && (
            <ErrorBoundary fallback={<ErrorFallback />}>
              <HomePage />
            </ErrorBoundary>
          )}
        </div>
        <div className={`screen${on('compras')}`} id="s-compras">
          {show('compras') && (
            <ErrorBoundary fallback={<ErrorFallback />}>
              <ComprasRoom />
            </ErrorBoundary>
          )}
        </div>
        <div className={`screen${on('financeiro')}`} id="s-financeiro">
          {show('financeiro') && (
            <ErrorBoundary fallback={<ErrorFallback />}>
              <FinanceiroRoom />
            </ErrorBoundary>
          )}
        </div>
        <div className={`screen${on('agenda')}`} id="s-agenda">
          {show('agenda') && (
            <ErrorBoundary fallback={<ErrorFallback />}>
              <AgendaRoom />
            </ErrorBoundary>
          )}
        </div>
        <div className={`screen${on('estrategia')}`} id="s-estrategia">
          {show('estrategia') && (
            <ErrorBoundary fallback={<ErrorFallback />}>
              <EstrategiaRoom />
            </ErrorBoundary>
          )}
        </div>
        <div className={`screen${on('clientes')}`} id="s-clientes">
          {show('clientes') && (
            <ErrorBoundary fallback={<ErrorFallback />}>
              <ClientesRoom />
            </ErrorBoundary>
          )}
        </div>
        <div className={`screen${on('atividade')}`} id="s-atividade">
          {show('atividade') && (
            <ErrorBoundary fallback={<ErrorFallback />}>
              <AtividadeScreen />
            </ErrorBoundary>
          )}
        </div>
        <div className={`screen${on('admin')}`} id="s-admin">
          {show('admin') && myRole === 'owner' && (
            <ErrorBoundary fallback={<ErrorFallback />}>
              <AdminScreen />
            </ErrorBoundary>
          )}
        </div>
        <div className={`screen${on('blu_ops')}`} id="s-blu_ops">
          {show('blu_ops') && tier === 'ADMIN' && (
            <ErrorBoundary fallback={<ErrorFallback />}>
              <AgentOpsRoom />
            </ErrorBoundary>
          )}
        </div>
        <div className={`screen${on('biblioteca')}`} id="s-biblioteca">
          {show('biblioteca') && (
            <ErrorBoundary fallback={<ErrorFallback />}>
              <BusinessMemoryPage />
            </ErrorBoundary>
          )}
        </div>
      </main>

      <EditorOverlay
        open={editorOpen}
        docName={'Proposta — Cliente Central'}
        onClose={() => setEditorOpen(false)}
      />
      <ToastContainer />
      <ChatPanel />
      {firstRun && hasNoData && <FirstRunOverlay onOpenConnections={() => setConnectionsOpen(true)} />}
      <ConnectionsModal open={connectionsOpen} onClose={() => setConnectionsOpen(false)} />
      <SpotlightSearch open={searchOpen} onClose={() => setSearchOpen(false)} />
    </div>
  )
}
