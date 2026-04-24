import { createClient } from "@supabase/supabase-js";

// Cast import.meta.env for type-check environments that don't ship vite/client types.
const env = (import.meta as unknown as { env?: Record<string, string | undefined> }).env ?? {};

const supabaseUrl = env.VITE_SUPABASE_URL;
const supabaseAnonKey = env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    "❌ Supabase credentials not configured. VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY must be set at build time.",
  );
}

// Same config as the dashboard so session is shared on the same origin:
// PKCE + detectSessionInUrl handles OAuth redirects on /onboarding/welcome.
export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true,
    flowType: "pkce",
  },
});
