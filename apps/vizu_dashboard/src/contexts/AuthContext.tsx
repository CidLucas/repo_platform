import React, {
  createContext,
  useState,
  useEffect,
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

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [clientId, setClientId] = useState<string | null>(null);

  useEffect(() => {
    // Verifica sessão atual
    const getSession = async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      setSession(session);
      setUser(session?.user ?? null);

      // Initialize client_id on first login
      if (session?.access_token) {
        try {
          const meResponse = await getMe(session.access_token);
          setClientId(meResponse.client_id);
          // Store in localStorage for services that don't have React context access
          localStorage.setItem('vizu_client_id', meResponse.client_id);
          console.log('✅ Cliente Vizu ID initialized:', meResponse.client_id);
        } catch (error) {
          console.error('Failed to initialize client_id:', error);
          // Try to recover from localStorage
          const storedClientId = localStorage.getItem('vizu_client_id');
          if (storedClientId) {
            setClientId(storedClientId);
            console.log('✅ Cliente Vizu ID recovered from localStorage:', storedClientId);
          }
        }
      }

      setIsLoading(false);
    };

    getSession();

    // Escuta mudanças de autenticação
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (_event, session) => {
      setSession(session);
      setUser(session?.user ?? null);

      // Initialize client_id for any auth event that provides a valid session
      // This handles SIGNED_IN, TOKEN_REFRESHED, INITIAL_SESSION, and USER_UPDATED
      if (session?.access_token && _event !== 'SIGNED_OUT') {
        // Only fetch if we don't already have a clientId
        if (!clientId) {
          try {
            const meResponse = await getMe(session.access_token);
            setClientId(meResponse.client_id);
            // Store in localStorage for services that don't have React context access
            localStorage.setItem('vizu_client_id', meResponse.client_id);
            console.log(`✅ Cliente Vizu ID initialized on ${_event}:`, meResponse.client_id);
          } catch (error) {
            console.error('Failed to initialize client_id:', error);
            // Try to recover from localStorage
            const storedClientId = localStorage.getItem('vizu_client_id');
            if (storedClientId) {
              setClientId(storedClientId);
              console.log('✅ Cliente Vizu ID recovered from localStorage:', storedClientId);
            }
          }
        }
      }

      // Clear clientId on sign out
      if (_event === 'SIGNED_OUT') {
        setClientId(null);
        localStorage.removeItem('vizu_client_id');
      }

      setIsLoading(false);
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
        redirectTo: `${window.location.origin}/dashboard`,
      },
    });
    return { error };
  };

  const signInWithMicrosoft = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "azure",
      options: {
        redirectTo: `${window.location.origin}/dashboard`,
        scopes: "email",
      },
    });
    return { error };
  };

  const signInWithApple = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "apple",
      options: {
        redirectTo: `${window.location.origin}/dashboard`,
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
