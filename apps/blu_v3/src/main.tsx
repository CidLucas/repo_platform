import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from '@blu/auth'
import { captureCalendarToken, captureDriveToken } from './api/agenda'
import ErrorBoundary from './components/shared/ErrorBoundary'
import ErrorFallback from './components/shared/ErrorFallback'
import './styles/global.css'
import App from './App'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 2 * 60 * 1000, retry: 1 },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary fallback={<ErrorFallback />}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider loginRedirectPath="/onboarding" onCalendarToken={captureCalendarToken} onDriveToken={captureDriveToken}>
          <BrowserRouter future={{ v7_relativeSplatPath: true }}>
            <App />
          </BrowserRouter>
        </AuthProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  </React.StrictMode>,
)
