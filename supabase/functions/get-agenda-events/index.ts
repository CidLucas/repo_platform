// Edge Function: get-agenda-events
//
// Fetches events from Google Calendar, Monday.com, and Notion in parallel for
// the authenticated client, returning a unified normalized array for the
// Gantt/Agenda view.
//
// Auth: requires a valid Supabase user JWT (verify_jwt = true in config.toml).
// Body (optional): { "rangeDays": number } — default 28 for Gantt window.
// Response: { events: AgendaEvent[], fetched_at: string, sources: { google, monday, notion } }

import Fernet from "npm:fernet@0.4.0";
import {
  requireAuth,
  createServiceClient,
  AuthError,
} from "../_shared/blu_auth.ts";
import { corsHeaders, json } from "../_shared/cors.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;
const CREDENTIALS_ENCRYPTION_KEY = Deno.env.get("CREDENTIALS_ENCRYPTION_KEY");

function decryptFernet(ciphertext: string): string {
  if (!CREDENTIALS_ENCRYPTION_KEY) {
    throw new Error("CREDENTIALS_ENCRYPTION_KEY not set");
  }
  const secret = new Fernet.Secret(CREDENTIALS_ENCRYPTION_KEY);
  const token = new Fernet.Token({ secret, token: ciphertext, ttl: 0 });
  return token.decode();
}

// ─── Types ────────────────────────────────────────────────────────────────────

/**
 * AgendaEvent — unified shape for all external sources.
 *
 * Hierarchy (Monday):
 *   type="project"  parent_id=null         → board
 *   type="phase"    parent_id=board_id     → group within board
 *   type="task"     parent_id=group_id     → item within group
 *
 * Google Calendar events always have type="event", parent_id=null.
 * Notion pages always have type="page", parent_id=null.
 */
export interface AgendaEvent {
  id: string;
  title: string;
  start_date: string;       // ISO date string (YYYY-MM-DD or full ISO)
  due_date: string | null;  // ISO date string or null
  domain: string;
  source: "google" | "monday" | "notion";
  type: "project" | "phase" | "task" | "milestone" | "event" | "page";
  parent_id: string | null; // links task→phase, phase→project
  url: string | null;
  status: string;
  location: string | null;
  owner: string | null;       // person responsible (display name)
  progress_pct: number | null; // 0–100 or null
  group_title: string | null;  // phase/group name (populated on tasks)
}

interface TokenRow {
  provider: string;
  access_token_encrypted: string | null;
  refresh_token_encrypted: string | null;
}

// ─── Domain inference ─────────────────────────────────────────────────────────

function inferDomain(text: string): string {
  const t = (text ?? "").toLowerCase();
  if (t.includes("compra") || t.includes("fornec") || t.includes("pedido") || t.includes("estoque")) return "Compras";
  if (t.includes("financ") || t.includes("pagar") || t.includes("receber") || t.includes("caixa") || t.includes("fatura")) return "Financeiro";
  if (t.includes("agenda") || t.includes("reunião") || t.includes("reuniao") || t.includes("meeting") || t.includes("call")) return "Agenda";
  if (t.includes("doc") || t.includes("contrato") || t.includes("nota") || t.includes("nf")) return "Documentos";
  if (t.includes("estrat") || t.includes("meta") || t.includes("okr") || t.includes("planej")) return "Estratégia";
  if (t.includes("client") || t.includes("venda") || t.includes("proposta") || t.includes("crm")) return "Clientes";
  return "Geral";
}

// ─── Google Calendar ──────────────────────────────────────────────────────────

async function fetchGoogleCalendarEvents(
  tokenRow: TokenRow | undefined,
  clientId: string,
  supabase: ReturnType<typeof createServiceClient>,
  rangeDays: number,
): Promise<AgendaEvent[]> {
  if (!tokenRow?.refresh_token_encrypted) return [];

  const refreshToken = decryptFernet(tokenRow.refresh_token_encrypted);

  const { data: oauthConfig, error: oauthErr } = await supabase.rpc("get_platform_google_oauth_config");
  if (oauthErr || !oauthConfig?.client_id || !oauthConfig?.client_secret) {
    throw new Error("oauth_not_configured");
  }

  const params = new URLSearchParams({
    client_id: oauthConfig.client_id,
    client_secret: oauthConfig.client_secret,
    refresh_token: refreshToken,
    grant_type: "refresh_token",
  });
  const tokenResp = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: params.toString(),
  });
  if (!tokenResp.ok) {
    const text = await tokenResp.text();
    throw new Error(`token_refresh_failed:${tokenResp.status}:${text}`);
  }
  const tokenData = await tokenResp.json();
  if (!tokenData.access_token) throw new Error("token_refresh_failed:no_access_token");
  const accessToken = tokenData.access_token as string;

  const now = new Date();
  const timeMin = now.toISOString();
  const timeMax = new Date(now.getTime() + rangeDays * 24 * 60 * 60 * 1000).toISOString();

  const url = new URL("https://www.googleapis.com/calendar/v3/calendars/primary/events");
  url.searchParams.set("timeMin", timeMin);
  url.searchParams.set("timeMax", timeMax);
  url.searchParams.set("singleEvents", "true");
  url.searchParams.set("orderBy", "startTime");
  url.searchParams.set("maxResults", "50");

  const eventsResp = await fetch(url.toString(), {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!eventsResp.ok) {
    const errText = await eventsResp.text();
    throw new Error(`calendar_api_error:${eventsResp.status}:${errText}`);
  }

  const eventsData = await eventsResp.json();
  return (eventsData.items || []).map((ev: Record<string, unknown>): AgendaEvent => {
    const start = ev.start as { dateTime?: string; date?: string } | undefined;
    const end = ev.end as { dateTime?: string; date?: string } | undefined;
    return {
      id: "gcal_" + String(ev.id ?? ""),
      title: String(ev.summary ?? "(sem título)"),
      start_date: String(start?.dateTime ?? start?.date ?? ""),
      due_date: (end?.dateTime ?? end?.date) ?? null,
      domain: inferDomain(String(ev.summary ?? "")),
      source: "google",
      type: "event",
      parent_id: null,
      url: (ev.htmlLink as string | undefined) ?? null,
      status: "scheduled",
      location: (ev.location as string | undefined) ?? null,
      owner: null,
      progress_pct: null,
      group_title: null,
    };
  });
}

// ─── Monday.com ───────────────────────────────────────────────────────────────
//
// Hierarchy returned:
//   Board  → type="project",  parent_id=null
//   Group  → type="phase",    parent_id="monday_board_{board_id}"
//   Item   → type="task",     parent_id="monday_group_{board_id}_{group_id}"

interface MondayColumnValue {
  id: string;
  type: string;
  text: string;
  value: string | null;
}

interface MondayItem {
  id: string;
  name: string;
  column_values: MondayColumnValue[];
  subitems?: MondayItem[]; // subitems are items themselves
}

interface MondayGroup {
  id: string;
  title: string;
  color: string;
  items_page: { items: MondayItem[] };
}

interface MondayBoard {
  id: string;
  name: string;
  description: string | null;
  groups: MondayGroup[];
}

function extractMondayDate(colValues: MondayColumnValue[], ...idHints: string[]): string | null {
  // 1. Try timeline columns first (type=timeline, value={"from":"YYYY-MM-DD","to":"YYYY-MM-DD"})
  //    Used when looking for "start" hints
  for (const hint of idHints) {
    const col = colValues.find((c) =>
      c.id.toLowerCase().includes(hint) && c.type === "timeline" && c.value
    );
    if (col?.value) {
      try {
        const parsed = JSON.parse(col.value) as { from?: string; to?: string };
        if (parsed.from) return parsed.from;
      } catch { /* ignore */ }
    }
  }
  // 2. Any timeline column — return "from" date
  const timelineCol = colValues.find((c) => c.type === "timeline" && c.value);
  if (timelineCol?.value) {
    try {
      const parsed = JSON.parse(timelineCol.value) as { from?: string; to?: string };
      if (parsed.from) return parsed.from;
    } catch { /* ignore */ }
  }
  // 3. Plain date columns (type=date, text=YYYY-MM-DD)
  for (const hint of idHints) {
    const col = colValues.find((c) =>
      c.id.toLowerCase().includes(hint) && c.type === "date" && c.text
    );
    if (col?.text) return col.text;
  }
  const dateCol = colValues.find((c) => c.type === "date" && c.text);
  return dateCol?.text ?? null;
}

function extractMondayDueDate(colValues: MondayColumnValue[]): string | null {
  // timeline "to" field is the due/end date
  const timelineCol = colValues.find((c) => c.type === "timeline" && c.value);
  if (timelineCol?.value) {
    try {
      const parsed = JSON.parse(timelineCol.value) as { from?: string; to?: string };
      if (parsed.to) return parsed.to;
    } catch { /* ignore */ }
  }
  // Fallback: date columns with "due"/"deadline"/"end" hints
  for (const hint of ["due", "deadline", "date4", "end", "timeline_end"]) {
    const col = colValues.find((c) =>
      c.id.toLowerCase().includes(hint) && c.type === "date" && c.text
    );
    if (col?.text) return col.text;
  }
  return null;
}

function extractMondayStatus(colValues: MondayColumnValue[]): string {
  // Prefer a column named "Status" (id contains "status" or "color")
  const col = colValues.find((c) =>
    (c.type === "color" || c.type === "status") &&
    (c.id.toLowerCase().includes("status") || c.id.toLowerCase().includes("color"))
  ) ?? colValues.find((c) => c.type === "color" || c.type === "status");
  return col?.text || "active";
}

function extractMondayOwner(colValues: MondayColumnValue[]): string | null {
  const col = colValues.find((c) =>
    c.type === "multiple-person" || c.type === "people" || c.type === "person" ||
    c.id.includes("person") || c.id.includes("owner") || c.id.includes("responsavel") || c.id.includes("responsible")
  );
  if (!col?.text) return null;
  return col.text.split(",")[0].trim() || null;
}

function extractMondayProgress(colValues: MondayColumnValue[]): number | null {
  // Numbers column often used for % complete
  const col = colValues.find((c) =>
    (c.type === "numbers" || c.type === "formula") &&
    (c.id.includes("progress") || c.id.includes("percent") || c.id.includes("complete"))
  );
  if (!col?.text) return null;
  const n = parseFloat(col.text);
  return isNaN(n) ? null : Math.max(0, Math.min(100, n));
}

function isoDate(d: string | null, fallback: string): string {
  if (!d) return fallback;
  // Monday returns YYYY-MM-DD already; ensure it's a valid date
  const parsed = new Date(d);
  return isNaN(parsed.getTime()) ? fallback : d;
}

async function fetchMondayHierarchy(
  tokenRow: TokenRow | undefined,
  rangeDays: number,
): Promise<AgendaEvent[]> {
  if (!tokenRow?.access_token_encrypted) return [];

  const apiToken = decryptFernet(tokenRow.access_token_encrypted);

  // Full hierarchy query: boards → groups → items with all column types
  // Complexity budget: Monday limit is 5_000_000.
  // Strategy: fetch boards list first (cheap), then groups+items per board (separate queries).
  const boardsQuery = `
    query {
      boards(limit: 20) {
        id
        name
        description
        board_kind
      }
    }
  `;

  const boardsResp = await fetch("https://api.monday.com/v2", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiToken}`,
      "Content-Type": "application/json",
      "API-Version": "2024-01",
    },
    body: JSON.stringify({ query: boardsQuery }),
  });
  if (!boardsResp.ok) {
    const errText = await boardsResp.text();
    throw new Error(`monday_api_error:${boardsResp.status}:${errText}`);
  }

  const boardsData = await boardsResp.json();
  if (boardsData.errors?.length) {
    throw new Error(`monday_gql_error:${JSON.stringify(boardsData.errors[0])}`);
  }

  interface BoardStub { id: string; name: string; description: string | null; board_kind?: string }
  const allBoards: BoardStub[] = boardsData?.data?.boards ?? [];

  const boardStubs: BoardStub[] = allBoards.filter((b: BoardStub) => {
    // Note: board_kind is always 'public' for subitems boards too — name-based filter is the
    // only reliable approach. We cover both PT-BR and EN naming conventions.
    if (b.name?.toLowerCase().startsWith('welcome to')) return false;
    if (b.name?.toLowerCase().includes('subelementos de ')) return false;  // PT-BR
    if (b.name?.toLowerCase().includes('subitems of ')) return false;      // EN
    return true;
  });

  // ── Fetch all board details in a single query (1 round-trip instead of N) ──
  //    IDs list is safe to inline: all are numeric strings from the boards query.
  async function fetchAllBoardDetails(boardList: BoardStub[]): Promise<MondayBoard[]> {
    if (boardList.length === 0) return [];
    const ids = boardList.map(b => b.id).join(', ');
    const q = `
      query {
        boards(ids: [${ids}]) {
          id
          name
          description
          groups {
            id
            title
            color
            items_page(limit: 50) {
              items {
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
          }
        }
      }
    `;
    const r = await fetch("https://api.monday.com/v2", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiToken}`,
        "Content-Type": "application/json",
        "API-Version": "2024-01",
      },
      body: JSON.stringify({ query: q }),
    });
    if (!r.ok) throw new Error(`monday_boards_detail_error:${r.status}`);
    const d = await r.json();
    if (d.errors?.length) throw new Error(`monday_boards_detail_gql:${JSON.stringify(d.errors[0])}`);
    return (d?.data?.boards ?? []) as MondayBoard[];
  }

  // Batch boards: up to 20 boards per query to avoid Monday complexity limits.
  // For most clients (1-5 boards) this is a single round-trip.
  const BATCH = 20;
  const boards: MondayBoard[] = [];
  for (let i = 0; i < boardStubs.length; i += BATCH) {
    const chunk = boardStubs.slice(i, i + BATCH);
    try {
      const batch = await fetchAllBoardDetails(chunk);
      boards.push(...batch);
    } catch (err) {
      // Batch failed (complexity?) — fall back to individual fetches
      console.error("[get-agenda-events] batch detail failed, falling back:", err);
      async function fetchBoardDetail(board: BoardStub): Promise<MondayBoard> {
        const q = `
          query {
            boards(ids: [${board.id}]) {
              id
              name
              description
              groups {
                id
                title
                color
                items_page(limit: 50) {
                  items {
                    id
                    name
                    column_values { id type text value }
                  }
                }
              }
            }
          }
        `;
        const r = await fetch("https://api.monday.com/v2", {
          method: "POST",
          headers: { Authorization: `Bearer ${apiToken}`, "Content-Type": "application/json", "API-Version": "2024-01" },
          body: JSON.stringify({ query: q }),
        });
        if (!r.ok) throw new Error(`monday_board_error:${board.id}:${r.status}`);
        const d = await r.json();
        if (d.errors?.length) throw new Error(`monday_board_gql:${board.id}:${JSON.stringify(d.errors[0])}`);
        return (d?.data?.boards?.[0] ?? { ...board, groups: [] }) as MondayBoard;
      }
      const results = await Promise.allSettled(chunk.map(fetchBoardDetail));
      for (const res of results) {
        if (res.status === "fulfilled") boards.push(res.value);
      }
    }
  }
  const today = new Date().toISOString().slice(0, 10);
  const maxDate = new Date(Date.now() + rangeDays * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);

  const events: AgendaEvent[] = [];

  for (const board of boards) {
    const boardId = `monday_board_${board.id}`;
    const groups = board.groups ?? [];

    // Compute board-level date span from all items
    let boardMinStart: string | null = null;
    let boardMaxDue: string | null = null;

    // Collect phases and tasks first to compute board span
    const phaseEvents: AgendaEvent[] = [];
    const taskEvents: AgendaEvent[] = [];

    for (const group of groups) {
      const groupId = `monday_group_${board.id}_${group.id}`;
      const items = group.items_page?.items ?? [];

      let groupMinStart: string | null = null;
      let groupMaxDue: string | null = null;

      for (const item of items) {
        const cols = item.column_values ?? [];
        const startDate = extractMondayDate(cols, "start", "date0", "timeline_start") ?? null;
        const dueDate   = extractMondayDueDate(cols);

        // Only count this item in span calculations if it has at least one real date
        const hasDate = startDate || dueDate;

        // Update group span (only real dates)
        if (hasDate) {
          const effectiveStart = startDate ?? dueDate!;
          if (!groupMinStart || effectiveStart < groupMinStart) groupMinStart = effectiveStart;
          if (dueDate && (!groupMaxDue || dueDate > groupMaxDue)) groupMaxDue = dueDate;
        }

        // Extract text columns: description and notes
        const descCol = cols.find((c) => c.type === "text" && (c.id.includes("descri") || c.id.includes("desc")));
        const notesCol = cols.find((c) => c.type === "text" && (c.id.includes("note") || c.id.includes("nota")));
        const phaseLabel = cols.find((c) => c.type === "dropdown")?.text ?? null;

        const itemId = `monday_item_${item.id}`;

        taskEvents.push({
          id: itemId,
          title: item.name,
          start_date: startDate ?? dueDate ?? today,
          due_date: dueDate,
          domain: inferDomain(`${item.name} ${board.name}`),
          source: "monday",
          type: "task",
          parent_id: groupId,
          url: `https://monday.com/boards/${board.id}/pulses/${item.id}`,
          status: extractMondayStatus(cols),
          location: phaseLabel,          // reuse location field for phase label (e.g. "Fase 2")
          owner: extractMondayOwner(cols),
          progress_pct: extractMondayProgress(cols),
          group_title: group.title,
          description: descCol?.text ?? null,
          notes: notesCol?.text ?? null,
        });

        // ── Subitems (4th level: task → subitem) ──
        for (const sub of item.subitems ?? []) {
          const subCols = sub.column_values ?? [];
          const subStart = extractMondayDate(subCols, "start", "date0", "timeline_start") ?? null;
          const subDue   = extractMondayDueDate(subCols);
          const subDescCol = subCols.find((c) => c.type === "text" && (c.id.includes("descri") || c.id.includes("desc")));
          const subNotesCol = subCols.find((c) => c.type === "text" && (c.id.includes("note") || c.id.includes("nota")));

          taskEvents.push({
            id: `monday_subitem_${sub.id}`,
            title: sub.name,
            start_date: subStart ?? subDue ?? startDate ?? dueDate ?? today,
            due_date: subDue ?? dueDate,
            domain: inferDomain(`${sub.name} ${item.name} ${board.name}`),
            source: "monday",
            type: "task",
            parent_id: itemId,  // parent = item, not group — correct nesting
            url: `https://monday.com/boards/${board.id}/pulses/${sub.id}`,
            status: extractMondayStatus(subCols),
            location: null,
            owner: extractMondayOwner(subCols),
            progress_pct: extractMondayProgress(subCols),
            group_title: group.title,
            description: subDescCol?.text ?? null,
            notes: subNotesCol?.text ?? null,
          });
        }
      }

      const phaseStart = groupMinStart ?? today;
      const phaseDue = groupMaxDue;

      // Update board span
      if (!boardMinStart || phaseStart < boardMinStart) boardMinStart = phaseStart;
      if (phaseDue) {
        if (!boardMaxDue || phaseDue > boardMaxDue) boardMaxDue = phaseDue;
      }

      phaseEvents.push({
        id: groupId,
        title: group.title,
        start_date: phaseStart,
        due_date: phaseDue,
        domain: inferDomain(`${group.title} ${board.name}`),
        source: "monday",
        type: "phase",
        parent_id: boardId,
        url: `https://monday.com/boards/${board.id}`,
        status: "active",
        location: null,
        owner: null,
        progress_pct: null,
        group_title: null,
      });
    }

    // Skip boards that are entirely outside range (no due date or max due before today)
    if (boardMaxDue && boardMaxDue < today) continue;

    // Project (board) row
    events.push({
      id: boardId,
      title: board.name,
      start_date: boardMinStart ?? today,
      due_date: boardMaxDue,
      domain: inferDomain(board.name + " " + (board.description ?? "")),
      source: "monday",
      type: "project",
      parent_id: null,
      url: `https://monday.com/boards/${board.id}`,
      status: "active",
      location: null,
      owner: null,
      progress_pct: null,
      group_title: null,
    });

    events.push(...phaseEvents);
    events.push(...taskEvents);
  }

  return events;
}

// ─── Notion ───────────────────────────────────────────────────────────────────

const NOTION_VERSION = "2022-06-28";

// Known date-like property names (case-insensitive match)
const DATE_PROP_NAMES = ["date", "data", "start", "início", "due", "prazo", "due date", "data de entrega", "deadline", "end", "fim"];
const START_PROP_NAMES = ["start", "início", "start date", "data início", "date", "data"];

function notionHeaders(token: string) {
  return {
    Authorization: `Bearer ${token}`,
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
  };
}

// Extract title from Notion page properties
function extractNotionTitle(props: Record<string, unknown> | undefined): string {
  if (!props) return "Sem título";
  for (const val of Object.values(props)) {
    const v = val as Record<string, unknown>;
    if (v?.type === "title") {
      const arr = (v.title as { plain_text: string }[] | undefined) ?? [];
      const text = arr.map(t => t.plain_text).join("").trim();
      if (text) return text;
    }
  }
  return "Sem título";
}

// Extract date string from a Notion date property value
function extractDateProp(v: Record<string, unknown>): { start: string; end: string | null } | null {
  if (v?.type !== "date") return null;
  const d = v.date as { start?: string; end?: string | null } | null;
  if (!d?.start) return null;
  return { start: d.start.slice(0, 10), end: d.end ? d.end.slice(0, 10) : null };
}

// Extract best start/due dates from page properties
function extractNotionDates(props: Record<string, unknown> | undefined): { start: string | null; due: string | null } {
  if (!props) return { start: null, due: null };

  let startDate: string | null = null;
  let dueDate: string | null = null;

  // Priority: look for known start-like prop names first
  for (const [key, val] of Object.entries(props)) {
    const k = key.toLowerCase();
    if (START_PROP_NAMES.includes(k)) {
      const d = extractDateProp(val as Record<string, unknown>);
      if (d) { startDate = d.start; if (d.end) dueDate = d.end; break; }
    }
  }

  // Then look for due-like prop names
  for (const [key, val] of Object.entries(props)) {
    const k = key.toLowerCase();
    if (DATE_PROP_NAMES.includes(k)) {
      const d = extractDateProp(val as Record<string, unknown>);
      if (d) {
        if (!startDate) startDate = d.start;
        if (!dueDate && d.end) dueDate = d.end;
        else if (!dueDate) dueDate = d.start;
        break;
      }
    }
  }

  // Fallback: any date property
  if (!startDate) {
    for (const val of Object.values(props)) {
      const d = extractDateProp(val as Record<string, unknown>);
      if (d) { startDate = d.start; if (d.end) dueDate = d.end; break; }
    }
  }

  return { start: startDate, due: dueDate };
}

// Extract owner from people property
function extractNotionOwner(props: Record<string, unknown> | undefined): string | null {
  if (!props) return null;
  for (const val of Object.values(props)) {
    const v = val as Record<string, unknown>;
    if (v?.type === "people") {
      const people = (v.people as { name?: string }[] | undefined) ?? [];
      if (people.length > 0) return people.map(p => p.name ?? "").filter(Boolean).join(", ");
    }
  }
  return null;
}

// Extract status from status/select property
function extractNotionStatus(props: Record<string, unknown> | undefined): string | null {
  if (!props) return null;
  for (const val of Object.values(props)) {
    const v = val as Record<string, unknown>;
    if (v?.type === "status") {
      return ((v.status as { name?: string } | null)?.name) ?? null;
    }
    if (v?.type === "select") {
      return ((v.select as { name?: string } | null)?.name) ?? null;
    }
  }
  return null;
}

// Extract number (progress) from number property named "progress", "progresso", "%"
function extractNotionProgress(props: Record<string, unknown> | undefined): number | null {
  if (!props) return null;
  for (const [key, val] of Object.entries(props)) {
    const k = key.toLowerCase();
    if (["progress", "progresso", "%", "completion"].includes(k)) {
      const v = val as Record<string, unknown>;
      if (v?.type === "number" && typeof v.number === "number") return Math.round(v.number);
    }
  }
  return null;
}

// Query a single database and return its rows as tasks
async function queryNotionDatabase(
  dbId: string,
  dbTitle: string,
  token: string,
  today: string,
  _rangeDays: number,
): Promise<AgendaEvent[]> {
  const resp = await fetch(`https://api.notion.com/v1/databases/${dbId}/query`, {
    method: "POST",
    headers: notionHeaders(token),
    body: JSON.stringify({
      page_size: 100,
      // no date filter — let the Gantt handle visibility; we filter archived only
    }),
  });
  if (!resp.ok) return []; // skip inaccessible databases silently

  const data = await resp.json();
  const rows = (data?.results ?? []) as Record<string, unknown>[];

  return rows
    .filter(row => !row.archived)
    .map((row): AgendaEvent => {
      const props = row.properties as Record<string, unknown> | undefined;
      const title = extractNotionTitle(props);
      const { start, due } = extractNotionDates(props);
      const owner = extractNotionOwner(props);
      const status = extractNotionStatus(props);
      const progress_pct = extractNotionProgress(props);

      // Fallback dates: if no dates, anchor at today with +14d window so it appears on Gantt
      const startDate = start ?? today;
      const dueDate = due ?? (start ? null : (() => {
        const d = new Date(today); d.setDate(d.getDate() + 14); return d.toISOString().slice(0, 10);
      })());

      return {
        id: "notion_" + String(row.id ?? ""),
        title,
        start_date: startDate,
        due_date: dueDate,
        domain: inferDomain(title),
        source: "notion",
        type: "task",
        parent_id: "notion_db_" + dbId,
        url: (row.url as string | undefined) ?? null,
        status: status ?? (row.archived ? "archived" : "active"),
        location: null,
        owner,
        progress_pct,
        group_title: dbTitle,
      };
    });
}

async function fetchNotionEvents(
  tokenRow: TokenRow | undefined,
  rangeDays: number,
): Promise<AgendaEvent[]> {
  if (!tokenRow?.access_token_encrypted) return [];

  const apiToken = decryptFernet(tokenRow.access_token_encrypted);
  const today = new Date().toISOString().slice(0, 10);
  const events: AgendaEvent[] = [];

  // ── 1. Fetch databases (projects) ─────────────────────────────────────────
  const dbResp = await fetch("https://api.notion.com/v1/search", {
    method: "POST",
    headers: notionHeaders(apiToken),
    body: JSON.stringify({
      filter: { property: "object", value: "database" },
      page_size: 20,
    }),
  });
  console.log("[notion] db search status:", dbResp.status);

  const databases: Array<{ id: string; title: string }> = [];

  if (!dbResp.ok) {
    const errText = await dbResp.text();
    console.log("[notion] db search error:", dbResp.status, errText.slice(0, 300));
  } else {
    const dbData = await dbResp.json();
    console.log("[notion] db search results:", JSON.stringify(dbData?.results?.length), "has_more:", dbData?.has_more);
    for (const db of (dbData?.results ?? []) as Record<string, unknown>[]) {
      if (db.archived) continue;
      const titleArr = (db.title as { plain_text: string }[] | undefined) ?? [];
      const dbTitle = titleArr.map(t => t.plain_text).join("").trim() || "Notion DB";
      const dbId = String(db.id ?? "");
      databases.push({ id: dbId, title: dbTitle });

      // Add database itself as a project-level root
      events.push({
        id: "notion_db_" + dbId,
        title: dbTitle,
        start_date: today,
        due_date: null,
        domain: inferDomain(dbTitle),
        source: "notion",
        type: "project",
        parent_id: null,
        url: (db.url as string | undefined) ?? null,
        status: "active",
        location: null,
        owner: null,
        progress_pct: null,
        group_title: null,
      });
    }
  }

  // ── 2. Query each database for tasks (rows) ────────────────────────────────
  const taskBatches = await Promise.allSettled(
    databases.map(db => queryNotionDatabase(db.id, db.title, apiToken, today, rangeDays))
  );
  for (const result of taskBatches) {
    if (result.status === "fulfilled") events.push(...result.value);
  }

  // ── 3. Fallback: loose pages not inside databases ──────────────────────────
  const pageResp = await fetch("https://api.notion.com/v1/search", {
    method: "POST",
    headers: notionHeaders(apiToken),
    body: JSON.stringify({
      filter: { property: "object", value: "page" },
      page_size: 30,
      sort: { direction: "descending", timestamp: "last_edited_time" },
    }),
  });

  if (pageResp.ok) {
    const pageData = await pageResp.json();
    for (const page of (pageData?.results ?? []) as Record<string, unknown>[]) {
      if (page.archived) continue;
      // Skip pages that are rows inside a database we already fetched
      const parentType = (page.parent as Record<string, unknown> | undefined)?.type;
      if (parentType === "database_id") continue;

      const props = page.properties as Record<string, unknown> | undefined;
      const title = extractNotionTitle(props);
      const { start, due } = extractNotionDates(props);
      const owner = extractNotionOwner(props);
      const status = extractNotionStatus(props);

      const startDate = start ?? today;
      const dueDate = due ?? (start ? null : (() => {
        const d = new Date(today); d.setDate(d.getDate() + 14); return d.toISOString().slice(0, 10);
      })());

      events.push({
        id: "notion_" + String(page.id ?? ""),
        title,
        start_date: startDate,
        due_date: dueDate,
        domain: inferDomain(title),
        source: "notion",
        type: "page",
        parent_id: null,
        url: (page.url as string | undefined) ?? null,
        status: status ?? "active",
        location: null,
        owner,
        progress_pct: null,
        group_title: null,
      });
    }
  }

  return events;
}

// ─── Handler ──────────────────────────────────────────────────────────────────

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  const startedAt = Date.now();
  let clientIdLog: string | null = null;

  try {
    // ── 1. Auth ──────────────────────────────────────────────────────────────
    const ctx = await requireAuth(req, SUPABASE_URL, SUPABASE_ANON_KEY);
    const userId = ctx.userId;

    // ── 2. Body ──────────────────────────────────────────────────────────────
    let body: { rangeDays?: number } = {};
    if (req.method === "POST") {
      try {
        body = await req.json();
      } catch {
        // empty body is fine
      }
    }
    const rangeDays = Math.max(1, Math.min(90, Number(body.rangeDays ?? 84)));

    const supabase = createServiceClient(SUPABASE_URL, SERVICE_ROLE_KEY);

    // ── Resolve client_id ────────────────────────────────────────────────────
    const { data: clientRow, error: clientErr } = await supabase
      .from("clientes_blu")
      .select("client_id")
      .eq("external_user_id", userId)
      .maybeSingle();

    if (clientErr) {
      console.error("[get-agenda-events] client lookup failed", clientErr);
      return json({ error: "Failed to resolve client" }, 500);
    }
    if (!clientRow) {
      return json({ error: "no_client" }, 404);
    }
    const clientId = String(clientRow.client_id);
    clientIdLog = clientId;

    // ── 3. Fetch all integration tokens in one query ──────────────────────────
    const { data: tokenRows, error: tokensErr } = await supabase
      .from("integration_tokens")
      .select("provider, access_token_encrypted, refresh_token_encrypted")
      .eq("client_id", clientId)
      .in("provider", ["google", "monday", "notion"]);

    if (tokensErr) {
      console.error("[get-agenda-events] tokens lookup failed", tokensErr);
      return json({ error: "Failed to read integration tokens" }, 500);
    }

    const tokenMap: Record<string, TokenRow> = {};
    for (const row of tokenRows ?? []) {
      tokenMap[row.provider] = row;
    }

    // ── 4. Parallel fetchers ─────────────────────────────────────────────────
    const [googleResult, mondayResult, notionResult] = await Promise.allSettled([
      fetchGoogleCalendarEvents(tokenMap["google"], clientId, supabase, rangeDays),
      fetchMondayHierarchy(tokenMap["monday"], rangeDays),
      fetchNotionEvents(tokenMap["notion"], rangeDays),
    ]);

    const googleEvents = googleResult.status === "fulfilled" ? googleResult.value : [];
    const mondayEvents = mondayResult.status === "fulfilled" ? mondayResult.value : [];
    const notionEvents = notionResult.status === "fulfilled" ? notionResult.value : [];

    const debugErrors: Record<string, string> = {};
    if (googleResult.status === "rejected") {
      const msg = googleResult.reason instanceof Error ? googleResult.reason.message : String(googleResult.reason);
      console.error("[get-agenda-events] google fetch failed", msg);
      debugErrors.google = msg;
    }
    if (mondayResult.status === "rejected") {
      const msg = mondayResult.reason instanceof Error ? mondayResult.reason.message : String(mondayResult.reason);
      console.error("[get-agenda-events] monday fetch failed", msg);
      debugErrors.monday = msg;
    }
    if (notionResult.status === "rejected") {
      const msg = notionResult.reason instanceof Error ? notionResult.reason.message : String(notionResult.reason);
      console.error("[get-agenda-events] notion fetch failed", msg);
      debugErrors.notion = msg;
    }

    // ── 5. Merge — projects first, then phases, then tasks, then calendar ────
    const mergedEvents: AgendaEvent[] = [
      ...mondayEvents.filter((e) => e.type === "project"),
      ...mondayEvents.filter((e) => e.type === "phase"),
      ...mondayEvents.filter((e) => e.type === "task"),
      ...notionEvents,
      ...googleEvents,
    ];

    console.log(
      JSON.stringify({
        fn: "get-agenda-events",
        client_id: clientId,
        status: "ok",
        events_count: mergedEvents.length,
        monday_projects: mondayEvents.filter((e) => e.type === "project").length,
        monday_phases: mondayEvents.filter((e) => e.type === "phase").length,
        monday_tasks: mondayEvents.filter((e) => e.type === "task").length,
        range_days: rangeDays,
        latency_ms: Date.now() - startedAt,
      }),
    );

    // ── 6. Return ────────────────────────────────────────────────────────────
    return json({
      events: mergedEvents,
      fetched_at: new Date().toISOString(),
      sources: {
        google: googleResult.status === "fulfilled" && googleResult.value.length > 0,
        monday: mondayResult.status === "fulfilled" && mondayResult.value.length > 0,
        notion: notionResult.status === "fulfilled" && notionResult.value.length > 0,
      },
      ...(Object.keys(debugErrors).length > 0 ? { _debug_errors: debugErrors } : {}),
    });
  } catch (e) {
    console.error(
      JSON.stringify({
        fn: "get-agenda-events",
        client_id: clientIdLog,
        status: "error",
        latency_ms: Date.now() - startedAt,
        error: e instanceof Error ? e.message : String(e),
      }),
    );
    if (e instanceof AuthError) {
      return json({ error: e.message }, e.status);
    }
    return json(
      {
        error: "internal_error",
        message: e instanceof Error ? e.message : String(e),
      },
      500,
    );
  }
});
