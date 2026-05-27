/**
 * supabase/functions/_shared/bigquery_auth.ts
 *
 * Shared BigQuery helpers used by preview-bigquery-columns,
 * discover-bigquery-columns, and etl-bigquery-ingest.
 *
 * Responsibilities:
 *   1. getGoogleAccessToken(serviceAccountJson) — RS256 JWT → OAuth2 access_token.
 *   2. getBigQuerySchema(token, project, dataset, table) — tables.get column list.
 *   3. queryBigQueryPaginated(token, project, sql, onPage) — jobs.query + getQueryResults
 *      with pageToken pagination. Streams rows page-by-page so callers don't buffer
 *      the entire dataset in memory.
 *
 * Token cache policy:
 *   None. Each invocation mints a fresh JWT. Edge functions are short-lived and
 *   one extra token exchange per request is cheap compared to the risk of leaking
 *   tokens across tenants in a warm runtime instance.
 *
 * Scope policy:
 *   bigquery.readonly is sufficient for tables.get, jobs.query, and getQueryResults
 *   against existing tables. Ingest does NOT need bigquery (full) scope — we never
 *   write back to BigQuery.
 */

export interface BqColumn {
  name: string;
  type: string;
  nullable: boolean;
}

// ── base64url helpers ────────────────────────────────────────────────────────

function b64url(buf: ArrayBuffer): string {
  return btoa(String.fromCharCode(...new Uint8Array(buf)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=/g, "");
}

function strB64url(str: string): string {
  return b64url(new TextEncoder().encode(str).buffer);
}

// ── OAuth: service account JWT → access_token ────────────────────────────────

export async function getGoogleAccessToken(
  serviceAccountJson: Record<string, string>,
  scope: string = "https://www.googleapis.com/auth/bigquery.readonly",
): Promise<string> {
  const { client_email, private_key } = serviceAccountJson;
  if (!client_email || !private_key) {
    throw new Error(
      "service_account_json is missing client_email or private_key",
    );
  }

  const now = Math.floor(Date.now() / 1000);
  const headerB64 = strB64url(JSON.stringify({ alg: "RS256", typ: "JWT" }));
  const payloadB64 = strB64url(
    JSON.stringify({
      iss: client_email,
      scope,
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
    body:
      `grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer&assertion=${jwt}`,
  });

  if (!tokenResp.ok) {
    const errText = await tokenResp.text();
    throw new Error(
      `Google token exchange failed (${tokenResp.status}): ${errText}`,
    );
  }

  const tokenData = await tokenResp.json();
  if (!tokenData.access_token) {
    throw new Error("Google token response missing access_token");
  }
  return tokenData.access_token as string;
}

// ── BigQuery: tables.get → column list ───────────────────────────────────────

export async function getBigQuerySchema(
  accessToken: string,
  projectId: string,
  datasetId: string,
  tableId: string,
): Promise<BqColumn[]> {
  const url =
    `https://bigquery.googleapis.com/bigquery/v2/projects/${
      encodeURIComponent(projectId)
    }/datasets/${encodeURIComponent(datasetId)}/tables/${
      encodeURIComponent(tableId)
    }`;

  const resp = await fetch(url, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(
      `BigQuery tables.get API error (${resp.status}): ${errText}`,
    );
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

// ── BigQuery: jobs.query + getQueryResults with pagination ───────────────────

export interface BqPage {
  /** Row objects: { columnName: value, ... }. BigQuery returns all values as strings. */
  rows: Array<Record<string, string | null>>;
  /** Page number (0-indexed within this invocation). */
  pageIndex: number;
  /** Total rows reported by BigQuery for this query (only reliable after the first page). */
  totalRows: number;
}

/**
 * Optional cursor that identifies an in-flight BigQuery query.
 *
 * When the caller has a time budget (e.g. an Edge Function with a CPU limit),
 * it can persist this cursor between invocations and resume paginating from
 * where it left off — without re-submitting the query or losing position.
 */
export interface BqResumeCursor {
  /** BigQuery job id returned by jobs.query. */
  jobId: string;
  /** Job location (US, EU, etc.). May be undefined for legacy jobs. */
  location?: string;
  /** Page token to feed into the next getQueryResults call. */
  pageToken: string;
}

/**
 * Result of a (possibly partial) paginated query run.
 *
 * - `processed` always reflects the rows fed to `onPage` during THIS call.
 * - `resume` is set when pagination stopped before exhausting all pages
 *   (either because `onPage` returned `{ stop: true }` or because a fresh
 *   pageToken was returned by BigQuery but the caller asked to bail).
 *   Callers should persist `resume` and pass it back as `opts.resumeFrom`
 *   on the next invocation to continue from the same spot.
 * - `totalRows` is BigQuery's own row count for the underlying SELECT —
 *   useful for progress %.
 */
export interface BqRunResult {
  processed: number;
  totalRows: number;
  resume?: BqResumeCursor;
}

/**
 * Run a SELECT against BigQuery and stream pages to a callback.
 *
 * Pagination at 10_000 rows by default — caller may override with `opts.pageSize`.
 * Each page becomes one bulk INSERT into Postgres; 10k rows × ~30 columns keeps
 * the staging insert under ~5 MB which is well below pg_net / edge function limits.
 *
 * Resumable pagination:
 *   - Pass `opts.resumeFrom` to skip jobs.query and walk pageToken directly. This
 *     is how etl-bigquery-ingest continues a long sync across multiple edge
 *     function invocations without re-running the BQ query.
 *   - `onPage` may return `{ stop: true }` (or call `signalStop()`) to abort
 *     pagination after the current page. The returned BqRunResult will carry
 *     a `resume` cursor pointing at the next unread page.
 *
 * @param onPage  Async callback invoked for each page. If it throws, pagination
 *                stops and the error propagates. Return `{ stop: true }` to
 *                bail cleanly with a resume cursor.
 */
export async function queryBigQueryPaginated(
  accessToken: string,
  projectId: string,
  sql: string,
  onPage: (page: BqPage) => Promise<void | { stop?: boolean }>,
  opts: {
    pageSize?: number;
    timeoutMs?: number;
    resumeFrom?: BqResumeCursor;
  } = {},
): Promise<BqRunResult> {
  const pageSize = opts.pageSize ?? 10_000;
  const timeoutMs = opts.timeoutMs ?? 20_000; // stay under the 25s edge-function budget

  let pageIndex = 0;
  let processed = 0;
  let totalRows = 0;
  let bqJobId: string | undefined;
  let bqLocation: string | undefined;
  let fields: Array<{ name: string; type: string }> = [];
  let pageToken: string | undefined;

  // Helper: convert BigQuery's { f: [{v: ...}, ...] } row format → object.
  const toRowObjects = (
    rows: Array<{ f: Array<{ v: string | null }> }> | undefined,
  ): Array<Record<string, string | null>> => {
    if (!rows) return [];
    return rows.map((r) => {
      const obj: Record<string, string | null> = {};
      r.f.forEach((cell, i) => {
        obj[fields[i].name] = cell.v;
      });
      return obj;
    });
  };

  if (opts.resumeFrom) {
    // Resume path: skip jobs.query and pick up at the saved pageToken.
    bqJobId = opts.resumeFrom.jobId;
    bqLocation = opts.resumeFrom.location;
    pageToken = opts.resumeFrom.pageToken;

    // If no pageToken, the BQ job may still be running — poll it first.
    if (!pageToken) {
      const pollUrl = new URL(
        `https://bigquery.googleapis.com/bigquery/v2/projects/${encodeURIComponent(projectId)}/queries/${encodeURIComponent(bqJobId!)}`,
      );
      pollUrl.searchParams.set("maxResults", String(opts.pageSize ?? 10_000));
      pollUrl.searchParams.set("timeoutMs", String(opts.timeoutMs ?? 60_000));
      if (bqLocation) pollUrl.searchParams.set("location", bqLocation);

      const pollResp = await fetch(pollUrl.toString(), {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!pollResp.ok) {
        const errText = await pollResp.text();
        throw new Error(`BigQuery poll failed (${pollResp.status}): ${errText}`);
      }
      const pollData = await pollResp.json();
      fields = pollData.schema?.fields ?? [];
      totalRows = parseInt(pollData.totalRows ?? "0", 10);

      if (!pollData.jobComplete) {
        // Still running — persist cursor and yield.
        return {
          processed: 0,
          totalRows: 0,
          resume: { jobId: bqJobId!, location: bqLocation ?? "US", pageToken: undefined },
        };
      }
      // Job done — process first page from poll response.
      const firstPage = toRowObjects(pollData.rows);
      if (firstPage.length > 0) {
        const r = await onPage({ rows: firstPage, pageIndex, totalRows });
        processed += firstPage.length;
        pageIndex += 1;
        if (r && r.stop) {
          return {
            processed,
            totalRows,
            resume: pollData.pageToken
              ? { jobId: bqJobId!, location: bqLocation ?? "US", pageToken: pollData.pageToken }
              : undefined,
          };
        }
      }
      pageToken = pollData.pageToken as string | undefined;
    }

    // We need the schema (field names) — getQueryResults returns it on each page.
    // Field list is populated lazily from the first resumed page below.
  } else {
    // Fresh path: submit a new query.
    const startUrl =
      `https://bigquery.googleapis.com/bigquery/v2/projects/${
        encodeURIComponent(projectId)
      }/queries`;

    const startResp = await fetch(startUrl, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query: sql,
        useLegacySql: false,
        maxResults: pageSize,
        timeoutMs,
      }),
    });

    if (!startResp.ok) {
      const errText = await startResp.text();
      throw new Error(
        `BigQuery jobs.query failed (${startResp.status}): ${errText}`,
      );
    }

    const startData = await startResp.json();
    bqJobId = startData.jobReference?.jobId as string | undefined;
    bqLocation = startData.jobReference?.location as string | undefined;
    fields = startData.schema?.fields ?? [];

    if (!bqJobId) {
      throw new Error("BigQuery jobs.query response missing jobReference.jobId");
    }

    totalRows = parseInt(startData.totalRows ?? "0", 10);

    // First page may come inline with the job submission response.
    if (startData.jobComplete) {
      const firstPage = toRowObjects(startData.rows);
      if (firstPage.length > 0) {
        const r = await onPage({ rows: firstPage, pageIndex, totalRows });
        processed += firstPage.length;
        pageIndex += 1;
        if (r && r.stop) {
          return {
            processed,
            totalRows,
            resume: startData.pageToken
              ? { jobId: bqJobId, location: bqLocation, pageToken: startData.pageToken }
              : undefined,
          };
        }
      }
    } else {
      // Query still running after timeoutMs — return a resume cursor pointing at
      // the BQ job so the next invoke can poll results without re-submitting.
      return {
        processed: 0,
        totalRows: 0,
        resume: { jobId: bqJobId!, location: bqLocation ?? "US", pageToken: undefined },
      };
    }

    pageToken = startData.pageToken as string | undefined;
  }

  // Walk pageToken until exhausted or onPage signals stop.
  while (pageToken) {
    const nextUrl = new URL(
      `https://bigquery.googleapis.com/bigquery/v2/projects/${
        encodeURIComponent(projectId)
      }/queries/${encodeURIComponent(bqJobId!)}`,
    );
    nextUrl.searchParams.set("maxResults", String(pageSize));
    nextUrl.searchParams.set("pageToken", pageToken);
    if (bqLocation) nextUrl.searchParams.set("location", bqLocation);
    nextUrl.searchParams.set("timeoutMs", String(timeoutMs));

    const pageResp = await fetch(nextUrl.toString(), {
      headers: { Authorization: `Bearer ${accessToken}` },
    });

    if (!pageResp.ok) {
      const errText = await pageResp.text();
      throw new Error(
        `BigQuery getQueryResults failed (${pageResp.status}): ${errText}`,
      );
    }

    const pageData = await pageResp.json();

    // First time on the resume path: populate fields from the page schema.
    if (fields.length === 0) {
      fields = pageData.schema?.fields ?? [];
    }
    if (totalRows === 0 && pageData.totalRows) {
      totalRows = parseInt(pageData.totalRows, 10);
    }

    const rows = toRowObjects(pageData.rows);

    if (rows.length > 0) {
      const r = await onPage({ rows, pageIndex, totalRows });
      processed += rows.length;
      pageIndex += 1;
      if (r && r.stop) {
        return {
          processed,
          totalRows,
          resume: pageData.pageToken
            ? { jobId: bqJobId!, location: bqLocation, pageToken: pageData.pageToken }
            : undefined,
        };
      }
    }

    pageToken = pageData.pageToken as string | undefined;
  }

  return { processed, totalRows };
}
