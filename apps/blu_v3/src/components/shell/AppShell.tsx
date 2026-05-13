import { useState, useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useAppStore } from '../../store/appStore'
import type { Screen } from '../../store/appStore'
import Topbar from './Topbar'
import Sidebar from './Sidebar'
import ToastContainer from '../shared/Toast'
import EditorOverlay from '../shared/EditorOverlay'
import ChatPanel from '../chat/ChatPanel'
import HomePage from '../../pages/app/HomePage'
import ComprasRoom from '../../pages/app/ComprasRoom'
import FinanceiroRoom from '../../pages/app/FinanceiroRoom'
import AgendaRoom from '../../pages/app/AgendaRoom'
import DocumentosRoom from '../../pages/app/DocumentosRoom'
import EstrategiaRoom from '../../pages/app/EstrategiaRoom'
import ClientesRoom from '../../pages/app/ClientesRoom'
import AtividadeScreen from '../../pages/app/AtividadeScreen'
import AdminScreen from '../../pages/app/AdminScreen'
import AgentesScreen from '../../pages/app/AgentesScreen'
import BibliotecaRoom from '../../pages/app/BibliotecaRoom'
import AgentOpsRoom from '../../pages/app/AgentOpsRoom'

export default function AppShell() {
  const screen = useAppStore(s => s.screen)
  const qc = useQueryClient()
  const [editorOpen, setEditorOpen] = useState(false)
  const [editorDoc, setEditorDoc] = useState('Proposta — Cliente Central')
  const [lightMode, setLightMode] = useState(() => {
    try { return localStorage.getItem('blu-theme') === 'light' } catch { return false }
  })

  // Track which screens have been visited so we only mount them on first activation.
  // Once mounted, screens stay mounted (preserving React Query cache and scroll state).
  const [visited, setVisited] = useState<Set<Screen>>(new Set(['home']))

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

  function toggleTheme() {
    setLightMode(prev => {
      const next = !prev
      try { localStorage.setItem('blu-theme', next ? 'light' : 'dark') } catch {}
      return next
    })
  }

  const openEditor = (docName: string) => {
    setEditorDoc(docName)
    setEditorOpen(true)
  }

  const on = (s: Screen) => screen === s ? ' on' : ''
  const show = (s: Screen) => visited.has(s)

  return (
    <div className="shell">
      <Topbar onToggleTheme={toggleTheme} lightMode={lightMode} />
      <Sidebar />
      <main className="main">
        <div className={`screen${on('home')}`} id="s-home">
          {show('home') && <HomePage />}
        </div>
        <div className={`screen${on('compras')}`} id="s-compras">
          {show('compras') && <ComprasRoom />}
        </div>
        <div className={`screen${on('financeiro')}`} id="s-financeiro">
          {show('financeiro') && <FinanceiroRoom />}
        </div>
        <div className={`screen${on('agenda')}`} id="s-agenda">
          {show('agenda') && <AgendaRoom />}
        </div>
        <div className={`screen${on('documentos')}`} id="s-documentos">
          {show('documentos') && <DocumentosRoom openEditor={openEditor} />}
        </div>
        <div className={`screen${on('estrategia')}`} id="s-estrategia">
          {show('estrategia') && <EstrategiaRoom />}
        </div>
        <div className={`screen${on('clientes')}`} id="s-clientes">
          {show('clientes') && <ClientesRoom />}
        </div>
        <div className={`screen${on('atividade')}`} id="s-atividade">
          {show('atividade') && <AtividadeScreen />}
        </div>
        <div className={`screen${on('agentes')}`} id="s-agentes">
          {show('agentes') && <AgentesScreen />}
        </div>
        <div className={`screen${on('admin')}`} id="s-admin">
          {show('admin') && <AdminScreen />}
        </div>
        <div className={`screen${on('biblioteca')}`} id="s-biblioteca">
          {show('biblioteca') && <BibliotecaRoom />}
        </div>
        <div className={`screen${on('blu_ops')}`} id="s-blu_ops">
          {show('blu_ops') && <AgentOpsRoom />}
        </div>
      </main>

      <EditorOverlay
        open={editorOpen}
        docName={editorDoc}
        onClose={() => setEditorOpen(false)}
      />
      <ToastContainer />
      <ChatPanel />
    </div>
  )
}
