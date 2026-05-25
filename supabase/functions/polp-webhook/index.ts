/**
 * polp-webhook — Receive Polp real-time events and sync data into Supabase
 *
 * Register this URL in the Polp dashboard as the webhook endpoint.
 * Set POLP_WEBHOOK_SECRET env var and configure Polp to send
 * X-Polp-Signature (HMAC-SHA256 over raw body). Legacy X-Secret is kept as
 * backward-compatible fallback.
 *
 * Handled events:
 *   integrations.updated  → update polp_integrations status; trigger account sync
 *   accounts.updated      → refresh balance in polp_accounts
 *   accounts.synchronized → full account + transaction + bill sync
 *   transactions.created  → upsert single transaction
 *   transactions.updated  → upsert single transaction
 *   transactions.deleted  → mark deleted (soft delete via status)
 *   bills.created         → upsert bill
 *   bills.updated         → upsert bill
 */

import { createServiceClient } from "../_shared/blu_auth.ts";
import { json } from "../_shared/cors.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const POLP_API_CLIENT = Deno.env.get("POLP_API_CLIENT")!;
const POLP_API_SECRET = Deno.env.get("POLP_API_SECRET")!;
const POLP_WEBHOOK_SECRET = Deno.env.get("POLP_WEBHOOK_SECRET") ?? "";
const POLP_BASE_URL = "https://dev.polp.com.br/api/v1";

const polpHeaders = {
  "x-api-client": POLP_API_CLIENT,
  "x-api-secret": POLP_API_SECRET,
};

const textEncoder = new TextEncoder();

function hexToBytes(hex: string): Uint8Array {
  if (!hex || hex.length % 2 !== 0) return new Uint8Array();
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    const value = Number.parseInt(hex.slice(i, i + 2), 16);
    if (Number.isNaN(value)) return new Uint8Array();
    bytes[i / 2] = value;
  }
  return bytes;
}

function normalizeSignature(value: string | null): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (trimmed.startsWith("sha256=")) return trimmed.slice(7);
  return trimmed;
}

function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes).map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function fallbackEventIdFromBody(rawBody: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", textEncoder.encode(rawBody));
  return `body_sha256:${bytesToHex(new Uint8Array(digest))}`;
}

async function validateWebhookSignature(rawBody: string, req: Request): Promise<boolean> {
  if (!POLP_WEBHOOK_SECRET) return true; // dev fallback

  const signatureHeader = normalizeSignature(
    req.headers.get("x-polp-signature") ?? req.headers.get("x-pluggy-signature"),
  );
  if (signatureHeader) {
    const key = await crypto.subtle.importKey(
      "raw",
      textEncoder.encode(POLP_WEBHOOK_SECRET),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["verify"],
    );
    const signatureBytes = hexToBytes(signatureHeader);
    if (signatureBytes.length === 0) return false;
    return await crypto.subtle.verify("HMAC", key, signatureBytes, textEncoder.encode(rawBody));
  }

  // Backward compatibility with legacy X-Secret integration config
  const legacySecret = req.headers.get("x-secret") ?? "";
  return legacySecret === POLP_WEBHOOK_SECRET;
}

interface PolpWebhookPayload {
  event: string;
  entity: string;
  entity_id: number;
  event_id?: string | number;
  id?: string | number;
  changes?: Record<string, unknown>;
  data?: Record<string, unknown>;
}

async function polpGet<T>(path: string): Promise<T> {
  const res = await fetch(`${POLP_BASE_URL}${path}`, { headers: polpHeaders });
  if (!res.ok) throw new Error(`Polp ${path} → ${res.status}`);
  const body = await res.json();
  return body.data as T;
}

async function polpGetList<T>(path: string): Promise<T[]> {
  const res = await fetch(`${POLP_BASE_URL}${path}`, { headers: polpHeaders });
  if (!res.ok) throw new Error(`Polp ${path} → ${res.status}`);
  const body = await res.json();
  return (body.data ?? []) as T[];
}

async function syncAccounts(svc: ReturnType<typeof createServiceClient>, clientId: string, polpIntegrationId: number, integrationUuid: string) {
  const accounts = await polpGetList<Record<string, unknown>>(`/integrations/${polpIntegrationId}/accounts`);
  for (const acc of accounts) {
    await svc.from("polp_accounts").upsert({
      client_id: clientId,
      integration_id: integrationUuid,
      polp_account_id: acc.id,
      type: acc.type,
      subtype: acc.subtype ?? null,
      number: acc.number ?? null,
      name: acc.name ?? null,
      balance: acc.balance ?? 0,
      currency_code: acc.currency_code ?? "BRL",
      marketing_name: acc.marketing_name ?? null,
      owner: acc.owner ?? null,
      bank_data: acc.bank_data ?? null,
      credit_data: acc.credit_data ?? null,
      updated_at: new Date().toISOString(),
    }, { onConflict: "client_id,polp_account_id" });

    // Sync bills for CREDIT accounts
    if (acc.type === "CREDIT") {
      await syncBills(svc, clientId, acc.id as number);
    }
    // Sync recent transactions (first page)
    await syncTransactions(svc, clientId, acc.id as number);
  }
}

async function syncTransactions(svc: ReturnType<typeof createServiceClient>, clientId: string, polpAccountId: number) {
  const transactions = await polpGetList<Record<string, unknown>>(`/accounts/${polpAccountId}/transactions`);
  for (const tx of transactions) {
    await svc.from("polp_transactions").upsert({
      client_id: clientId,
      polp_account_id: polpAccountId,
      polp_transaction_id: tx.id,
      external_id: tx.external_id ?? null,
      description: tx.description ?? null,
      amount: tx.amount,
      currency_code: tx.currency_code ?? "BRL",
      date: tx.date,
      type: tx.type,
      status: tx.status ?? null,
      balance_after: tx.balance ?? null,
      category: tx.category ?? null,
      merchant: tx.merchant ?? null,
      payment_data: tx.payment_data ?? null,
      credit_card_metadata: tx.credit_card_metadata ?? null,
      updated_at: new Date().toISOString(),
    }, { onConflict: "client_id,polp_transaction_id" });
  }
}

async function syncBills(svc: ReturnType<typeof createServiceClient>, clientId: string, polpAccountId: number) {
  const bills = await polpGetList<Record<string, unknown>>(`/accounts/${polpAccountId}/bills`);
  for (const bill of bills) {
    await svc.from("polp_bills").upsert({
      client_id: clientId,
      polp_account_id: polpAccountId,
      polp_bill_id: bill.id,
      due_date: (bill.due_date as string).split("T")[0],
      total_amount: bill.total_amount,
      minimum_payment_amount: bill.minimum_payment_amount ?? null,
      currency_code: bill.total_amount_currency_code ?? "BRL",
      allows_installments: bill.allows_installments ?? null,
      finance_charges: bill.finance_charges ?? null,
      payments: bill.payments ?? null,
      updated_at: new Date().toISOString(),
    }, { onConflict: "client_id,polp_bill_id" });
  }
}

Deno.serve(async (req: Request) => {
  if (req.method !== "POST") return json({ error: "Method not allowed" }, 405);

  const rawBody = await req.text();

  if (!(await validateWebhookSignature(rawBody, req))) {
    return json({ error: "Unauthorized" }, 401);
  }

  let payload: PolpWebhookPayload;
  try {
    payload = JSON.parse(rawBody) as PolpWebhookPayload;
  } catch {
    return json({ error: "Invalid JSON" }, 400);
  }

  const eventIdRaw =
    payload.event_id ??
    payload.id ??
    payload.data?.event_id ??
    payload.data?.eventId;
  const eventId = eventIdRaw !== undefined && eventIdRaw !== null
    ? String(eventIdRaw)
    : await fallbackEventIdFromBody(rawBody);

  const svc = createServiceClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

  // Idempotency guard by event_id
  const { data: dedupeRow, error: dedupeErr } = await svc
    .from("polp_webhook_events")
    .insert({
      event_id: eventId,
      event_type: payload.event,
      entity: payload.entity,
      entity_id: payload.entity_id,
      payload,
      status: "processing",
      processed_at: new Date().toISOString(),
    })
    .select("id")
    .maybeSingle();

  if (dedupeErr) {
    const code = (dedupeErr as { code?: string }).code;
    if (code === "23505") {
      return json({ ok: true, duplicate: true, event_id: eventId });
    }
    console.error("polp-webhook dedupe error:", dedupeErr);
    return json({ error: "Failed to register webhook event" }, 500);
  }

  const webhookEventRowId = dedupeRow?.id as string | undefined;

  try {
    // Resolve client_id from polp_integration_id (stored in DB on first connect)
    const resolveClientForIntegration = async (polpIntId: number) => {
      const { data } = await svc
        .from("polp_integrations")
        .select("id, client_id")
        .eq("polp_integration_id", polpIntId)
        .single();
      return data as { id: string; client_id: string } | null;
    };

    // ── integrations.updated ───────────────────────────────────────────────
    if (payload.event === "integrations.updated") {
      const intg = await polpGet<Record<string, unknown>>(`/integrations/${payload.entity_id}`);
      await svc.from("polp_integrations").update({
        status: intg.status,
        execution_status: intg.execution_status,
        error: intg.error ?? null,
        url_to_authenticate: intg.url_to_authenticate ?? null,
        url_to_authenticate_expires_at: intg.url_to_authenticate_expires_at ?? null,
        last_updated_at: intg.last_updated_at ?? null,
        next_auto_sync_at: intg.next_auto_sync_at ?? null,
        updated_at: new Date().toISOString(),
      }).eq("polp_integration_id", payload.entity_id);

      // When integration becomes UPDATED, sync all accounts
      if (intg.status === "UPDATED") {
        const row = await resolveClientForIntegration(payload.entity_id);
        if (row) await syncAccounts(svc, row.client_id, payload.entity_id, row.id);
      }
    }

    // ── accounts.synchronized ─────────────────────────────────────────────
    if (payload.event === "accounts.synchronized") {
      // entity_id here is the account_id; find the integration via account
      const acc = await polpGet<Record<string, unknown>>(`/accounts/${payload.entity_id}/balance`);
      // Update balance
      await svc.from("polp_accounts")
        .update({ balance: acc.balance, updated_at: new Date().toISOString() })
        .eq("polp_account_id", payload.entity_id);
      // Sync fresh transactions
      const { data: accRow } = await svc.from("polp_accounts")
        .select("client_id, polp_account_id")
        .eq("polp_account_id", payload.entity_id)
        .single();
      if (accRow) {
        await syncTransactions(svc, accRow.client_id as string, accRow.polp_account_id as number);
      }
    }

    // ── accounts.updated ──────────────────────────────────────────────────
    if (payload.event === "accounts.updated" && payload.changes?.balance !== undefined) {
      await svc.from("polp_accounts")
        .update({ balance: payload.changes.balance, updated_at: new Date().toISOString() })
        .eq("polp_account_id", payload.entity_id);
    }

    // ── transactions.created / transactions.updated ───────────────────────
    if (payload.event === "transactions.created" || payload.event === "transactions.updated") {
      const tx = await polpGet<Record<string, unknown>>(`/transactions/${payload.entity_id}`);
      const { data: accRow } = await svc.from("polp_accounts")
        .select("client_id")
        .eq("polp_account_id", tx.account_id)
        .single();
      if (accRow) {
        await svc.from("polp_transactions").upsert({
          client_id: accRow.client_id,
          polp_account_id: tx.account_id,
          polp_transaction_id: tx.id,
          external_id: tx.external_id ?? null,
          description: tx.description ?? null,
          amount: tx.amount,
          currency_code: tx.currency_code ?? "BRL",
          date: tx.date,
          type: tx.type,
          status: tx.status ?? null,
          balance_after: tx.balance ?? null,
          category: tx.category ?? null,
          merchant: tx.merchant ?? null,
          payment_data: tx.payment_data ?? null,
          credit_card_metadata: tx.credit_card_metadata ?? null,
          updated_at: new Date().toISOString(),
        }, { onConflict: "client_id,polp_transaction_id" });
      }
    }

    // ── bills.created / bills.updated ─────────────────────────────────────
    if (payload.event === "bills.created" || payload.event === "bills.updated") {
      const bill = await polpGet<Record<string, unknown>>(`/accounts/${payload.entity_id}/bills`);
      // entity_id is bill id; resolve account from bills list response
      // Bills endpoint is per account — entity_id on bill events is the bill id
      // We look up the existing bill row to get account + client
      const { data: billRow } = await svc.from("polp_bills")
        .select("client_id, polp_account_id")
        .eq("polp_bill_id", payload.entity_id)
        .single();
      if (billRow) {
        await svc.from("polp_bills").upsert({
          client_id: billRow.client_id,
          polp_account_id: billRow.polp_account_id,
          polp_bill_id: payload.entity_id,
          due_date: (bill as Record<string, unknown> & { due_date?: string }).due_date?.split("T")[0],
          total_amount: (bill as Record<string, unknown> & { total_amount?: number }).total_amount ?? 0,
          updated_at: new Date().toISOString(),
        }, { onConflict: "client_id,polp_bill_id" });
      }
    }

    if (webhookEventRowId) {
      await svc
        .from("polp_webhook_events")
        .update({
          status: "processed",
          processed_at: new Date().toISOString(),
          error_message: null,
        })
        .eq("id", webhookEventRowId);
    }

    return json({ ok: true });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    console.error("polp-webhook error:", err);

    if (webhookEventRowId) {
      await svc
        .from("polp_webhook_events")
        .update({
          status: "failed",
          processed_at: new Date().toISOString(),
          error_message: message.slice(0, 500),
        })
        .eq("id", webhookEventRowId);
    }

    return json({ error: message }, 500);
  }
});
