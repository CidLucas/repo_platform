import { supabase } from "./supabase";

/**
 * Resolve client_id for the currently authenticated user.
 *
 * Resolution order:
 *   1. app_metadata.client_id  (set by backend, most secure)
 *   2. user_metadata.client_id (social / onboarding fallback)
 *   3. clientes_blu lookup by external_user_id = auth.uid()
 *
 * Throws if no authenticated user or no client mapping found.
 */
export async function resolveClientId(
  providedClientId?: string,
): Promise<string> {
  if (providedClientId) return providedClientId;

  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();
  if (error || !user) {
    throw new Error("User not authenticated");
  }

  const fromApp = user.app_metadata?.client_id;
  if (fromApp) return fromApp;

  const fromUser = user.user_metadata?.client_id;
  if (fromUser) return fromUser;

  const { data, error: lookupError } = await supabase
    .from("clientes_blu")
    .select("client_id")
    .eq("external_user_id", user.id)
    .maybeSingle();

  if (lookupError) {
    throw new Error(
      `Failed to resolve client by external_user_id: ${lookupError.message}`,
    );
  }

  if (data?.client_id) return data.client_id;

  throw new Error(
    `Client not found for user: ${user.id} (no app_metadata, user_metadata, or external_user_id mapping)`,
  );
}

/**
 * Get the current Supabase access token.
 * Throws if no active session.
 */
export async function getAuthToken(): Promise<string> {
  const { data } = await supabase.auth.getSession();
  const token = data?.session?.access_token;
  if (!token) {
    throw new Error("Authentication required. Please log in.");
  }
  return token;
}

/**
 * Build standard Authorization + Content-Type headers.
 */
export async function buildAuthHeaders(): Promise<Record<string, string>> {
  const token = await getAuthToken();
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
}
