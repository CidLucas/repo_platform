import React, {
  createContext,
  useState,
  useEffect,
  useRef,
  ReactNode,
} from "react";
import { User, Session, AuthError } from "@supabase/supabase-js";
import { supabase } from "../lib/supabase";
import { getMe } from "../services/analyticsService";

export interface AuthContextType {
  user: User | null;
  session: Session | null;
  isLoading: boolean;
  clientId: string | null; // Real client_id from clientes_vizu table
  tier: string | null; // Tier from clientes_vizu table (FREE, BASIC, SME, PREMIUM, ENTERPRISE, ADMIN)
  signInWithEmail: (
    email: string,
    password: string
  ) => Promise<{ error: AuthError | null }>;
  signInWithGoogle: () => Promise<{ error: AuthError | null }>;
  signInWithMicrosoft: () => Promise<{ error: AuthError | null }>;
  signInWithApple: () => Promise<{ error: AuthError | null }>;
  signUp: (
    email: string,
    password: string,
    metadata?: Record<string, unknown>
  ) => Promise<{ error: AuthError | null }>;
  signOut: () => Promise<void>;
}

// eslint-disable-next-line react-refresh/only-export-components -- Context exports are intentional
export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [clientId, setClientId] = useState<string | null>(null);
  const [tier, setTier] = useState<string | null>(null);
  const clientIdFetchedRef = useRef(false);

  const initializeClientId = async (accessToken: string) => {
    if (clientIdFetchedRef.current) {
      return;
    }

    clientIdFetchedRef.current = true;

    try {
      const meResponse = await Promise.race([
        getMe(accessToken),
        new Promise<never>((_, reject) => {
          setTimeout(() => reject(new Error('getMe timeout')), 5000);
        }),
      ]);

      setClientId(meResponse.client_id);
      localStorage.setItem('vizu_client_id', meResponse.client_id);
      console.log('Client ID initialized:', meResponse.client_id);

      // Fetch tier from clientes_vizu table (direct Supabase query, RLS-protected)
      try {
        const { data: clientData } = await supabase
          .from('clientes_vizu')
          .select('tier')
          .eq('client_id', meResponse.client_id)
          .single();
        const resolvedTier = clientData?.tier || 'FREE';
        setTier(resolvedTier);
        localStorage.setItem('vizu_client_tier', resolvedTier);
        console.log('Tier initialized:', resolvedTier);
      } catch (tierError) {
        console.warn('Failed to fetch tier, defaulting to cached or FREE:', tierError);
        const storedTier = localStorage.getItem('vizu_client_tier');
        setTier(storedTier || 'FREE');
      }
    } catch (error) {
      console.error('Failed to initialize client_id:', error);
      clientIdFetchedRef.current = false;
      const storedClientId = localStorage.getItem('vizu_client_id');
      if (storedClientId) {
        setClientId(storedClientId);
        clientIdFetchedRef.current = true;
      }
      const storedTier = localStorage.getItem('vizu_client_tier');
      if (storedTier) {
        setTier(storedTier);
      }
    }
  };

  useEffect(() => {
    // Check if we're on an OAuth callback
    // PKCE flow: code in query params (?code=...)
    // Implicit flow: access_token in hash (#access_token=...)
    const isOAuthCallback =
      window.location.hash.includes('access_token') ||
      window.location.search.includes('code=');

    // Verifica sessão atual
    const initSession = async () => {
      // If this is an OAuth callback on the login page, let LoginPage handle it
      // The LoginPage will call exchangeCodeForSession explicitly
      if (isOAuthCallback && window.location.pathname === '/login') {
        console.log('🔐 OAuth callback detected on login page, letting LoginPage handle it...');
        // Don't set isLoading to false here - wait for onAuthStateChange
        return;
      }

      const {
        data: { session },
      } = await supabase.auth.getSession();
      setSession(session);
      setUser(session?.user ?? null);

      // Never block app routing on client_id fetch
      setIsLoading(false);

      // Initialize client_id in background (non-blocking)
      if (session?.access_token && !clientIdFetchedRef.current) {
        void initializeClientId(session.access_token);
      }
    };

    initSession();

    // Escuta mudanças de autenticação
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (_event, session) => {
      console.log('🔐 Auth state changed:', _event, session ? 'has session' : 'no session');

      // Clear OAuth params from URL after callback is processed
      if (_event === 'SIGNED_IN') {
        const hasOAuthParams = window.location.hash.includes('access_token') ||
          window.location.search.includes('code=');
        if (hasOAuthParams) {
          window.history.replaceState(null, '', window.location.pathname);
        }
      }

      setSession(session);
      setUser(session?.user ?? null);

      // Unblock protected routes immediately after auth state is known
      setIsLoading(false);

      // Initialize client_id in background (non-blocking)
      if (session?.access_token && _event !== 'SIGNED_OUT') {
        if (!clientIdFetchedRef.current) {
          void initializeClientId(session.access_token);
        }
      }

      // Clear clientId on sign out
      if (_event === 'SIGNED_OUT') {
        clientIdFetchedRef.current = false;
        setClientId(null);
        setTier(null);
        localStorage.removeItem('vizu_client_id');
        localStorage.removeItem('vizu_client_tier');
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const signInWithEmail = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    return { error };
  };

  const signInWithGoogle = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/login`,
      },
    });
    return { error };
  };

  const signInWithMicrosoft = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "azure",
      options: {
        redirectTo: `${window.location.origin}/login`,
        scopes: "email",
      },
    });
    return { error };
  };

  const signInWithApple = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "apple",
      options: {
        redirectTo: `${window.location.origin}/login`,
      },
    });
    return { error };
  };

  const signUp = async (
    email: string,
    password: string,
    metadata?: Record<string, unknown>
  ) => {
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: metadata,
      },
    });
    return { error };
  };

  const signOut = async () => {
    await supabase.auth.signOut();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        isLoading,
        clientId,
        tier,
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
  );
};
