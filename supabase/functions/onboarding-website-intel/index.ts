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
  if (/(servi[cç]o|ag[eê]ncia|consultoria|atendimento)/.test(t)) return "servicos";
  if (/(design|gr[aá]fico|ux|ui)/.test(t)) return "design";
  if (/(buffet|catering|evento)/.test(t)) return "alimentacao";
  if (/(constru[cç]|construcao|obra|edifica)/.test(t)) return "construcao";
  if (/(log[ií]stica|logistica|transportadora|frete|entregas?)/.test(t)) return "logistica";
  if (/(consultoria|assessoria|consultor)/.test(t)) return "consultoria";
  if (/(advocacia|advogado|jur[ií]dico|direito)/.test(t)) return "juridico";
  if (/(imobili[aá]ri|imobiliari|corretor|im[oó]veis?)/.test(t)) return "imobiliario";
  if (/(seguro|previd[eê]ncia)/.test(t)) return "financeiro";
  if (/(turismo|viagem|hotel|passagem)/.test(t)) return "turismo";
  if (/(alimenta|caf[eé]|restaurante|comida)/.test(t)) return "alimentacao";
  if (/(transporte|traslado|mudan[cç]a|motorista)/.test(t)) return "logistica";
  if (/(beleza|est[eé]tica|cabelo|maquiagem)/.test(t)) return "beleza";
  if (/(fitness|academia|personal|treino)/.test(t)) return "fitness";
  if (/(oficina|mec[aâ]nica|reparo|conserto)/.test(t)) return "automotivo";
  if (/(engenharia|engenheiro|projeto|obra)/.test(t)) return "engenharia";
  if (/(marketing|publicidade|propaganda|m[ií]dia)/.test(t)) return "marketing";
  if (/(\bti\b|tecnologia|inform[aá]tica|software|desenvolvedor)/.test(t)) return "tecnologia";
  return null;
}

function extractCNPJ(html: string): string | null {
  const pattern = /\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}/;
  const match = html.match(pattern);
  return match ? match[0] : null;
}

function extractPhone(html: string): string | null {
  const formattedPattern = /\(\d{2}\)\s?\d{4,5}-?\d{4}/;
  const formattedMatch = html.match(formattedPattern);
  if (formattedMatch) return formattedMatch[0];

  const plainPattern = /\d{10,11}/;
  const plainMatch = html.match(plainPattern);
  return plainMatch ? plainMatch[0] : null;
}

function validateCNPJ(cnpj) {
  const cleaned = cnpj.replace(/\D/g, "");
  if (cleaned.length !== 14) return false;

  const weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  const weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];

  let sum = 0;
  for (let i = 0; i < 12; i++) {
    sum += parseInt(cleaned[i]) * weights1[i];
  }
  let rest = sum % 11;
  const dv1 = rest < 2 ? 0 : 11 - rest;

  sum = 0;
  for (let i = 0; i < 13; i++) {
    sum += parseInt(cleaned[i]) * weights2[i];
  }
  rest = sum % 11;
  const dv2 = rest < 2 ? 0 : 11 - rest;

  return dv1 === parseInt(cleaned[12]) && dv2 === parseInt(cleaned[13]);
}

function calcSourceConfidence(sourceCount: number): number {
  if (sourceCount >= 3) return 0.7;
  if (sourceCount >= 2) return 0.5;
  return 0.3;
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
        cnpj: null,
        telefone: null,
        confidence_details: {
          cnpj_confidence: 0,
          telefone_confidence: 0,
          vertical_confidence: 0,
        },
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

    const rawCnpj = extractCNPJ(html);
    const cnpj = rawCnpj && validateCNPJ(rawCnpj) ? rawCnpj : null;
    const telefone = extractPhone(html);
    const vertical = detectVertical(summaryText);
    const suggestions = suggestFromVertical(vertical);

    // Source counting for confidence scoring
    let sourceCount = 0;
    if (title) sourceCount++;
    if (metaDescMatch?.[1]) sourceCount++;
    if (html.length > 0) sourceCount++;
    const sourceConfidence = calcSourceConfidence(sourceCount);

    const cnpj_confidence = cnpj ? sourceConfidence : 0;
    const telefone_confidence = telefone ? sourceConfidence : 0;
    const vertical_confidence = vertical ? sourceConfidence : 0;
    const confidence = (cnpj_confidence + telefone_confidence + vertical_confidence) / 3;

    return json({
      company_name: title,
      vertical,
      suggested_size: null,
      ...suggestions,
      confidence,
      cnpj,
      telefone,
      confidence_details: {
        cnpj_confidence,
        telefone_confidence,
        vertical_confidence,
      },
    });
  } catch (err) {
    console.warn("[onboarding-website-intel] fallback due to error", err);
    return json({
      company_name: null,
      vertical: null,
      suggested_size: null,
      ...suggestFromVertical(null),
      confidence: 0,
      cnpj: null,
      telefone: null,
      confidence_details: {
        cnpj_confidence: 0,
        telefone_confidence: 0,
        vertical_confidence: 0,
      },
    });
  }
});
