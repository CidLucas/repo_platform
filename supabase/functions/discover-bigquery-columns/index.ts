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
      credential_id: number;
      service_account_json: Record<string, string>;
      project_id: string;
      dataset_id: string;
      table_name: string;
    };

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

    // ── 3. Ownership check via userClient (SECURITY INVOKER / RLS-scoped) ───
    const userClient = createUserClient(ctx.token, SUPABASE_URL, SUPABASE_ANON_KEY);

    const { data: cred, error: credError } = await userClient
      .from("credencial_servico_externo")
      .select("client_id")
      .eq("id", credential_id)
      .maybeSingle();

    if (credError) {
      console.error("[discover-bigquery-columns] Credential lookup failed:", credError);
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
        `[discover-bigquery-columns] User ${ctx.userId} attempted access to credential ${credential_id} owned by client ${cred.client_id}`,
      );
      return json({ error: "Unauthorized: credential belongs to another tenant" }, 403);
    }

    console.log(
      `[discover-bigquery-columns] User ${ctx.userId} discovering schema for credential ${credential_id} (client ${cred.client_id})`,
    );
    console.log(
      `[discover-bigquery-columns] Target: ${project_id}.${dataset_id}.${table_name}`,
    );

    // ── 4. Google BigQuery schema discovery (external I/O) ──────────────────
    const accessToken = await getGoogleAccessToken(service_account_json);
    const columns = await getBigQuerySchema(accessToken, project_id, dataset_id, table_name);
    console.log(`[discover-bigquery-columns] Found ${columns.length} columns`);

    // ── 5. Persist results via service client (DDL + cross-schema writes) ───
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
      console.error(
        "[discover-bigquery-columns] Failed to update source_columns:",
        updateError,
      );
    }

    const bigqueryTableRef = `${project_id}.${dataset_id}.${table_name}`;

    const { data: dataSource } = await serviceClient
      .from("client_data_sources")
      .select("client_id")
      .eq("credential_id", credential_id)
      .maybeSingle();

    if (dataSource?.client_id) {
      const { error: updateMetadataError } = await serviceClient
        .from("bigquery_foreign_tables")
        .update({ bigquery_table: bigqueryTableRef })
        .eq("client_id", dataSource.client_id);

      if (updateMetadataError) {
        console.error(
          "[discover-bigquery-columns] Failed to update FT metadata:",
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
        console.error(
          "[discover-bigquery-columns] FT creation failed:",
          rpcError.message,
        );
        return json({ error: `Failed to create foreign table: ${rpcError.message}` }, 500);
      }

      console.log(
        "[discover-bigquery-columns] Foreign table created with typed columns and full BigQuery reference",
      );
    }

    return json({ success: true, columns });
  } catch (err) {
    if (err instanceof AuthError) {
      return json({ error: err.message }, err.status);
    }
    console.error("[discover-bigquery-columns] Error:", err);
    return json(
      { error: err instanceof Error ? err.message : "Unknown error" },
      500,
    );
  }
});
