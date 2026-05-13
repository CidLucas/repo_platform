import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from '@blu/auth'
import LandingPage from './pages/LandingPage'
import OnboardingApp from './pages/onboarding/OnboardingApp'
import AppShell from './components/shell/AppShell'

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

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingRoute />} />
      <Route path="/onboarding/*" element={<OnboardingApp />} />
      <Route
        path="/app/*"
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      />
    </Routes>
  )
}
