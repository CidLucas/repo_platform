import { corsHeaders, json } from "../_shared/cors.ts";

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
  if (/(design|logo|branding|criativo|artes|visual)/.test(t)) return "design";
  if (/(buffet|eventos|festa|cerimonia|gastronomia)/.test(t)) return "buffet";
  if (/(construcao|obra|engenharia|incorporadora|reforma)/.test(t)) return "construcao";
  if (/(logistica|frete|transporte|entregas|frota)/.test(t)) return "logistica";
  if (/(consultoria|assessoria|mentoria|treinamento)/.test(t)) return "consultoria";
  if (/(servi[cç]o|ag[eê]ncia|consultoria|atendimento)/.test(t)) return "servicos";
  return null;
}

function validateCNPJ(cnpj: string): boolean {
  const digits = cnpj.replace(/\D/g, "");
  if (digits.length !== 14) return false;
  if (/^(\d)\1+$/.test(digits)) return false;
  const weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  const weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  let sum1 = 0;
  for (let i = 0; i < 12; i++) {
    sum1 += parseInt(digits[i], 10) * weights1[i];
  }
  const rem1 = sum1 % 11;
  const d1 = rem1 < 2 ? 0 : 11 - rem1;
  if (d1 !== parseInt(digits[12], 10)) return false;
  let sum2 = 0;
  for (let i = 0; i < 13; i++) {
    sum2 += parseInt(digits[i], 10) * weights2[i];
  }
  const rem2 = sum2 % 11;
  const d2 = rem2 < 2 ? 0 : 11 - rem2;
  if (d2 !== parseInt(digits[13], 10)) return false;
  return true;
}

function extractCNPJ(html: string): string | null {
  const regex = /(\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2})/g;
  const matches = html.match(regex);
  if (!matches) return null;
  for (const m of matches) {
    if (validateCNPJ(m)) return m;
  }
  return null;
}

function extractPhone(html: string): string | null {
  const regex = /\(\d{2}\)\s?(?:9\d{4}-\d{4}|\d{4}-\d{4})/g;
  const match = html.match(regex);
  return match ? match[0] : null;
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
        cnpj: null,
        phone: null,
        ...suggestFromVertical(null),
        confidence: 0.3,
      });
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
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
    const cnpj = extractCNPJ(html);
    const phone = extractPhone(html);

    const vertical = detectVertical(summaryText);
    const suggestions = suggestFromVertical(vertical);

    const sourceCount =
      (title ? 1 : 0) +
      (metaDescMatch ? 1 : 0) +
      (cnpj ? 1 : 0) +
      (phone ? 1 : 0) +
      (summaryText.length > 0 ? 1 : 0);

    let confidence: number;
    if (sourceCount >= 3) confidence = 0.7;
    else if (sourceCount === 2) confidence = 0.5;
    else confidence = 0.3;

    return json({
      company_name: title,
      vertical,
      suggested_size: null,
      cnpj,
      phone,
      ...suggestions,
      confidence,
    });
  } catch (err) {
    console.warn("[onboarding-website-intel] fallback due to error", err);
    return json({
      company_name: null,
      vertical: null,
      suggested_size: null,
      cnpj: null,
      phone: null,
      ...suggestFromVertical(null),
      confidence: 0.35,
    });
  }
});
