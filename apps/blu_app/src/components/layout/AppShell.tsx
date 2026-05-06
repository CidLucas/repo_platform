import { useState, useEffect, type ReactNode } from 'react'
import { cn } from '@/utils/cn'
import { NavBar } from './NavBar'
import { AgentNav } from './AgentNav'
import { GlobalChatFab } from './GlobalChatFab'
import { NotificationProvider } from '@/contexts/NotificationContext'
import { TrustProvider } from '@/contexts/TrustContext'
import { ToastProvider, useToast } from '@/components/feedback/SuccessToast'
import { TrustMilestoneToast } from '@/components/trust/TrustMilestoneToast'
import { OnboardingBanner } from './OnboardingBanner'
import { useRealtime } from '@/hooks/useRealtime'
import { useQueryClient } from '@tanstack/react-query'

interface AppShellProps {
  children: ReactNode
}

/** Inner shell — mounts realtime subscription once auth is resolved */
function ShellContent({ children }: { children: ReactNode }) {
  const [navOpen, setNavOpen] = useState(false)
  useRealtime()

  return (
    <div className="flex h-dvh overflow-hidden bg-base">
      {/* Persistent sidebar (desktop) / slide-in (mobile) */}
      <AgentNav open={navOpen} onClose={() => setNavOpen(false)} />

      {/* Main content — offset by sidebar width on desktop */}
      <div className={cn('flex-1 flex flex-col min-w-0 overflow-hidden', 'lg:pl-12')}>
        <NavBar onMenuToggle={() => setNavOpen((v) => !v)} />
        <OnboardingBanner />

        {/* Scroll root for all pages — home scrolls here; agent pages scroll inside DeskLayout */}
        <main className="flex-1 min-h-0 overflow-y-auto">
          {children}
        </main>
      </div>

      {/* Global milestone toast watcher — renders nothing visually */}
      <TrustMilestoneToast />

      {/* Floating chat button — opens agent chat from any page */}
      <GlobalChatFab />

      {/* Global mutation error → ErrorHuman toast */}
      <QueryErrorWatcher />
    </div>
  )
}

/**
 * Subscribes to the mutation cache and shows a friendly error toast
 * whenever a mutation fails. Lives inside ToastProvider scope.
 */
function QueryErrorWatcher() {
  const queryClient = useQueryClient()
  const { showToast } = useToast()

  useEffect(() => {
    const unsubscribe = queryClient.getMutationCache().subscribe((event) => {
      if (
        event.type === 'updated' &&
        event.mutation?.state.status === 'error'
      ) {
        showToast('Algo deu errado. Tente novamente.', { variant: 'warning', duration: 4000 })
      }
    })
    return unsubscribe
  }, [queryClient, showToast])

  return null
}

/**
 * AppShell — root authenticated layout.
 * Provider order (inner to outer):
 *   ToastProvider → TrustProvider → NotificationProvider → ShellContent
 */
export function AppShell({ children }: AppShellProps) {
  return (
    <ToastProvider>
      <TrustProvider>
        <NotificationProvider>
          <ShellContent>{children}</ShellContent>
        </NotificationProvider>
      </TrustProvider>
    </ToastProvider>
  )
}
