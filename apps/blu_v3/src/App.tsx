import { Routes, Route, Navigate, Link } from 'react-router-dom'
import { useAuth } from '@blu/auth'
import LandingPage from './pages/LandingPage'
import OnboardingApp from './pages/onboarding/OnboardingApp'
import AppShell from './components/shell/AppShell'
import ErrorBoundary from './components/shared/ErrorBoundary'
import ErrorFallback from './components/shared/ErrorFallback'

function LandingRoute() {
  const { user, loading } = useAuth()
  if (loading) return null
  if (user) return <Navigate to="/app" replace />
  return <LandingPage />
}

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return null
  if (!user) return <Navigate to="/onboarding?mode=login" replace />
  return <>{children}</>
}

function ComingSoon({ title }: { title: string }) {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
      <div style={{ fontSize: 32, fontWeight: 800 }}>blu</div>
      <div style={{ fontSize: 18, fontWeight: 600 }}>{title}</div>
      <div style={{ color: 'var(--mu, #888)' }}>Página em construção</div>
      <Link to="/" style={{ marginTop: 8, color: '#7E5CC8', textDecoration: 'none', fontSize: 14 }}>← Voltar</Link>
    </div>
  )
}

export default function App() {
  return (
    <ErrorBoundary fallback={<ErrorFallback />}>
      <Routes>
        <Route path="/" element={<LandingRoute />} />
        <Route path="/privacidade" element={<ComingSoon title="Política de Privacidade" />} />
        <Route path="/termos" element={<ComingSoon title="Termos de Uso" />} />
        <Route path="/lgpd" element={<ComingSoon title="LGPD" />} />
        <Route
          path="/onboarding/*"
          element={
            <ErrorBoundary fallback={<ErrorFallback />}>
              <OnboardingApp />
            </ErrorBoundary>
          }
        />
        <Route
          path="/app/*"
          element={
            <RequireAuth>
              <ErrorBoundary fallback={<ErrorFallback />}>
                <AppShell />
              </ErrorBoundary>
            </RequireAuth>
          }
        />
      </Routes>
    </ErrorBoundary>
  )
}
