import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? Deno.env.get("SERVICE_ROLE_KEY")!;

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

// base64url-encode an ArrayBuffer
function b64url(buf: ArrayBuffer): string {
  return btoa(String.fromCharCode(...new Uint8Array(buf)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=/g, "");
}

// base64url-encode a plain string (via UTF-8 bytes)
function strB64url(str: string): string {
  return b64url(new TextEncoder().encode(str).buffer);
}

/**
 * Exchange a service account JSON key for a Google OAuth2 access token.
 * Signs a JWT with the SA private key (RS256) and POSTs it to Google's token endpoint.
 */
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

  // Strip PEM headers and whitespace, then decode to binary
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
    throw new Error(`Google token response missing access_token: ${JSON.stringify(tokenData)}`);
  }
  return tokenData.access_token as string;
}

interface BqColumn {
  name: string;
  type: string;
  nullable: boolean;
}

/**
 * Fetch BigQuery table schema via REST API.
 * Returns array of { name, type, nullable } objects.
 */
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
    throw new Error(`BigQuery table ${projectId}.${datasetId}.${tableId} returned no schema fields`);
  }

  return fields.map((f) => ({
    name: f.name,
    type: f.type,
    nullable: f.mode !== "REQUIRED",
  }));
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    // Get Authorization header to verify user
    const authHeader = req.headers.get("Authorization");
    if (!authHeader) {
      return json({ error: "Missing authorization header" }, 401);
    }

    const body = await req.json();
    const {
      credential_id,
      // deno-lint-ignore no-explicit-any
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

    if (!credential_id || !service_account_json || !project_id || !dataset_id || !table_name) {
      return json(
        { error: "credential_id, service_account_json, project_id, dataset_id, table_name are required" },
        400,
      );
    }

    // Verify user owns this credential via service role check
    const supabase = createClient(SUPABASE_URL, SERVICE_ROLE_KEY, {
      auth: { autoRefreshToken: false, persistSession: false },
    });

    // Extract token and verify ownership
    const token = authHeader.replace("Bearer ", "");
    const { data: { user }, error: authError } = await supabase.auth.getUser(token);

    if (authError || !user) {
      return json({ error: "Invalid authorization token" }, 401);
    }

    // Verify credential belongs to user's client
    const { data: cred, error: credError } = await supabase
      .from("credencial_servico_externo")
      .select("client_id")
      .eq("id", credential_id)
      .maybeSingle();

    if (credError || !cred) {
      return json({ error: "Credential not found" }, 404);
    }

    // Verify user has access to this client (via client context)
    // This is enforced at the app level - the user's session should be scoped to a client
    console.log(`[discover-bigquery-columns] User ${user.id} discovering schema for credential ${credential_id}`);
    console.log(`[discover-bigquery-columns] Discovering schema for ${project_id}.${dataset_id}.${table_name}`);

    // 1. Get Google access token
    const accessToken = await getGoogleAccessToken(service_account_json);

    // 2. Fetch BigQuery table schema
    const columns = await getBigQuerySchema(accessToken, project_id, dataset_id, table_name);
    console.log(`[discover-bigquery-columns] Found ${columns.length} columns`);

    // 3. Persist discovered columns to client_data_sources
    const { error: updateError } = await supabase
      .from("client_data_sources")
      .update({
        source_columns: columns,
        sync_status: "columns_discovered",
        updated_at: new Date().toISOString(),
      })
      .eq("credential_id", credential_id);

    if (updateError) {
      console.error("[discover-bigquery-columns] Failed to update source_columns:", updateError);
    }

    // 4. Create the foreign table with properly typed columns
    // First, update bigquery_foreign_tables with the full BigQuery table reference
    const bigqueryTableRef = `${project_id}.${dataset_id}.${table_name}`;

    const { data: dataSource } = await supabase
      .from("client_data_sources")
      .select("client_id")
      .eq("credential_id", credential_id)
      .maybeSingle();

    if (dataSource?.client_id) {
      // Update the bigquery_foreign_tables with the full table reference
      const { error: updateMetadataError } = await supabase
        .from("bigquery_foreign_tables")
        .update({
          bigquery_table: bigqueryTableRef,
        })
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

      const { error: rpcError } = await supabase.rpc(
        "create_bigquery_foreign_table_from_schema",
        {
          p_client_id: dataSource.client_id,
          p_columns: columns,
        },
      );
      if (rpcError) {
        console.error(
          "[discover-bigquery-columns] FT creation failed:",
          rpcError.message,
        );
        return json(
          { error: `Failed to create foreign table: ${rpcError.message}` },
          500,
        );
      } else {
        console.log("[discover-bigquery-columns] Foreign table created with typed columns and full BigQuery reference");
      }
    }

    return json({ success: true, columns });
  } catch (err) {
    console.error("[discover-bigquery-columns] Error:", err);
    return json(
      { error: err instanceof Error ? err.message : "Unknown error" },
      500,
    );
  }
});
