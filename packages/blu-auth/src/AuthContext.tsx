import { createContext, useEffect, useRef, useState, type ReactNode } from 'react'
import type { AuthError, Session, User } from '@supabase/supabase-js'
import { supabase } from './client'
import { resolveClientId } from './auth'

interface AuthState {
  session: Session | null
  user: User | null
  clientId: string | null
  tier: string | null
  loading: boolean
}

export interface AuthContextValue extends AuthState {
  signInWithEmail: (email: string, password: string) => Promise<{ error: AuthError | null }>
  signInWithGoogle: () => Promise<{ error: AuthError | null }>
  signInWithMicrosoft: () => Promise<{ error: AuthError | null }>
  signInWithApple: () => Promise<{ error: AuthError | null }>
  signUp: (email: string, password: string, metadata?: Record<string, unknown>) => Promise<{ error: AuthError | null }>
  signOut: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export interface AuthProviderProps {
  children: ReactNode
  /** Called on SIGNED_IN when provider_refresh_token is present (calendar OAuth) */
  onCalendarToken?: (params: {
    refreshToken: string
    accessToken: string
    email: string
  }) => Promise<void>
  /** Called on SIGNED_IN when provider_refresh_token is present (drive OAuth) */
  onDriveToken?: (params: {
    refreshToken: string
    accessToken: string
    email: string
  }) => Promise<void>
  /** Called after sign-in to identify the user in analytics/telemetry */
  onIdentifyUser?: (id: string, properties?: Record<string, unknown>) => void
  /** Called after sign-out to reset analytics/telemetry */
  onResetUser?: () => void
  /**
   * Path OAuth providers redirect to after authentication.
   * Must be a route in the app that has AuthProvider mounted.
   * Defaults to '/login'. blu_v3 should pass '/onboarding'.
   */
  loginRedirectPath?: string
}

export function AuthProvider({
  children,
  onCalendarToken,
  onDriveToken,
  onIdentifyUser,
  onResetUser,
  loginRedirectPath = '/login',
}: AuthProviderProps) {
  const [state, setState] = useState<AuthState>({
    session: null,
    user: null,
    clientId: null,
    tier: null,
    loading: true,
  })
  const clientIdFetchedRef = useRef(false)

  const initClientId = async () => {
    if (clientIdFetchedRef.current) return
    clientIdFetchedRef.current = true
    try {
      const clientId = await Promise.race([
        resolveClientId(),
        new Promise<never>((_, reject) =>
          setTimeout(() => reject(new Error('resolveClientId timeout')), 5000)
        ),
      ])

      let tier: string | null = null
      try {
        const { data } = await supabase
          .from('clientes_blu')
          .select('tier')
          .eq('client_id', clientId)
          .maybeSingle()
        tier = data?.tier ?? 'free'
      } catch {
        tier = 'free'
      }

      setState((s) => ({ ...s, clientId, tier }))
    } catch (err) {
      // "Client not found" is a terminal state for new users — don't retry.
      // Only reset the ref for transient errors (network, timeout) so they can retry.
      if (!(err instanceof Error && err.message.includes('Client not found'))) {
        clientIdFetchedRef.current = false
      }
      setState((s) => ({ ...s, clientId: null, tier: null }))
    }
  }

  useEffect(() => {
    const isOAuthCallback =
      window.location.hash.includes('access_token') ||
      window.location.search.includes('code=')

    const initSession = async () => {
      if (isOAuthCallback && window.location.pathname === '/login') return

      const { data: { session } } = await supabase.auth.getSession()
      setState((s) => ({ ...s, session, user: session?.user ?? null, loading: false }))

      if (session?.user) {
        onIdentifyUser?.(session.user.id, { email: session.user.email })
        void initClientId()
      }
    }

    void initSession()

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (_event === 'SIGNED_IN') {
        const hasOAuthParams =
          window.location.hash.includes('access_token') ||
          window.location.search.includes('code=')
        if (hasOAuthParams) {
          window.history.replaceState(null, '', window.location.pathname)
        }

        if (
          session?.provider_refresh_token &&
          sessionStorage.getItem('cal_oauth_pending') === '1'
        ) {
          sessionStorage.removeItem('cal_oauth_pending')
          void onCalendarToken?.({
            refreshToken: session.provider_refresh_token,
            accessToken: session.provider_token ?? '',
            email: session.user.email ?? '',
          }).then(() => {
            sessionStorage.setItem('cal_oauth_done', '1')
          })
        }

        if (
          session?.provider_refresh_token &&
          sessionStorage.getItem('drive_oauth_pending') === '1'
        ) {
          sessionStorage.removeItem('drive_oauth_pending')
          void onDriveToken?.({
            refreshToken: session.provider_refresh_token,
            accessToken: session.provider_token ?? '',
            email: session.user.email ?? '',
          }).then(() => {
            sessionStorage.setItem('drive_oauth_done', '1')
          })
        }
      }

      setState((s) => ({ ...s, session, user: session?.user ?? null, loading: false }))

      if (session?.user && _event !== 'SIGNED_OUT') {
        onIdentifyUser?.(session.user.id, { email: session.user.email })
        void initClientId()
      }

      if (_event === 'SIGNED_OUT') {
        clientIdFetchedRef.current = false
        setState({ session: null, user: null, clientId: null, tier: null, loading: false })
        onResetUser?.()
      }
    })

    return () => subscription.unsubscribe()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const signInWithEmail = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    return { error }
  }

  const signInWithGoogle = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${window.location.origin}${loginRedirectPath}` },
    })
    return { error }
  }

  const signInWithMicrosoft = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'azure',
      options: { redirectTo: `${window.location.origin}${loginRedirectPath}`, scopes: 'email' },
    })
    return { error }
  }

  const signInWithApple = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'apple',
      options: { redirectTo: `${window.location.origin}${loginRedirectPath}` },
    })
    return { error }
  }

  const signUp = async (email: string, password: string, metadata?: Record<string, unknown>) => {
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: { data: metadata },
    })
    return { error }
  }

  const signOut = async () => {
    await supabase.auth.signOut()
  }

  return (
    <AuthContext.Provider
      value={{
        ...state,
        signInWithEmail,
        signInWithGoogle,
        signInWithMicrosoft,
        signInWithApple,
        signUp,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}
