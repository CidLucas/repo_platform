/**
 * polp-sync — Manual full sync for a client's Polp integrations
 *
 * Called when user clicks the "↻" sync button on the Open Finance card in AdminScreen.
 * Fetches all integrations for the client, then syncs accounts + transactions + bills.
 */

import {
  createServiceClient,
  createUserClient,
  requireAuth,
} from "../_shared/blu_auth.ts";
import { corsHeaders, json } from "../_shared/cors.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const POLP_API_CLIENT = Deno.env.get("POLP_API_CLIENT")!;
const POLP_API_SECRET = Deno.env.get("POLP_API_SECRET")!;
const POLP_BASE_URL = "https://dev.polp.com.br/api/v1";

const polpHeaders = {
  "x-api-client": POLP_API_CLIENT,
  "x-api-secret": POLP_API_SECRET,
};

async function polpGetList<T>(path: string): Promise<T[]> {
  const res = await fetch(`${POLP_BASE_URL}${path}`, { headers: polpHeaders });
  if (!res.ok) throw new Error(`Polp ${path} → ${res.status}`);
  const body = await res.json();
  return (body.data ?? []) as T[];
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return json({ error: "Method not allowed" }, 405);

  try {
    const ctx = await requireAuth(req, SUPABASE_URL, SUPABASE_ANON_KEY);
    const userClient = createUserClient(ctx.token, SUPABASE_URL, SUPABASE_ANON_KEY);
    const svc = createServiceClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

    const { client_id } = await req.json() as { client_id: string };
    if (!client_id) return json({ error: "client_id required" }, 400);

    const { data: membership } = await userClient
      .from("client_users")
      .select("id")
      .eq("client_id", client_id)
      .eq("auth_user_id", ctx.userId)
      .single();
    if (!membership) return json({ error: "Forbidden" }, 403);

    // Load all polp integrations for this client
    const { data: integrations, error: intgErr } = await svc
      .from("polp_integrations")
      .select("id, polp_integration_id, status")
      .eq("client_id", client_id);
    if (intgErr) throw intgErr;

    let accountsSynced = 0;
    let transactionsSynced = 0;
    let billsSynced = 0;

    for (const intg of integrations ?? []) {
      if (intg.status === "DELETED") continue;

      const accounts = await polpGetList<Record<string, unknown>>(
        `/integrations/${intg.polp_integration_id}/accounts`
      );

      for (const acc of accounts) {
        await svc.from("polp_accounts").upsert({
          client_id,
          integration_id: intg.id,
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
        accountsSynced++;

        // Transactions (first page — 50 most recent)
        const txs = await polpGetList<Record<string, unknown>>(
          `/accounts/${acc.id}/transactions`
        );
        for (const tx of txs) {
          await svc.from("polp_transactions").upsert({
            client_id,
            polp_account_id: acc.id,
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
          transactionsSynced++;
        }

        // Bills for credit accounts
        if (acc.type === "CREDIT") {
          const bills = await polpGetList<Record<string, unknown>>(
            `/accounts/${acc.id}/bills`
          );
          for (const bill of bills) {
            await svc.from("polp_bills").upsert({
              client_id,
              polp_account_id: acc.id,
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
            billsSynced++;
          }
        }
      }
    }

    return json({ ok: true, accounts_synced: accountsSynced, transactions_synced: transactionsSynced, bills_synced: billsSynced });
  } catch (err) {
    const status = (err as { status?: number }).status ?? 500;
    return json({ error: (err as Error).message }, status);
  }
});
