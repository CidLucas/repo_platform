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

function normalizeUrl(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return "";
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    return trimmed;
  }
  return `https://${trimmed}`;
}

function stripHtml(input: string): string {
  return input
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function detectVertical(text: string): string | null {
  const t = text.toLowerCase();
  if (/(loja|e-commerce|ecommerce|checkout|carrinho|sku|produto)/.test(t)) return "ecommerce";
  if (/(distribui|atacado|fornecedor|compras|estoque|supply)/.test(t)) return "industria";
  if (/(cl[ií]nica|hospital|paciente|consult[oó]rio)/.test(t)) return "saude";
  if (/(curso|aluno|escola|educa)/.test(t)) return "educacao";
  if (/(contabil|financeir|banco|cr[eé]dito|invest)/.test(t)) return "financeiro";
  if (/(servi[cç]o|ag[eê]ncia|consultoria|atendimento)/.test(t)) return "servicos";
  return null;
}

function suggestFromVertical(vertical: string | null) {
  if (vertical === "ecommerce") {
    return {
      suggested_agents: ["analytics", "inventory", "marketing"],
      suggested_routines: ["daily_sales_digest", "low_stock_alert", "stale_lead_followup"],
      suggested_kpis: {
        commercial: ["com.receita_periodo", "com.ticket_medio", "com.clientes_novos", "com.clientes_recorrentes", "com.crescimento_receita_perc"],
        inventory: ["inv.skus_ativos", "inv.qtd_vendida_periodo", "inv.receita_periodo", "inv.giro_estimado", "inv.stockout_rate_perc"],
        supply: ["sup.rfqs_abertas", "sup.taxa_resposta_perc", "sup.tempo_resposta_medio_h", "sup.spend_periodo", "sup.fornecedores_ativos"],
        finance: ["fin.receita_liquida", "fin.ticket_medio", "fin.margem_bruta_perc", "fin.crescimento_receita_perc", "fin.total_pedidos"],
      },
    };
  }

  if (vertical === "servicos") {
    return {
      suggested_agents: ["crm", "scheduling", "analytics"],
      suggested_routines: ["stale_lead_followup", "appointment_reminder", "weekly_performance"],
      suggested_kpis: {
        commercial: ["com.pedidos_periodo", "com.clientes_novos", "com.clientes_recorrentes", "com.recencia_media_dias", "com.ticket_medio"],
        inventory: ["inv.skus_ativos", "inv.ticket_medio_sku", "inv.receita_periodo", "inv.qtd_vendida_periodo", "inv.crescimento_quantidade_perc"],
        supply: ["sup.pos_pendentes_aprovacao", "sup.cycle_time_medio_h", "sup.fornecedores_ativos", "sup.spend_periodo", "sup.taxa_resposta_perc"],
        finance: ["fin.receita_liquida", "fin.custo_total", "fin.margem_operacional_perc", "fin.ticket_medio", "fin.crescimento_receita_perc"],
      },
    };
  }

  return {
    suggested_agents: ["analytics", "crm", "documents"],
    suggested_routines: ["daily_sales_digest", "weekly_performance", "low_stock_alert"],
    suggested_kpis: {
      commercial: ["com.receita_periodo", "com.ticket_medio", "com.clientes_unicos", "com.clientes_novos", "com.crescimento_receita_perc"],
      inventory: ["inv.skus_ativos", "inv.qtd_vendida_periodo", "inv.receita_periodo", "inv.ticket_medio_sku", "inv.crescimento_quantidade_perc"],
      supply: ["sup.rfqs_abertas", "sup.taxa_resposta_perc", "sup.spend_periodo", "sup.fornecedores_ativos", "sup.pos_pendentes_aprovacao"],
      finance: ["fin.receita_liquida", "fin.custo_total", "fin.margem_bruta_perc", "fin.ticket_medio", "fin.total_pedidos"],
    },
  };
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }
  if (req.method !== "POST") {
    return json({ error: "method not allowed" }, 405);
  }

  try {
    const body = (await req.json()) as { website_url?: string };
    const normalized = normalizeUrl(body.website_url ?? "");
    if (!normalized) {
      return json({
        company_name: null,
        vertical: null,
        suggested_size: null,
        ...suggestFromVertical(null),
        confidence: 0,
      });
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    let html = "";
    try {
      const resp = await fetch(normalized, {
        method: "GET",
        signal: controller.signal,
        headers: {
          "User-Agent": "BluOnboardingIntel/1.0",
        },
      });
      if (resp.ok) {
        html = await resp.text();
      }
    } finally {
      clearTimeout(timeout);
    }

    const titleMatch = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
    const metaDescMatch = html.match(/<meta[^>]+name=["']description["'][^>]+content=["']([^"']+)["']/i);

    const title = titleMatch ? stripHtml(titleMatch[1]) : null;
    const summaryText = stripHtml([title ?? "", metaDescMatch?.[1] ?? "", html.slice(0, 3000)].join(" "));

    const vertical = detectVertical(summaryText);
    const suggestions = suggestFromVertical(vertical);

    return json({
      company_name: title,
      vertical,
      suggested_size: null,
      ...suggestions,
      confidence: vertical ? 0.72 : 0.45,
    });
  } catch (err) {
    console.warn("[onboarding-website-intel] fallback due to error", err);
    return json({
      company_name: null,
      vertical: null,
      suggested_size: null,
      ...suggestFromVertical(null),
      confidence: 0.35,
    });
  }
});
