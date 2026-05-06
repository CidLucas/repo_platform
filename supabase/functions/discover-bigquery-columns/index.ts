import {
  requireAuth,
  createUserClient,
  createServiceClient,
  AuthError,
} from "../_shared/blu_auth.ts";
import { corsHeaders, json } from "../_shared/cors.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY =
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? Deno.env.get("SERVICE_ROLE_KEY")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;

// ── Google helpers ───────────────────────────────────────────────────────────

function b64url(buf: ArrayBuffer): string {
  return btoa(String.fromCharCode(...new Uint8Array(buf)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=/g, "");
}

function strB64url(str: string): string {
  return b64url(new TextEncoder().encode(str).buffer);
}

async function getGoogleAccessToken(
  serviceAccountJson: Record<string, string>,
): Promise<string> {
  const { client_email, private_key } = serviceAccountJson;
  if (!client_email || !private_key) {
    throw new Error("service_account_json is missing client_email or private_key");
  }

  const now = Math.floor(Date.now() / 1000);
  const headerB64 = strB64url(JSON.stringify({ alg: "RS256", typ: "JWT" }));
  const payloadB64 = strB64url(
    JSON.stringify({
      iss: client_email,
      scope: "https://www.googleapis.com/auth/bigquery.readonly",
      aud: "https://oauth2.googleapis.com/token",
      iat: now,
      exp: now + 3600,
    }),
  );
  const signingInput = `${headerB64}.${payloadB64}`;

  const pemBody = private_key
    .replace(/-----BEGIN PRIVATE KEY-----/g, "")
    .replace(/-----END PRIVATE KEY-----/g, "")
    .replace(/\s+/g, "");

  const keyBytes = Uint8Array.from(atob(pemBody), (c) => c.charCodeAt(0));
  const cryptoKey = await crypto.subtle.importKey(
    "pkcs8",
    keyBytes.buffer,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["sign"],
  );

  const signature = await crypto.subtle.sign(
    { name: "RSASSA-PKCS1-v1_5" },
    cryptoKey,
    new TextEncoder().encode(signingInput),
  );

  const jwt = `${signingInput}.${b64url(signature)}`;

  const tokenResp = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: `grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer&assertion=${jwt}`,
  });

  if (!tokenResp.ok) {
    const errText = await tokenResp.text();
    throw new Error(`Google token exchange failed (${tokenResp.status}): ${errText}`);
  }

  const tokenData = await tokenResp.json();
  if (!tokenData.access_token) {
    throw new Error(
      `Google token response missing access_token: ${JSON.stringify(tokenData)}`,
    );
  }
  return tokenData.access_token as string;
}

interface BqColumn {
  name: string;
  type: string;
  nullable: boolean;
}

async function getBigQuerySchema(
  accessToken: string,
  projectId: string,
  datasetId: string,
  tableId: string,
): Promise<BqColumn[]> {
  const url =
    `https://bigquery.googleapis.com/bigquery/v2/projects/${encodeURIComponent(projectId)}/datasets/${encodeURIComponent(datasetId)}/tables/${encodeURIComponent(tableId)}`;

  const resp = await fetch(url, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`BigQuery tables.get API error (${resp.status}): ${errText}`);
  }

  const tableData = await resp.json();
  const fields: Array<{ name: string; type: string; mode?: string }> =
    tableData.schema?.fields ?? [];

  if (fields.length === 0) {
    throw new Error(
      `BigQuery table ${projectId}.${datasetId}.${tableId} returned no schema fields`,
    );
  }

  return fields.map((f) => ({
    name: f.name,
    type: f.type,
    nullable: f.mode !== "REQUIRED",
  }));
}

// ── Handler ──────────────────────────────────────────────────────────────────

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
    // userClient runs under the caller's JWT. If RLS on credencial_servico_externo
    // restricts rows to the user's tenant, this lookup automatically enforces it.
    // We also cross-verify via clientes_blu to cover envs without full RLS yet.
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

    // Explicit cross-check: confirm the credential's client belongs to this user.
    // Works even in envs where RLS on credencial_servico_externo isn't fully set up.
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
    // Ownership has been verified above. Service role is required here because:
    //   a) client_data_sources and bigquery_foreign_tables may not have user-level
    //      RLS write policies that allow the anon role to update them.
    //   b) create_bigquery_foreign_table_from_schema is a DDL-level admin RPC.
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

    // Store canonical dot-notation reference as metadata.
    // The FDW constructs the full path (project.dataset.table) from server config;
    // the FT OPTIONS use only the bare table_name.
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
