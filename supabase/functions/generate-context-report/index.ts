// supabase/functions/generate-context-report/index.ts
//
// Generates a monthly business context report for a single client and stores
// it in vector_db.documents so agents can RAG-search it.
//
// This is a TypeScript port of the Python context_report routine
// (libs/blu_agent_framework/src/blu_agent_framework/routines/context_report.py).
//
// Triggered:
//   - Fire-and-forget from onboarding-bootstrap after the RPC completes
//   - Via pg_net on first analytics_v2.reg_jobs 'completed' insertion
//   - Monthly via pg_cron
//
// Request:  POST { client_id: string }
// Response: 200 { document_id, skipped, client_id }
//           Skipped=true means no analytics data yet — caller should retry later.

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { corsHeaders, json } from "../_shared/cors.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

// ─── Constants ────────────────────────────────────────────────────────────────

const DIMENSION_ORDER: [string, string][] = [
  ["finance",    "Finanças"],
  ["commercial", "Comercial"],
  ["inventory",  "Estoque"],
  ["supply",     "Suprimentos"],
];

const SUMMARY_KPIS = [
  "receita_liquida",
  "ticket_medio",
  "total_pedidos",
  "clientes_unicos",
  "taxa_recorrencia_perc",
  "fornecedores_ativos",
];

const SNAPSHOT_KPIS = new Set([
  "receita_ytd",
  "skus_total",
  "clientes_base_total",
  "clientes_ativos_90d",
  "recencia_media_dias",
]);

const STREAK_MIN = 2;

// ─── Types ────────────────────────────────────────────────────────────────────

interface MetricRow {
  dimension: string;
  kpi: string;
  label: string;
  unit: string;
  current_value: number | null;
  prev_month_value: number | null;
  avg_6m: number | null;
  mom_pct: number | null;
  vs_6m_avg_pct: number | null;
  streak_months: number;
}

interface AnnualRow {
  ano: number;
  receita: number | null;
  total_pedidos: number | null;
  clientes_unicos: number | null;
  clientes_novos: number | null;
  ticket_medio: number | null;
  fornecedores_ativos: number | null;
  skus_ativos: number | null;
  yoy_receita_pct: number | null;
  is_partial: boolean;
  receita_anualizada: number | null;
}

interface TopClient {
  nome: string | null;
  receita_total: number | null;
  total_pedidos: number | null;
  share_perc: number | null;
}

interface TopProduct {
  nome: string | null;
  sku: string | null;
  receita_total: number | null;
  quantidade_total_vendida: number | null;
  share_perc: number | null;
}

interface TopSupplier {
  nome: string | null;
  receita_total: number | null;
  total_pedidos_recebidos: number | null;
  share_perc: number | null;
}

interface Insight {
  title: string;
  body: string;
  severity: string;
  dimension: string | null;
}

// ─── Value formatting ────────────────────────────────────────────────────────

function fmt(value: number | null, unit: string): string {
  if (value === null || value === undefined) return "N/D";
  if (unit === "BRL") {
    if (value >= 1_000_000) return `R$ ${(value / 1_000_000).toFixed(1)}M`;
    if (value >= 1_000) return `R$ ${(value / 1_000).toFixed(0)}k`;
    return `R$ ${value.toFixed(0)}`;
  }
  if (unit === "%") return `${value.toFixed(1)}%`;
  if (unit === "count") {
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
    if (value >= 1_000) return Math.round(value).toLocaleString("pt-BR");
    return String(Math.round(value));
  }
  if (unit === "days") return `${Math.round(value)} dias`;
  return value.toFixed(2);
}

function fmtPct(value: number | null): string {
  return value !== null ? `${value.toFixed(1)}%` : "N/D";
}

function fmtChange(momPct: number, unit: string): string {
  const sign = momPct >= 0 ? "+" : "";
  if (unit === "%") return `${sign}${momPct.toFixed(1)} p.p.`;
  return `${sign}${momPct.toFixed(1)}%`;
}

function monthAbbr(month: number): string {
  const ABBR = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"];
  return ABBR[(month - 1) % 12];
}

// ─── Phrase builders ─────────────────────────────────────────────────────────

function buildSnapshotPhrase(row: MetricRow, kpiMap: Map<string, MetricRow>): string {
  const v = row.current_value!;

  if (row.kpi === "receita_ytd") {
    const now = new Date();
    const months = now.getMonth() || 1; // months elapsed (0-based, so Jan=0 → 1)
    const period = now.getMonth() > 0
      ? `jan–${monthAbbr(now.getMonth())}/${now.getFullYear()}`
      : `jan/${now.getFullYear()}`;
    return `**${row.label}**: ${fmt(v, "BRL")} acumulados em ${months} meses (${period})`;
  }

  if (row.kpi === "skus_total") {
    const ativos = kpiMap.get("skus_ativos");
    if (ativos?.current_value) {
      const pct = v > 0 ? ((ativos.current_value / v) * 100).toFixed(1) : "0";
      return `**${row.label}**: ${fmt(v, "count")} SKUs no catálogo · ${fmt(ativos.current_value, "count")} ativos este mês (${pct}% do catálogo)`;
    }
    return `**${row.label}**: ${fmt(v, "count")} SKUs no catálogo`;
  }

  if (row.kpi === "clientes_base_total") {
    const ativos = kpiMap.get("clientes_ativos_90d");
    if (ativos?.current_value && v > 0) {
      const pct = ((ativos.current_value / v) * 100).toFixed(1);
      return `**${row.label}**: ${fmt(v, "count")} clientes cadastrados · ${fmt(ativos.current_value, "count")} ativos nos últimos 90 dias (${pct}% da base)`;
    }
    return `**${row.label}**: ${fmt(v, "count")} clientes cadastrados`;
  }

  if (row.kpi === "clientes_ativos_90d") {
    const base = kpiMap.get("clientes_base_total");
    if (base?.current_value && base.current_value > 0) {
      const pct = ((v / base.current_value) * 100).toFixed(1);
      return `**${row.label}**: ${fmt(v, "count")} clientes (${pct}% dos ${fmt(base.current_value, "count")} cadastrados)`;
    }
    return `**${row.label}**: ${fmt(v, "count")} clientes com compra nos últimos 90 dias`;
  }

  if (row.kpi === "recencia_media_dias") {
    let status: string;
    if (v <= 30) status = "base muito ativa";
    else if (v <= 90) status = "base saudável";
    else if (v <= 180) status = "base envelhecendo";
    else if (v <= 365) status = "base com baixa frequência de retorno";
    else status = "base com alto índice de abandono";
    return `**${row.label}**: ${fmt(v, "days")} em média — ${status}`;
  }

  return `**${row.label}**: ${fmt(v, row.unit)}`;
}

function buildPhrase(row: MetricRow): string {
  const currentStr = fmt(row.current_value, row.unit);
  const parts: string[] = [`**${row.label}**: ${currentStr} este mês`];

  if (row.mom_pct !== null && row.prev_month_value !== null) {
    const prevStr = fmt(row.prev_month_value, row.unit);
    const changeStr = fmtChange(row.mom_pct, row.unit);
    const arrow = row.mom_pct >= 0 ? "▲" : "▼";
    parts.push(`${arrow} ${changeStr} vs mês anterior (${prevStr})`);
  } else if (row.prev_month_value === null) {
    parts.push("primeiro mês com dados");
  }

  if (row.vs_6m_avg_pct !== null && row.avg_6m !== null) {
    const avgStr = fmt(row.avg_6m, row.unit);
    const direction = row.vs_6m_avg_pct >= 0 ? "acima" : "abaixo";
    const absPct = Math.abs(row.vs_6m_avg_pct);
    if (row.unit === "%" && row.current_value !== null) {
      const pp = Math.abs(row.current_value - row.avg_6m);
      parts.push(`${pp.toFixed(1)} p.p. ${direction} da média dos últimos 6 meses (${avgStr})`);
    } else {
      parts.push(`${absPct.toFixed(1)}% ${direction} da média dos últimos 6 meses (${avgStr})`);
    }
  }

  const n = Math.abs(row.streak_months);
  if (n >= STREAK_MIN) {
    const trend = row.streak_months > 0 ? "crescimento" : "queda";
    parts.push(`tendência de ${trend} há ${n} meses consecutivos`);
  }

  return parts.join(" · ");
}

function buildSummary(rows: MetricRow[]): string[] {
  const kpiMap = new Map(rows.map(r => [r.kpi, r]));
  const lines: string[] = [];
  for (const slug of SUMMARY_KPIS) {
    const row = kpiMap.get(slug);
    if (!row || row.current_value === null) continue;
    let line = `**${row.label}**: ${fmt(row.current_value, row.unit)}`;
    if (row.mom_pct !== null) {
      const arrow = row.mom_pct >= 0 ? "▲" : "▼";
      line += ` (${arrow}${fmtChange(row.mom_pct, row.unit)} vs mês anterior)`;
    }
    lines.push(line);
  }
  return lines;
}

function buildSections(rows: MetricRow[]): Record<string, string[]> {
  const sections: Record<string, string[]> = {};
  for (const [dim] of DIMENSION_ORDER) sections[dim] = [];

  const kpiMap = new Map(rows.map(r => [r.kpi, r]));

  for (const row of rows) {
    if (row.current_value === null) continue;
    const phrase = SNAPSHOT_KPIS.has(row.kpi)
      ? buildSnapshotPhrase(row, kpiMap)
      : buildPhrase(row);
    if (row.dimension in sections) sections[row.dimension].push(phrase);
  }
  return sections;
}

// ─── Markdown renderer ───────────────────────────────────────────────────────

function renderMarkdown(opts: {
  empresa: string;
  tier: string;
  monthLabel: string;
  generatedAt: string;
  freshness: string | null;
  summary: string[];
  sections: Record<string, string[]>;
  annual: AnnualRow[];
  topClients: TopClient[];
  topProducts: TopProduct[];
  topSuppliers: TopSupplier[];
  insights: Insight[];
}): string {
  const lines: string[] = [];

  lines.push(`# BLU Relatório de Contexto — ${opts.empresa} (${opts.tier}) — ${opts.monthLabel}`);
  lines.push("");
  const freshnessStr = opts.freshness ? ` · Última sincronização: ${opts.freshness}` : "";
  lines.push(`*Gerado em ${opts.generatedAt}${freshnessStr}*`);
  lines.push("");
  lines.push("---");
  lines.push("");
  lines.push("## Visão Geral");
  lines.push("");
  if (opts.summary.length > 0) {
    for (const line of opts.summary) lines.push(`- ${line}`);
  } else {
    lines.push("*Sem dados de resumo disponíveis.*");
  }
  lines.push("");

  for (const [dim, label] of DIMENSION_ORDER) {
    const section = opts.sections[dim] ?? [];
    if (section.length === 0) continue;
    lines.push("---");
    lines.push("");
    lines.push(`## ${label}`);
    lines.push("");
    for (const phrase of section) lines.push(`- ${phrase}`);
    lines.push("");
  }

  if (opts.annual.length > 0) {
    lines.push("---");
    lines.push("");
    lines.push("## Histórico Anual");
    lines.push("");
    lines.push("| Ano | Receita | Pedidos | Clientes Únicos | Novos Clientes | Ticket Médio | Fornecedores | SKUs | vs Ano Anterior |");
    lines.push("|-----|---------|---------|----------------|----------------|--------------|-------------|------|----------------|");
    for (const y of opts.annual) {
      const yoyStr = y.yoy_receita_pct !== null
        ? `${y.yoy_receita_pct >= 0 ? "+" : ""}${y.yoy_receita_pct.toFixed(1)}%`
        : "—";
      const partial = y.is_partial ? "*" : "";
      lines.push(
        `| ${y.ano}${partial} | ${fmt(y.receita, "BRL")} | ${fmt(y.total_pedidos, "count")} | ${fmt(y.clientes_unicos, "count")} | ${fmt(y.clientes_novos, "count")} | ${fmt(y.ticket_medio, "BRL")} | ${fmt(y.fornecedores_ativos, "count")} | ${fmt(y.skus_ativos, "count")} | ${yoyStr} |`
      );
    }
    const partial = opts.annual.find(y => y.is_partial);
    if (partial) {
      lines.push("");
      lines.push(`*Ano em curso (parcial). Projeção anualizada: ${fmt(partial.receita_anualizada, "BRL")}.*`);
    }
    lines.push("");
  }

  if (opts.topClients.length > 0) {
    lines.push("---");
    lines.push("");
    lines.push("## Top Clientes por Receita (acumulado)");
    lines.push("");
    lines.push("| # | Cliente | Receita Total | Share | Pedidos |");
    lines.push("|---|---------|--------------|-------|---------|");
    opts.topClients.forEach((c, i) => {
      lines.push(`| ${i + 1} | ${c.nome ?? "N/D"} | ${fmt(c.receita_total, "BRL")} | ${fmtPct(c.share_perc)} | ${c.total_pedidos ?? 0} |`);
    });
    lines.push("");
  }

  if (opts.topProducts.length > 0) {
    lines.push("---");
    lines.push("");
    lines.push("## Top Produtos por Receita (acumulado)");
    lines.push("");
    lines.push("| # | Produto | Receita Total | Share | Qtd. Vendida |");
    lines.push("|---|---------|--------------|-------|-------------|");
    opts.topProducts.forEach((p, i) => {
      lines.push(`| ${i + 1} | ${p.nome ?? p.sku ?? "N/D"} | ${fmt(p.receita_total, "BRL")} | ${fmtPct(p.share_perc)} | ${fmt(p.quantidade_total_vendida, "count")} |`);
    });
    lines.push("");
  }

  if (opts.topSuppliers.length > 0) {
    lines.push("---");
    lines.push("");
    lines.push("## Top Fornecedores por Receita (acumulado)");
    lines.push("");
    lines.push("| # | Fornecedor | Receita Total | Share | Pedidos Recebidos |");
    lines.push("|---|-----------|--------------|-------|------------------|");
    opts.topSuppliers.forEach((s, i) => {
      lines.push(`| ${i + 1} | ${s.nome ?? "N/D"} | ${fmt(s.receita_total, "BRL")} | ${fmtPct(s.share_perc)} | ${s.total_pedidos_recebidos ?? 0} |`);
    });
    lines.push("");
  }

  if (opts.insights.length > 0) {
    lines.push("---");
    lines.push("");
    lines.push("## Alertas e Anomalias Detectadas");
    lines.push("");
    for (const ins of opts.insights) {
      const dim = ins.dimension ? ` *(${ins.dimension})*` : "";
      lines.push(`- **[${ins.severity.toUpperCase()}] ${ins.title}**${dim}: ${ins.body}`);
    }
    lines.push("");
  }

  lines.push("---");
  lines.push("*Este documento é gerado automaticamente pela Blu e atualizado mensalmente.*");

  return lines.join("\n");
}

// ─── Main handler ─────────────────────────────────────────────────────────────

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return json({ error: "method not allowed" }, 405);

  // Service-role only
  const authHeader = req.headers.get("Authorization") ?? "";
  if (!authHeader.includes(SUPABASE_SERVICE_ROLE_KEY)) {
    return json({ error: "unauthorized" }, 401);
  }

  let client_id: string;
  try {
    ({ client_id } = await req.json());
  } catch {
    return json({ error: "Invalid JSON body" }, 400);
  }
  if (!client_id) return json({ error: "client_id required" }, 400);

  const svc = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

  try {
    // ── 1. Fetch tenant info ────────────────────────────────────────────────
    const { data: tenantRow } = await svc
      .from("clientes_blu")
      .select("nome_empresa, tier")
      .eq("client_id", client_id)
      .maybeSingle();

    const empresa = tenantRow?.nome_empresa ?? "Empresa";
    const tier = tenantRow?.tier ?? "BASIC";

    // ── 2. Fetch all analytics data in parallel ─────────────────────────────
    const [metricsRes, dimTotalsRes, annualRes, insightsRes, freshnessRes] = await Promise.all([
      svc.rpc("get_context_metrics_for_client", { p_client_id: client_id }),
      svc.rpc("get_dim_totals_for_client", { p_client_id: client_id }),
      svc.rpc("get_annual_metrics_for_client", { p_client_id: client_id }),
      svc
        .from("client_insights")
        .select("title, body, severity, dimension")
        .eq("client_id", client_id)
        .eq("dismissed", false)
        .order("generated_at", { ascending: false })
        .limit(6),
      svc
        .from("analytics_v2.reg_jobs")
        .select("completed_at")
        .eq("client_id", client_id)
        .eq("status", "completed")
        .order("completed_at", { ascending: false })
        .limit(1)
        .maybeSingle(),
    ]);

    const metrics: MetricRow[] = (metricsRes.data ?? []).map((r: Record<string, unknown>) => ({
      dimension: r.dimension as string,
      kpi: r.kpi as string,
      label: r.label as string,
      unit: r.unit as string,
      current_value: r.current_value != null ? Number(r.current_value) : null,
      prev_month_value: r.prev_month_value != null ? Number(r.prev_month_value) : null,
      avg_6m: r.avg_6m != null ? Number(r.avg_6m) : null,
      mom_pct: r.mom_pct != null ? Number(r.mom_pct) : null,
      vs_6m_avg_pct: r.vs_6m_avg_pct != null ? Number(r.vs_6m_avg_pct) : null,
      streak_months: Number(r.streak_months ?? 0),
    }));

    // No analytics data yet — skip gracefully, caller retries later
    if (metrics.length === 0) {
      console.log(`[generate-context-report] No metrics for ${client_id} — skipping`);
      return json({ skipped: true, client_id });
    }

    // ── 3. Fetch top-5 lists from analytics_v2 ─────────────────────────────
    const dimTotals: Record<string, number> = {};
    for (const row of (dimTotalsRes.data ?? []) as { entity: string; total_receita: number }[]) {
      dimTotals[row.entity] = row.total_receita;
    }
    const totalReceita = Object.values(dimTotals).reduce((a, b) => a + b, 0) || 1;

    // Top 5 lists via direct SQL through the Supabase RPC pattern
    // We use a single RPC call to get all top lists efficiently
    const [topClientsRes, topProductsRes, topSuppliersRes] = await Promise.all([
      svc.rpc("get_top_clients_for_client", { p_client_id: client_id, p_limit: 5 }),
      svc.rpc("get_top_products_for_client", { p_client_id: client_id, p_limit: 5 }),
      svc.rpc("get_top_suppliers_for_client", { p_client_id: client_id, p_limit: 5 }),
    ]);

    const topClients: TopClient[] = (topClientsRes.data ?? []).map((r: Record<string, unknown>) => ({
      nome: r.nome as string | null,
      receita_total: r.receita_total != null ? Number(r.receita_total) : null,
      total_pedidos: r.total_pedidos != null ? Number(r.total_pedidos) : null,
      share_perc: r.receita_total != null ? (Number(r.receita_total) / totalReceita) * 100 : null,
    }));

    const topProducts: TopProduct[] = (topProductsRes.data ?? []).map((r: Record<string, unknown>) => ({
      nome: r.nome as string | null,
      sku: r.sku as string | null,
      receita_total: r.receita_total != null ? Number(r.receita_total) : null,
      quantidade_total_vendida: r.quantidade_total_vendida != null ? Number(r.quantidade_total_vendida) : null,
      share_perc: r.receita_total != null ? (Number(r.receita_total) / totalReceita) * 100 : null,
    }));

    const topSuppliers: TopSupplier[] = (topSuppliersRes.data ?? []).map((r: Record<string, unknown>) => ({
      nome: r.nome as string | null,
      receita_total: r.receita_total != null ? Number(r.receita_total) : null,
      total_pedidos_recebidos: r.total_pedidos_recebidos != null ? Number(r.total_pedidos_recebidos) : null,
      share_perc: r.receita_total != null ? (Number(r.receita_total) / totalReceita) * 100 : null,
    }));

    const insights: Insight[] = (insightsRes.data ?? []) as Insight[];
    const annual: AnnualRow[] = (annualRes.data ?? []) as AnnualRow[];

    let freshness: string | null = null;
    const freshnessRaw = freshnessRes.data?.completed_at;
    if (freshnessRaw) {
      try {
        const dt = new Date(freshnessRaw);
        freshness = dt.toLocaleString("pt-BR", { timeZone: "UTC", day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" }) + " UTC";
      } catch { freshness = freshnessRaw; }
    }

    // ── 4. Build report markdown ────────────────────────────────────────────
    const now = new Date();
    const monthLabel = now.toLocaleDateString("pt-BR", { month: "long", year: "numeric" });
    const generatedAt = now.toISOString().replace("T", " ").substring(0, 16) + " UTC";
    const monthSuffix = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
    const storagePath = `${client_id}/context-report-${monthSuffix}.md`;

    const summary = buildSummary(metrics);
    const sections = buildSections(metrics);
    const markdown = renderMarkdown({
      empresa, tier, monthLabel, generatedAt, freshness,
      summary, sections, annual,
      topClients, topProducts, topSuppliers, insights,
    });

    // ── 5. Archive previous generated report ────────────────────────────────
    await svc
      .schema("vector_db")
      .from("documents")
      .update({ source: "archived" })
      .eq("client_id", client_id)
      .eq("source", "generated")
      .eq("category", "business_context");

    // ── 6. Upload markdown to Storage ───────────────────────────────────────
    const { error: uploadErr } = await svc.storage
      .from("knowledge-base")
      .upload(storagePath, new TextEncoder().encode(markdown), {
        contentType: "text/markdown",
        upsert: true,
      });

    if (uploadErr) {
      console.error("[generate-context-report] Storage upload failed:", uploadErr);
      return json({ error: "Storage upload failed", details: uploadErr.message }, 500);
    }

    // ── 7. Insert vector_db.documents row ───────────────────────────────────
    const title = `Relatório de Contexto — ${monthLabel}`;
    const { data: docRow, error: docErr } = await svc
      .schema("vector_db")
      .from("documents")
      .insert({
        client_id,
        title,
        file_name: `context-report-${monthSuffix}.md`,
        file_type: "md",
        storage_path: storagePath,
        source: "generated",
        category: "business_context",
        status: "pending",
        scope: "client",
      })
      .select("id")
      .single();

    if (docErr) {
      console.error("[generate-context-report] Document insert failed:", docErr);
      return json({ error: "Document insert failed", details: docErr.message }, 500);
    }

    const documentId = docRow.id as string;

    // ── 8. Fire process-document (fire-and-forget) ──────────────────────────
    EdgeRuntime.waitUntil(
      fetch(`${SUPABASE_URL}/functions/v1/process-document`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
        },
        body: JSON.stringify({
          document_id: documentId,
          storage_path: storagePath,
          client_id,
          file_name: `context-report-${monthSuffix}.md`,
          file_type: "md",
          target_tokens: 300,
          skip_metadata_enrichment: true,
        }),
      })
        .then(async (r) => {
          if (!r.ok) {
            const txt = await r.text().catch(() => "");
            console.warn(`[generate-context-report] process-document ${r.status}: ${txt}`);
          }
        })
        .catch((err) => console.warn("[generate-context-report] process-document fire failed:", err))
    );

    console.log(`[generate-context-report] Done for ${client_id}: doc=${documentId}`);
    return json({ document_id: documentId, skipped: false, client_id });

  } catch (err) {
    console.error("[generate-context-report] Unhandled error:", err);
    return json({ error: "internal error", details: (err as Error).message }, 500);
  }
});
