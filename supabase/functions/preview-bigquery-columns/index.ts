/**
 * preview-bigquery-columns
 *
 * Lightweight, read-only variant of discover-bigquery-columns.
 *
 * The onboarding wizard calls this BEFORE clientes_blu/credencial rows exist:
 * it needs the column list to render StepMapping. No DB reads, no DB writes —
 * pure BigQuery schema passthrough.
 *
 * Auth required (no anonymous access). The service_account_json is supplied
 * by the caller, so this endpoint cannot escalate access to another tenant.
 */

import { requireAuth, AuthError } from "../_shared/blu_auth.ts";
import { corsHeaders, json } from "../_shared/cors.ts";
import {
  getGoogleAccessToken,
  getBigQuerySchema,
} from "../_shared/bigquery_auth.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const ctx = await requireAuth(req, SUPABASE_URL, SUPABASE_ANON_KEY);

    const body = await req.json();
    const {
      service_account_json,
      project_id,
      dataset_id,
      table_name,
    } = body as {
      service_account_json: Record<string, string>;
      project_id: string;
      dataset_id: string;
      table_name: string;
    };

    if (!service_account_json || !project_id || !dataset_id || !table_name) {
      return json(
        {
          error:
            "service_account_json, project_id, dataset_id, table_name are required",
        },
        400,
      );
    }

    console.log(
      `[preview-bigquery-columns] User ${ctx.userId} previewing ${project_id}.${dataset_id}.${table_name}`,
    );

    const accessToken = await getGoogleAccessToken(service_account_json);
    const columns = await getBigQuerySchema(
      accessToken,
      project_id,
      dataset_id,
      table_name,
    );

    console.log(`[preview-bigquery-columns] Found ${columns.length} columns`);

    return json({ columns });
  } catch (err) {
    if (err instanceof AuthError) {
      return json({ error: err.message }, err.status);
    }
    const message = err instanceof Error ? err.message : String(err);
    console.error("[preview-bigquery-columns] Unhandled error:", message);
    return json({ error: message }, 500);
  }
});
