import { createContext, useEffect, useRef, useState, type ReactNode } from 'react'
import type { AuthError, Session, User } from '@supabase/supabase-js'
import { supabase } from './client'
import { resolveClientId } from './auth'

/**
 * Lifecycle hook — invoked after a successful signUp.
 *
 * Consumers can subscribe to this hook to reset external state
 * (analytics, cache, telemetry) once a new account is created.
 * Today the implementation is a structured log; consumers that need
 * stronger guarantees (e.g. transactional telemetry flush) can wrap
 * their own logic on top.
 */
export const onSignUp = async (email: string, userId: string) => {
  console.info('[onSignUp] new user signed up', { email, userId })
}

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
      console.info('[Auth] initClientId resolved', {
        clientId,
        tier,
        timestamp: new Date().toISOString(),
      })
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
        console.info('[Auth] initSession — session found', {
          userId: session.user.id,
          email: session.user.email,
          provider: session.user.app_metadata?.provider ?? 'email',
          isOAuthCallback,
          timestamp: new Date().toISOString(),
        })
        onIdentifyUser?.(session.user.id, { email: session.user.email })
        void initClientId()
      } else {
        console.info('[Auth] initSession — anonymous', { isOAuthCallback, timestamp: new Date().toISOString() })
      }

      // Capture OAuth tokens immediately on redirect (before onAuthStateChange fires
      // or the provider_refresh_token is cleared from the session).
      if (isOAuthCallback && session?.provider_refresh_token) {
        if (sessionStorage.getItem('cal_oauth_pending') === '1') {
          sessionStorage.removeItem('cal_oauth_pending')
          void onCalendarToken?.({
            refreshToken: session.provider_refresh_token,
            accessToken: session.provider_token ?? '',
            email: session.user?.email ?? '',
          }).then(() => sessionStorage.setItem('cal_oauth_done', '1'))
        } else if (sessionStorage.getItem('drive_oauth_pending') === '1') {
          sessionStorage.removeItem('drive_oauth_pending')
          void onDriveToken?.({
            refreshToken: session.provider_refresh_token,
            accessToken: session.provider_token ?? '',
            email: session.user?.email ?? '',
          }).then(() => sessionStorage.setItem('drive_oauth_done', '1'))
        }
      }
    }

    void initSession()

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (_event === 'SIGNED_IN' || _event === 'TOKEN_REFRESHED' || _event === 'USER_UPDATED') {
        const hasOAuthParams =
          window.location.hash.includes('access_token') ||
          window.location.search.includes('code=')
        if (hasOAuthParams) {
          // AC5: Preserve ?mode= query param when cleaning OAuth hash/search.
          // The OAuth redirectTo includes ?mode=login but Supabase's callback
          // replaces the URL entirely. We clean the OAuth tokens from the URL
          // but keep any business-significant query params.
          const modeParam = new URLSearchParams(window.location.search).get('mode')
          const cleanPath = modeParam
            ? `${window.location.pathname}?mode=${modeParam}`
            : window.location.pathname
          window.history.replaceState(null, '', cleanPath)
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
        } else if (sessionStorage.getItem('cal_oauth_pending') === '1') {
          // Debug: log what we got to diagnose missing provider_refresh_token
          console.warn('[AuthContext] cal_oauth_pending set but provider_refresh_token missing', {
            event: _event,
            has_provider_token: !!session?.provider_token,
            has_refresh: !!session?.provider_refresh_token,
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
        console.info('[Auth] onAuthStateChange', {
          event: _event,
          userId: session.user.id,
          email: session.user.email,
          provider: session.user.app_metadata?.provider ?? 'email',
          timestamp: new Date().toISOString(),
        })
        onIdentifyUser?.(session.user.id, { email: session.user.email })
        void initClientId()
      }

      if (_event === 'SIGNED_OUT') {
        console.info('[Auth] onAuthStateChange SIGNED_OUT', { timestamp: new Date().toISOString() })
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
    if (!error) {
      console.info('[Auth] signInWithEmail succeeded', { email, timestamp: new Date().toISOString() })
    } else {
      console.warn('[Auth] signInWithEmail failed', { email, error: error.message, timestamp: new Date().toISOString() })
    }
    return { error }
  }

  const signInWithGoogle = async () => {
    console.info('[Auth] signInWithGoogle — redirecting', { redirectTo: `${window.location.origin}${loginRedirectPath}`, timestamp: new Date().toISOString() })
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${window.location.origin}${loginRedirectPath}` },
    })
    return { error }
  }

  const signInWithMicrosoft = async () => {
    console.info('[Auth] signInWithMicrosoft — redirecting', { redirectTo: `${window.location.origin}${loginRedirectPath}`, timestamp: new Date().toISOString() })
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'azure',
      options: { redirectTo: `${window.location.origin}${loginRedirectPath}`, scopes: 'email' },
    })
    return { error }
  }

  const signInWithApple = async () => {
    console.info('[Auth] signInWithApple — redirecting', { redirectTo: `${window.location.origin}${loginRedirectPath}`, timestamp: new Date().toISOString() })
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'apple',
      options: { redirectTo: `${window.location.origin}${loginRedirectPath}` },
    })
    return { error }
  }

  const signUp = async (email: string, password: string, metadata?: Record<string, unknown>) => {
    // AC#1: clear any existing session before signing up a new user.
    // Without this, the singleton `session`/`user`/`clientId`/`tier` state
    // from a previous sign-in leaks into the new signUp call, causing
    // onboarding to bootstrap with the previous tenant's data.
    // Use the wrapper signOut() so onResetUser fires and local state is
    // reset in lockstep with the SDK session (the SDK call alone races
    // against onAuthStateChange SIGNED_OUT).
    console.info('[Auth] signUp — clearing previous session', { email, timestamp: new Date().toISOString() })
    await signOut()

    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: { data: metadata },
    })
    if (!error) {
      console.info('[Auth] signUp succeeded', { email, timestamp: new Date().toISOString() })
    } else {
      console.warn('[Auth] signUp failed', { email, error: error.message, timestamp: new Date().toISOString() })
    }
    return { error }
  }

  const signOut = async () => {
    // AC2: Explicit state reset — don't wait for SIGNED_OUT listener.
    // The listener duplicates this for belt-and-suspenders, but the
    // explicit reset here is the source of truth for immediate consumption.
    clientIdFetchedRef.current = false
    setState({ session: null, user: null, clientId: null, tier: null, loading: false })
    onResetUser?.()
    await supabase.auth.signOut()
    console.info('[Auth] signOut — state reset explicitamente', { timestamp: new Date().toISOString() })
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
