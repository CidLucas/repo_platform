import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { RequireAuth } from '@/components/layout/RequireAuth'
import { LoginPage } from '@/pages/LoginPage'
import { HomePage } from '@/pages/HomePage'
import { ComprasRoom } from '@/pages/ComprasRoom'
import { FinanceiroRoom } from '@/pages/FinanceiroRoom'
import { AgendaRoom } from '@/pages/AgendaRoom'
import { DocumentosRoom } from '@/pages/DocumentosRoom'
import { EstrategiaRoom } from '@/pages/EstrategiaRoom'
import { ClientesRoom } from '@/pages/ClientesRoom'
import { AdminPage } from '@/pages/AdminPage'
import { OnboardingPage } from '@/pages/OnboardingPage'

export default function App() {
  return (
    <BrowserRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<RequireAuth />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/compras" element={<ComprasRoom />} />
          <Route path="/financeiro" element={<FinanceiroRoom />} />
          <Route path="/agenda" element={<AgendaRoom />} />
          <Route path="/documentos" element={<DocumentosRoom />} />
          <Route path="/estrategia" element={<EstrategiaRoom />} />
          <Route path="/clientes" element={<ClientesRoom />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/onboarding" element={<OnboardingPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
