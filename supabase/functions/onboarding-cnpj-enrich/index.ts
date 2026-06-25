// supabase/functions/onboarding-cnpj-enrich/index.ts
//
// B-1 AC-1: Edge function que valida CNPJ localmente (sem chamar API externa)
// e retorna dados mockados da Receita Federal para CNPJs válidos.
//
// Request:
//   POST { cnpj: string }
//
// Response (válido, 200):
//   { razao_social, nome_fantasia, cnae, cnae_descricao, endereco, telefone }
//
// Response (inválido, 400):
//   { error: "mensagem" }

import { corsHeaders, json } from "../_shared/cors.ts";

// ── CNPJ validation ─────────────────────────────────────────────────────────

const REPEATED_DIGITS_RE = /^(\d)\1+$/;

/**
 * Valida um CNPJ localmente (14 dígitos + dígitos verificadores).
 * Retorna true se o CNPJ é válido, false caso contrário.
 */
export function isValidCNPJ(raw: string): boolean {
  if (typeof raw !== "string") return false;

  const cnpj = raw.trim();

  // Deve ter exatamente 14 caracteres
  if (cnpj.length !== 14) return false;

  // Deve conter apenas dígitos numéricos
  if (!/^\d{14}$/.test(cnpj)) return false;

  // Rejeitar sequências repetidas (11111111111111, etc.)
  if (REPEATED_DIGITS_RE.test(cnpj)) return false;

  // ── Validação dos dígitos verificadores ──────────────────────────────────
  const digits = cnpj.split("").map(Number);

  // Primeiro dígito verificador (13ª posição)
  const w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  let sum1 = 0;
  for (let i = 0; i < 12; i++) {
    sum1 += digits[i] * w1[i];
  }
  const d1 = (sum1 % 11) < 2 ? 0 : 11 - (sum1 % 11);
  if (d1 !== digits[12]) return false;

  // Segundo dígito verificador (14ª posição)
  const w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  let sum2 = 0;
  for (let i = 0; i < 13; i++) {
    sum2 += digits[i] * w2[i];
  }
  const d2 = (sum2 % 11) < 2 ? 0 : 11 - (sum2 % 11);
  if (d2 !== digits[13]) return false;

  return true;
}

// ── Mock data para CNPJs válidos ────────────────────────────────────────────

/**
 * Gera dados mockados estilo Receita Federal para um CNPJ válido.
 * Usa os primeiros dígitos do CNPJ para dar um ar de consistência.
 */
function mockReceitaData(cnpj: string) {
  const prefix = cnpj.slice(0, 8);
  return {
    razao_social: `Empresa Exemplo ${prefix} Ltda`,
    nome_fantasia: `Exemplo ${prefix}`,
    cnae: `${prefix.slice(0, 4)}-${prefix.slice(4, 5)}/00`,
    cnae_descricao: "Atividades de consultoria em gestão empresarial",
    endereco: {
      logradouro: "Avenida Paulista",
      numero: "1000",
      complemento: "Sala 501",
      bairro: "Bela Vista",
      cidade: "São Paulo",
      uf: "SP",
      cep: "01310-100",
    },
    telefone: "(11) 99999-0000",
  };
}

// ── Handler exportada ───────────────────────────────────────────────────────

export async function handleCnpjEnrich(req: Request): Promise<Response> {
  try {
    // Extrair body
    let body: { cnpj?: unknown };
    try {
      body = await req.json() as { cnpj?: unknown };
    } catch {
      return json({ error: "JSON inválido no corpo da requisição" }, 400);
    }

    const cnpj = body?.cnpj;

    // Validar se é string
    if (typeof cnpj !== "string") {
      return json({ error: "CNPJ deve ser uma string" }, 400);
    }

    // Validar CNPJ
    if (!isValidCNPJ(cnpj)) {
      return json({ error: "CNPJ inválido" }, 400);
    }

    // CNPJ válido — retorna dados mockados da Receita
    const data = mockReceitaData(cnpj);
    return json(data, 200);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Erro interno";
    console.error("[onboarding-cnpj-enrich] unhandled error:", err);
    return json({ error: message }, 500);
  }
}

// ── Supabase Edge Function entry point ──────────────────────────────────────

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return json({ error: "method not allowed" }, 405);
  }

  return handleCnpjEnrich(req);
});
