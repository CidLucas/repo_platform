import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from '@/contexts/AuthContext'
import { initTelemetry } from '@/lib/telemetry'
import App from './App'
import '@/styles/globals.css'

initTelemetry()

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,       // 1 min
      gcTime: 300_000,         // 5 min
      retry: 1,
    },
    mutations: {
      onError: (error) => {
        console.error('[Query error]', error)
        // ErrorHuman toast wired in Phase 2 via ToastContext
      },
    },
  },
})

const root = document.getElementById('root')!
createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>
)
