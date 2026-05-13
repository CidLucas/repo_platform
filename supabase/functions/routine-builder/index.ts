// supabase/functions/routine-builder/index.ts
//
// AI-powered chat endpoint that helps clients build custom routines through
// conversation. The agent knows the client's available agents (from agent_catalog)
// and the action catalog, and guides the user through defining a routine that
// can then be saved as a client_routine with source='custom'.
//
// Request:  POST { messages: [{role, content}], context?: { domain?: string } }
// Response: { reply: string, routine?: RoutineDraft }
//
// The function returns a streaming SSE response so the chat feels fast.
// If the model outputs a JSON block like:
//   ```json
//   { "routine": { "name": "...", "steps": [...], "trigger_type": "..." } }
//   ```
// it is extracted and returned in the `routine` field alongside the text reply.

import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { requireAuth, createServiceClient } from "../_shared/blu_auth.ts";
import { corsHeaders } from "../_shared/cors.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const ANTHROPIC_API_KEY = Deno.env.get("ANTHROPIC_API_KEY")!;
const CLAUDE_MODEL = "claude-sonnet-4-6";

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  // ── Auth ────────────────────────────────────────────────────────────────────
  let ctx;
  try {
    ctx = await requireAuth(req, SUPABASE_URL, SUPABASE_ANON_KEY);
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "Unauthorized";
    return new Response(JSON.stringify({ error: msg }), {
      status: 401,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const clientId = ctx.appClientId ?? ctx.userClientId;
  if (!clientId) {
    return new Response(JSON.stringify({ error: "No client_id" }), {
      status: 403,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  // ── Parse body ───────────────────────────────────────────────────────────────
  let body: {
    messages: { role: "user" | "assistant"; content: string }[];
    context?: { domain?: string };
  };
  try {
    body = await req.json();
  } catch {
    return new Response(JSON.stringify({ error: "Invalid JSON" }), {
      status: 400,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const { messages, context = {} } = body;

  // ── Fetch action catalog ─────────────────────────────────────────────────────
  const svc = createServiceClient(SUPABASE_URL, SERVICE_ROLE_KEY);

  const { data: actions } = await svc
    .from("agent_action_catalog")
    .select("id, agent_slug, label, description, output_doc_type_id, trigger_capable")
    .eq("is_active", true)
    .order("sort_order");

  const { data: agents } = await svc
    .from("agent_catalog")
    .select("slug, name, description")
    .eq("is_active", true);

  // ── Build system prompt ──────────────────────────────────────────────────────
  const agentList = (agents ?? [])
    .map((a: { slug: string; name: string; description: string | null }) =>
      `- **${a.slug}** (${a.name}): ${a.description ?? ""}`
    )
    .join("\n");

  const actionList = (actions ?? [])
    .map((a: { id: string; agent_slug: string; label: string; description: string | null; trigger_capable: boolean }) =>
      `- \`${a.id}\` [${a.agent_slug}] — ${a.label}${a.description ? `: ${a.description}` : ""}${a.trigger_capable ? " [pode ser gatilho]" : ""}`
    )
    .join("\n");

  const domainContext = context.domain
    ? `\n\nO usuário está configurando rotinas para o domínio: **${context.domain}**.`
    : "";

  const systemPrompt = `Você é o assistente de criação de rotinas do Blu, uma plataforma de IA para pequenas e médias empresas.

Seu objetivo é ajudar o usuário a criar rotinas personalizadas que automatizam processos do negócio usando os agentes disponíveis.
${domainContext}

## Agentes disponíveis
${agentList}

## Ações disponíveis (use o ID exato nos passos)
${actionList}

## Como construir uma rotina
Uma rotina tem:
- **name**: nome curto e descritivo
- **description**: o que ela faz e quando é útil
- **trigger_type**: "manual" | "document" | "schedule" | "event"
- **steps**: lista de passos, cada um com:
  - step: número do passo (1, 2, 3…)
  - agent: slug do agente (ex: "compras")
  - action: ID da ação do catálogo (ex: "compras.create_rfq")
  - output: ID do tipo de documento gerado (opcional)

## Seu processo
1. Entenda o objetivo do usuário com perguntas curtas e objetivas
2. Proponha uma estrutura de rotina clara
3. Quando o usuário confirmar, gere o JSON da rotina

## Quando tiver um rascunho finalizado, responda com:
Texto explicando a rotina, seguido de um bloco JSON:

\`\`\`json
{
  "routine": {
    "name": "Nome da Rotina",
    "description": "Descrição",
    "trigger_type": "manual",
    "steps": [
      { "step": 1, "agent": "compras", "action": "compras.create_rfq" }
    ]
  }
}
\`\`\`

Seja conciso. Prefira confirmações curtas. Não explique conceitos técnicos.`;

  // ── Call Claude API ──────────────────────────────────────────────────────────
  const anthropicResp = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "x-api-key": ANTHROPIC_API_KEY,
      "anthropic-version": "2023-06-01",
      "content-type": "application/json",
    },
    body: JSON.stringify({
      model: CLAUDE_MODEL,
      max_tokens: 1024,
      system: systemPrompt,
      messages,
    }),
  });

  if (!anthropicResp.ok) {
    const err = await anthropicResp.text();
    return new Response(JSON.stringify({ error: `Claude API error: ${err}` }), {
      status: 502,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const result = await anthropicResp.json();
  const reply: string = result.content?.[0]?.text ?? "";

  // ── Extract routine draft if present ─────────────────────────────────────────
  let routine: unknown = null;
  const jsonMatch = reply.match(/```json\s*([\s\S]*?)```/);
  if (jsonMatch) {
    try {
      const parsed = JSON.parse(jsonMatch[1]);
      if (parsed?.routine) routine = parsed.routine;
    } catch {
      // ignore parse errors — just return raw reply
    }
  }

  return new Response(
    JSON.stringify({ reply, routine }),
    {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    }
  );
});
