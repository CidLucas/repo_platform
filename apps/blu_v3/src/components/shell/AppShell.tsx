import { useState } from 'react'
import { useAppStore } from '../../store/appStore'
import Topbar from './Topbar'
import Sidebar from './Sidebar'
import ToastContainer from '../shared/Toast'
import EditorOverlay from '../shared/EditorOverlay'
import HomePage from '../../pages/app/HomePage'
import ComprasRoom from '../../pages/app/ComprasRoom'
import FinanceiroRoom from '../../pages/app/FinanceiroRoom'
import AgendaRoom from '../../pages/app/AgendaRoom'
import DocumentosRoom from '../../pages/app/DocumentosRoom'
import EstrategiaRoom from '../../pages/app/EstrategiaRoom'
import ClientesRoom from '../../pages/app/ClientesRoom'
import AtividadeScreen from '../../pages/app/AtividadeScreen'
import AdminScreen from '../../pages/app/AdminScreen'

export default function AppShell() {
  const screen = useAppStore(s => s.screen)
  const [editorOpen, setEditorOpen] = useState(false)
  const [editorDoc, setEditorDoc] = useState('Proposta — Cliente Central')

  const openEditor = (docName: string) => {
    setEditorDoc(docName)
    setEditorOpen(true)
  }

  return (
    <div className="shell">
      <Topbar />
      <Sidebar />
      <main className="main">
        <div className={`screen${screen === 'home' ? ' on' : ''}`} id="s-home">
          <HomePage />
        </div>
        <div className={`screen${screen === 'compras' ? ' on' : ''}`} id="s-compras">
          <ComprasRoom />
        </div>
        <div className={`screen${screen === 'financeiro' ? ' on' : ''}`} id="s-financeiro">
          <FinanceiroRoom />
        </div>
        <div className={`screen${screen === 'agenda' ? ' on' : ''}`} id="s-agenda">
          <AgendaRoom />
        </div>
        <div className={`screen${screen === 'documentos' ? ' on' : ''}`} id="s-documentos">
          <DocumentosRoom openEditor={openEditor} />
        </div>
        <div className={`screen${screen === 'estrategia' ? ' on' : ''}`} id="s-estrategia">
          <EstrategiaRoom />
        </div>
        <div className={`screen${screen === 'clientes' ? ' on' : ''}`} id="s-clientes">
          <ClientesRoom />
        </div>
        <div className={`screen${screen === 'atividade' ? ' on' : ''}`} id="s-atividade">
          <AtividadeScreen />
        </div>
        <div className={`screen${screen === 'admin' ? ' on' : ''}`} id="s-admin">
          <AdminScreen />
        </div>
      </main>
      <EditorOverlay
        open={editorOpen}
        docName={editorDoc}
        onClose={() => setEditorOpen(false)}
      />
      <ToastContainer />
    </div>
  )
}
