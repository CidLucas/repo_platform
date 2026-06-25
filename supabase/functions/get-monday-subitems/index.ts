// Edge Function: get-monday-subitems
//
// Fetches subitems of a specific Monday.com item (lazy load for Gantt 4th level).
// Called when the user clicks to expand a task in MonthlyGantt.tsx.
//
// Auth: requires a valid Supabase user JWT.
// Body: { "item_id": string } — Monday item ID (numeric string)
// Response: { subitems: AgendaExternalEvent[], complexity?: number }

import {
  requireAuth,
  resolveClientId,
  createServiceClient,
  AuthError,
} from "../_shared/blu_auth.ts";
import { corsHeaders, json } from "../_shared/cors.ts";
import { fernetDecrypt } from "../_shared/fernet.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;
const CREDENTIALS_ENCRYPTION_KEY = Deno.env.get("CREDENTIALS_ENCRYPTION_KEY")!;

// ─── Column value extractors (same logic as get-agenda-events) ────────────────

type ColValue = { id: string; type: string; text: string; value: string };

function extractStartDate(cols: ColValue[]): string | null {
  const col = cols.find(c => c.type === "date" || c.type === "timeline");
  if (!col?.value) return null;
  try {
    const p = JSON.parse(col.value);
    return p.date ?? p.from ?? null;
  } catch { return null; }
}

function extractDueDate(cols: ColValue[]): string | null {
  const col = cols.find(c => c.type === "timeline");
  if (!col?.value) return null;
  try {
    const p = JSON.parse(col.value);
    return p.to ?? null;
  } catch { return null; }
}

function extractStatus(cols: ColValue[]): string {
  return cols.find(c => c.type === "color")?.text ?? "";
}

function extractOwner(cols: ColValue[]): string | null {
  const col = cols.find(c => c.type === "multiple-person" || c.type === "person");
  if (!col?.value) return null;
  try {
    const p = JSON.parse(col.value);
    const persons = p.personsAndTeams ?? [];
    return persons.map((x: { name?: string }) => x.name).filter(Boolean).join(", ") || null;
  } catch { return null; }
}

// ─── Monday GraphQL query ─────────────────────────────────────────────────────

const SUBITEMS_QUERY = (itemId: string) => `{
  items(ids: [${itemId}]) {
    subitems {
      id
      name
      column_values {
        id
        type
        text
        value
      }
    }
  }
  complexity { query after }
}`;

// ─── Handler ──────────────────────────────────────────────────────────────────

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });

  try {
    const sb = createServiceClient(SUPABASE_URL, SERVICE_ROLE_KEY);
    const ctx = await requireAuth(req, SUPABASE_URL, SUPABASE_ANON_KEY);
    const client_id = await resolveClientId(ctx, SUPABASE_URL, SUPABASE_ANON_KEY);
    if (!client_id) return json({ error: "client_id not found" }, 403);

    const body = await req.json().catch(() => ({}));
    const { item_id } = body as { item_id?: string };

    if (!item_id || !/^\d+$/.test(item_id)) {
      return json({ error: "item_id must be a numeric string" }, 400);
    }

    // Fetch Monday token for this client
    const { data: tokenRow, error: tokenErr } = await sb
      .from("integration_tokens")
      .select("access_token_encrypted")
      .eq("client_id", client_id)
      .eq("provider", "monday")
      .maybeSingle();

    if (tokenErr) return json({ error: tokenErr.message }, 500);

    if (!tokenRow?.access_token_encrypted) {
      return json({ subitems: [], reason: "monday_token_missing" }, 200);
    }

    const mondayToken = await fernetDecrypt(CREDENTIALS_ENCRYPTION_KEY, tokenRow.access_token_encrypted);

    // Query Monday API
    const mondayResp = await fetch("https://api.monday.com/v2", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${mondayToken}`,
        "Content-Type": "application/json",
        "API-Version": "2024-01",
      },
      body: JSON.stringify({ query: SUBITEMS_QUERY(item_id) }),
    });

    const mData = await mondayResp.json();

    if (mData.errors?.length) {
      return json({ subitems: [], error: mData.errors[0]?.message }, 200);
    }

    const rawSubitems: Array<{ id: string; name: string; column_values: ColValue[] }> =
      mData.data?.items?.[0]?.subitems ?? [];

    const today = new Date().toISOString().split("T")[0];

    const subitems = rawSubitems.map(sub => ({
      id: `monday_subitem_${sub.id}`,
      title: sub.name || `Subitem ${sub.id}`,
      start_date: extractStartDate(sub.column_values) ?? today,
      due_date: extractDueDate(sub.column_values),
      domain: "agenda",
      source: "monday",
      type: "subitem",
      parent_id: `monday_item_${item_id}`,
      url: null,
      status: extractStatus(sub.column_values),
      location: null,
      owner: extractOwner(sub.column_values),
      progress_pct: null,
      group_title: null,
      description: null,
      notes: null,
    }));

    return json({
      subitems,
      complexity: mData.data?.complexity ?? null,
    });
  } catch (e) {
    if (e instanceof AuthError) return json({ error: e.message }, 401);
    console.error("get-monday-subitems error:", e);
    return json({ error: String(e) }, 500);
  }
});
