/**
 * supabase/functions/_shared/cors.ts
 *
 * Shared CORS headers and JSON response helper for Blu Edge Functions.
 *
 * Usage:
 *   import { corsHeaders, json } from "../_shared/cors.ts";
 *
 *   // OPTIONS preflight:
 *   return new Response("ok", { headers: corsHeaders });
 *
 *   // JSON responses:
 *   return json({ error: "not found" }, 404);
 *   return json(result, 200, { "X-Request-Id": requestId });
 */

export const corsHeaders: Record<string, string> = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

export function json(
  body: unknown,
  status = 200,
  customHeaders?: Record<string, string>,
): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      ...corsHeaders,
      "Content-Type": "application/json",
      ...customHeaders,
    },
  });
}
