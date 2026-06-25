/**
 * discover-bigquery-columns
 *
 * BigQuery schema discovery. Two modes:
 *
 *   1. Normal (default) — call with `credential_id` in the body. Validates
 *      ownership against `clientes_blu` via RLS, persists the column list to
 *      `client_data_sources.source_columns`, updates
 *      `bigquery_foreign_tables.bigquery_table`, and calls the
 *      `create_bigquery_foreign_table_from_schema` RPC to (re)create the
 *      `wrappers_fdw` foreign table.
 *
 *   2. Preview (`?preview=true`) — call without `credential_id`. Used by the
 *      onboarding wizard before `clientes_blu` exists yet. Pure BigQuery
 *      passthrough: hits the Google API and returns the column list. No DB
 *      reads, no DB writes.
 *
 * Mode 1 is the "real" flow; mode 2 is a thin pre-flight check.
 *
 * Auth: requires a valid Supabase user JWT (verify_jwt = false + internal
 * requireAuth for ES256 support — see _shared/blu_auth.ts).
 */

import {
  requireAuth,
  createUserClient,
  createServiceClient,
  AuthError,
} from "../_shared/blu_auth.ts";
import { corsHeaders, json } from "../_shared/cors.ts";
import {
  getGoogleAccessToken,
  getBigQuerySchema,
} from "../_shared/bigquery_auth.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY =
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? Deno.env.get("SERVICE_ROLE_KEY")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  const fnName = "[discover-bigquery-columns]";
  const preview = new URL(req.url).searchParams.get("preview") === "true";

  try {
    // ── 1. Auth: validate JWT, extract user context ──────────────────────────
    const ctx = await requireAuth(req, SUPABASE_URL, SUPABASE_ANON_KEY);

    // ── 2. Parse body ────────────────────────────────────────────────────────
    const body = await req.json();
    const {
      credential_id,
      service_account_json,
      project_id,
      dataset_id,
      table_name,
    } = body as {
      credential_id?: number;
      service_account_json: Record<string, string>;
      project_id: string;
      dataset_id: string;
      table_name: string;
    };

    const bqRef = `${project_id}.${dataset_id}.${table_name}`;
    if (preview) {
      if (!service_account_json || !project_id || !dataset_id || !table_name) {
        return json(
          {
            error:
              "service_account_json, project_id, dataset_id, table_name are required (preview mode)",
          },
          400,
        );
      }
      console.log(`${fnName} [preview] user ${ctx.userId} previewing ${bqRef}`);
    } else {
      if (
        !credential_id ||
        !service_account_json ||
        !project_id ||
        !dataset_id ||
        !table_name
      ) {
        return json(
          {
            error:
              "credential_id, service_account_json, project_id, dataset_id, table_name are required",
          },
          400,
        );
      }
      console.log(
        `${fnName} user ${ctx.userId} discovering schema for credential ${credential_id}`,
      );
      console.log(`${fnName} target: ${bqRef}`);
    }

    // ── 3. Google BigQuery schema discovery (external I/O) ──────────────────
    const accessToken = await getGoogleAccessToken(service_account_json);
    const columns = await getBigQuerySchema(accessToken, project_id, dataset_id, table_name);
    console.log(`${fnName} found ${columns.length} columns`);

    // ── 4. Preview mode: return early, no DB writes ──────────────────────────
    if (preview) {
      return json({ columns });
    }

    // ── 5. Ownership check via userClient (SECURITY INVOKER / RLS-scoped) ───
    const userClient = createUserClient(ctx.token, SUPABASE_URL, SUPABASE_ANON_KEY);

    const { data: cred, error: credError } = await userClient
      .from("credencial_servico_externo")
      .select("client_id")
      .eq("id", credential_id)
      .maybeSingle();

    if (credError) {
      console.error(`${fnName} credential lookup failed:`, credError);
      return json({ error: "Failed to verify credential" }, 500);
    }
    if (!cred) {
      return json({ error: "Credential not found or access denied" }, 404);
    }

    const { data: ownership } = await userClient
      .from("clientes_blu")
      .select("client_id")
      .eq("external_user_id", ctx.userId)
      .eq("client_id", cred.client_id)
      .maybeSingle();

    if (!ownership) {
      console.warn(
        `${fnName} user ${ctx.userId} attempted access to credential ${credential_id} owned by client ${cred.client_id}`,
      );
      return json({ error: "Unauthorized: credential belongs to another tenant" }, 403);
    }

    // ── 6. Persist results via service client (DDL + cross-schema writes) ───
    const serviceClient = createServiceClient(SUPABASE_URL, SERVICE_ROLE_KEY);

    const { error: updateError } = await serviceClient
      .from("client_data_sources")
      .update({
        source_columns: columns,
        sync_status: "columns_discovered",
        updated_at: new Date().toISOString(),
      })
      .eq("credential_id", credential_id);

    if (updateError) {
      console.error(`${fnName} failed to update source_columns:`, updateError);
    }

    const { data: dataSource } = await serviceClient
      .from("client_data_sources")
      .select("client_id")
      .eq("credential_id", credential_id)
      .maybeSingle();

    if (dataSource?.client_id) {
      const { error: updateMetadataError } = await serviceClient
        .from("bigquery_foreign_tables")
        .update({ bigquery_table: bqRef })
        .eq("client_id", dataSource.client_id);

      if (updateMetadataError) {
        console.error(
          `${fnName} failed to update FT metadata:`,
          updateMetadataError.message,
        );
        return json(
          { error: `Failed to update foreign table metadata: ${updateMetadataError.message}` },
          500,
        );
      }

      const { error: rpcError } = await serviceClient.rpc(
        "create_bigquery_foreign_table_from_schema",
        { p_client_id: dataSource.client_id, p_columns: columns },
      );

      if (rpcError) {
        console.error(`${fnName} FT creation failed:`, rpcError.message);
        return json({ error: `Failed to create foreign table: ${rpcError.message}` }, 500);
      }

      console.log(`${fnName} foreign table created with typed columns and full BigQuery reference`);
    }

    return json({ success: true, columns });
  } catch (err) {
    if (err instanceof AuthError) {
      return json({ error: err.message }, err.status);
    }
    console.error(`${fnName} error:`, err);
    return json(
      { error: err instanceof Error ? err.message : "Unknown error" },
      500,
    );
  }
});
