// supabase/functions/website-context-builder/index.ts
//
// Builds a rich Markdown context document from a client's website and stores
// it in vector_db.documents so agents can RAG-search it.
//
// Triggered fire-and-forget from onboarding-bootstrap after the RPC completes.
// Can also be called directly (e.g., to refresh a client's context).
//
// Flow:
//   1. Validate service-role JWT (internal call only).
//   2. Multi-page Deno fetch crawl of the website (no heavy browser needed here —
//      we call the tool_pool_api crawl tool for deep crawling instead).
//   3. Combine crawled content + onboarding_state answers → Markdown doc.
//   4. Upload to Storage bucket "knowledge-base" at onboarding/context_{client_id}.md
//   5. Insert row into vector_db.documents with source='onboarding.website_context'.
//   6. Call process-document EF to chunk + embed (skip_metadata_enrichment=true).
//
// Request:  POST { client_id, website, onboarding_state }
// Response: 200 { document_id, pages_crawled }

import { corsHeaders, json } from "../_shared/cors.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

// -- Types -------------------------------------------------------------------

interface OnboardingSnapshot {
  nome?: string;
  empresa?: string;
  website?: string;
  vertical?: string | null;
  teamSize?: string | null;
  email?: string;
}

interface BuildRequest {
  client_id: string;
  website: string;
  onboarding_state?: OnboardingSnapshot;
}

// -- Helpers -----------------------------------------------------------------

/** Normalise a URL input — add https:// if missing. */
function normaliseUrl(raw: string): string {
  raw = raw.trim();
  if (!raw.startsWith("http://") && !raw.startsWith("https://")) {
    raw = `https://${raw}`;
  }
  return raw;
}

/** Strip HTML tags, collapse whitespace. */
function stripHtml(html: string): string {
  return html
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, " ")
    .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s{2,}/g, " ")
    .trim();
}

/** Fetch a single page with timeout. Returns {url, text} or null on failure. */
async function fetchPage(
  url: string,
  timeoutMs = 8000,
): Promise<{ url: string; text: string } | null> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const resp = await fetch(url, {
      signal: controller.signal,
      headers: { "User-Agent": "BluContextBot/1.0" },
    });
    clearTimeout(timer);
    if (!resp.ok) return null;
    const ct = resp.headers.get("content-type") ?? "";
    if (!ct.includes("text/html")) return null;
    const html = await resp.text();
    const text = stripHtml(html).slice(0, 6000); // cap per page
    return { url, text };
  } catch {
    clearTimeout(timer);
    return null;
  }
}

/** Discover up to maxLinks internal links from an HTML page. */
function extractInternalLinks(html: string, base: string, limit = 8): string[] {
  const origin = new URL(base).origin;
  const hrefs = [...html.matchAll(/href=["']([^"']+)["']/gi)].map((m) => m[1]);
  const seen = new Set<string>();
  const links: string[] = [];
  for (const href of hrefs) {
    try {
      const abs = new URL(href, base).toString();
      if (abs.startsWith(origin) && !seen.has(abs)) {
        seen.add(abs);
        links.push(abs);
        if (links.length >= limit) break;
      }
    } catch {
      // ignore malformed hrefs
    }
  }
  return links;
}

/** Lightweight multi-page crawl using Deno fetch (no headless browser). */
async function crawlWebsite(
  rootUrl: string,
): Promise<{ url: string; text: string }[]> {
  // Fetch root page to discover links
  const rootResp = await fetchPage(rootUrl);
  if (!rootResp) return [];

  const pages: { url: string; text: string }[] = [rootResp];

  // Get the raw HTML for link extraction
  let rootHtml = "";
  try {
    const r2 = await fetch(rootUrl, { headers: { "User-Agent": "BluContextBot/1.0" } });
    rootHtml = await r2.text();
  } catch {
    // ignore
  }

  const internalLinks = extractInternalLinks(rootHtml, rootUrl, 8);

  // Concurrently fetch sub-pages (max 8 additional)
  const subResults = await Promise.allSettled(
    internalLinks.map((link) => fetchPage(link, 6000)),
  );
  for (const r of subResults) {
    if (r.status === "fulfilled" && r.value) {
      pages.push(r.value);
    }
  }

  return pages;
}

/** Build the Markdown context document from crawled pages + onboarding answers. */
function buildContextMarkdown(
  pages: { url: string; text: string }[],
  state: OnboardingSnapshot,
  website: string,
): string {
  const verticalLabel: Record<string, string> = {
    ecommerce: "E-commerce / Varejo",
    servicos: "Serviços / Consultoria",
    industria: "Indústria / Distribuição",
    saude: "Saúde",
    educacao: "Educação",
    financeiro: "Financeiro",
    agro: "Agro",
    outro: "Outro",
  };
  const teamLabel: Record<string, string> = {
    solo: "Solopreneur",
    pequeno: "2–10 pessoas",
    estruturado: "10–50 pessoas",
  };

  const sections: string[] = [];

  // Header
  sections.push(`# Contexto da Empresa: ${state.empresa ?? "—"}`);
  sections.push(`> Gerado automaticamente pelo pipeline de onboarding Blu.`);
  sections.push(`> Fonte: ${website}`);
  sections.push("");

  // Onboarding facts
  sections.push("## Dados do Onboarding");
  if (state.empresa) sections.push(`- **Empresa:** ${state.empresa}`);
  if (state.nome) sections.push(`- **Responsável:** ${state.nome}`);
  if (state.email) sections.push(`- **Email:** ${state.email}`);
  if (state.vertical) {
    sections.push(`- **Setor:** ${verticalLabel[state.vertical] ?? state.vertical}`);
  }
  if (state.teamSize) {
    sections.push(`- **Tamanho do time:** ${teamLabel[state.teamSize] ?? state.teamSize}`);
  }
  sections.push("");

  // Website content
  sections.push("## Conteúdo do Site");
  for (const page of pages) {
    if (!page.text.trim()) continue;
    sections.push(`### ${page.url}`);
    sections.push(page.text.slice(0, 3000));
    sections.push("");
  }

  return sections.join("\n");
}

// -- Structured context extractor (heuristic, no external LLM required) ------

interface StructuredContext {
  products: string[];
  services: string[];
  differentiators: string[];
  target_audience: string;
  value_proposition: string;
}

function normalizeList(value: unknown): string[] {
  if (!value) return [];
  if (Array.isArray(value)) return value.map((item) => String(item).trim()).filter(Boolean);
  return String(value).split(",").map((item) => item.trim()).filter(Boolean);
}

function buildStructuredContext(
  pages: { url: string; text: string }[],
  state: OnboardingSnapshot,
): StructuredContext {
  const combined = pages.map((p) => p.text).join("\n\n");
  const lower = combined.toLowerCase();
  const sections: StructuredContext = {
    products: [],
    services: [],
    differentiators: [],
    target_audience: "",
    value_proposition: "",
  };

  const productHints = [
    "produtos",
    "catálogo",
    "catalog",
    "sku",
    "item",
    "serviços",
    "services",
    "soluções",
    "solutions",
    "o que oferecemos",
    "nossos produtos",
  ];
  const differentiatorHints = [
    "diferencial",
    "vantagem",
    "por que nós",
    "por que escolher",
    "benefício",
    "benefícios",
    "diferenciais",
    "somos diferentes",
    "unique",
    "why us",
  ];
  const audienceHints = [
    "público",
    "publico",
    "clientes",
    "clientes-alvo",
    "target",
    "para quem",
    "para empresas",
    "para famílias",
    "para quem",
  ];
  const valueHints = [
    "proposta de valor",
    "value proposition",
    "o que fazemos",
    "nossa missão",
    "missão",
    "visão",
    "valores",
    "fazemos acontecer",
  ];

  if (state.produtoServico) {
    sections.products = normalizeList(state.produtoServico);
  }
  if (state.vertical) {
    sections.services = normalizeList(state.vertical);
  }

  const pickLines = (hints: string[], maxLines = 12): string[] => {
    const sentences = combined
      .split(/(?<=[.!?])\s+/)
      .map((sentence) => sentence.trim())
      .filter((sentence) => sentence.length > 10 && sentence.length < 600);

    const scored = sentences
      .map((sentence) => {
        const lowerSentence = sentence.toLowerCase();
        const score = hints.reduce((acc, hint) => (lowerSentence.includes(hint) ? acc + 1 : acc), 0);
        return { sentence, score };
      })
      .filter((item) => item.score > 0)
      .sort((a, b) => b.score - a.score);

    const lines: string[] = [];
    for (const item of scored.slice(0, maxLines)) {
      const text = item.sentence.replace(/\s+/g, " ").trim();
      if (!lines.some((existing) => existing.toLowerCase() === text.toLowerCase())) {
        lines.push(text);
      }
    }
    return lines.slice(0, maxLines);
  };

  if (sections.products.length === 0 && combined) {
    sections.products = pickLines(productHints, 8).slice(0, 6);
  }
  sections.differentiators = pickLines(differentiatorHints, 10).slice(0, 6);
  sections.target_audience = pickLines(audienceHints, 6)[0] || "";
  sections.value_proposition = pickLines(valueHints, 6)[0] || "";

  return sections;
}

// -- Main handler ------------------------------------------------------------

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }
  if (req.method !== "POST") {
    return json({ error: "method not allowed" }, 405);
  }

  // Service-role only (called server-to-server from onboarding-bootstrap)
  const authHeader = req.headers.get("Authorization") ?? "";
  if (!authHeader.includes(SUPABASE_SERVICE_ROLE_KEY)) {
    return json({ error: "forbidden" }, 403);
  }

  let body: BuildRequest;
  try {
    body = (await req.json()) as BuildRequest;
  } catch {
    return json({ error: "invalid JSON body" }, 400);
  }

  const { client_id, website, onboarding_state = {} } = body;
  if (!client_id || !website) {
    return json({ error: "client_id and website are required" }, 400);
  }

  const rootUrl = normaliseUrl(website);
  console.log(`[website-context-builder] client=${client_id} url=${rootUrl}`);

  // ── Step 1: Crawl the website ─────────────────────────────────────────────
  let pages: { url: string; text: string }[] = [];
  try {
    pages = await crawlWebsite(rootUrl);
    console.log(`[website-context-builder] crawled ${pages.length} pages`);
  } catch (err) {
    console.warn("[website-context-builder] crawl failed:", err);
    // Continue with zero pages — we still write a minimal doc from onboarding data
  }

  // ── Step 2: Build Markdown doc ────────────────────────────────────────────
  const markdown = buildContextMarkdown(pages, onboarding_state, rootUrl);

  // ── Step 3: Upload to Storage ─────────────────────────────────────────────
  const adminClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);
  const storagePath = `onboarding/context_${client_id}.md`;

  const { error: uploadError } = await adminClient.storage
    .from("knowledge-base")
    .upload(storagePath, new TextEncoder().encode(markdown), {
      contentType: "text/markdown",
      upsert: true,
    });

  if (uploadError) {
    console.error("[website-context-builder] Storage upload failed:", uploadError);
    return json({ error: "storage upload failed", details: uploadError.message }, 500);
  }

  // ── Step 4: Insert document record ───────────────────────────────────────
  const fileName = `Contexto Web — ${onboarding_state.empresa ?? client_id}`;
  const { data: docRow, error: insertError } = await adminClient
    .from("documents")
    .schema("vector_db")
    .insert({
      client_id,
      file_name: fileName,
      file_type: "md",
      storage_path: storagePath,
      source: "onboarding.website_context",
      source_url: rootUrl,
    })
    .select("id")
    .single();

  if (insertError) {
    console.error("[website-context-builder] Document insert failed:", insertError);
    return json({ error: "document insert failed", details: insertError.message }, 500);
  }

  const documentId: string = (docRow as { id: string }).id;

  // ── Step 4b: Mark 'posicionamento' document in knowledge inventory ────────
  // Best-effort — website context qualifies as a partial positioning document.
  // Never-downgrade guard: only upsert if not already 'complete' (a human-uploaded
  // or agent-generated document outranks the auto-extracted website context).
  try {
    const { data: existing } = await adminClient
      .from("client_knowledge_documents")
      .select("status")
      .eq("client_id", client_id)
      .eq("document_type_id", "posicionamento")
      .maybeSingle();

    if (!existing || existing.status !== "complete") {
      await adminClient
        .from("client_knowledge_documents")
        .upsert(
          {
            client_id,
            document_type_id: "posicionamento",
            status: "partial",
            source: "onboarding",
            vector_document_id: documentId,
            updated_at: new Date().toISOString(),
          },
          { onConflict: "client_id,document_type_id" },
        );
    }
  } catch (err) {
    console.warn("[website-context-builder] Knowledge document upsert failed:", err);
  }

  // ── Step 4: Extract structured context from website + onboarding state ────
  const structuredContext = buildStructuredContext(pages, onboarding_state);

  // ── Step 4b: Persist structured context JSON ──────────────────────────────
  const structuredStoragePath = `onboarding/context_${client_id}.json`;
  const structuredJson = JSON.stringify(structuredContext, null, 2);
  await adminClient.storage
    .from("knowledge-base")
    .upload(structuredStoragePath, new TextEncoder().encode(structuredJson), {
      contentType: "application/json",
      upsert: true,
    });

  // ── Step 5: Fire process-document to chunk + embed ───────────────────────
  const processPayload = {
    document_id: documentId,
    storage_path: storagePath,
    client_id,
    file_name: fileName,
    file_type: "md",
    target_tokens: 150,
    skip_metadata_enrichment: true,
  };

  // Fire-and-forget: we return immediately; embedding happens in background
  const processUrl = `${SUPABASE_URL}/functions/v1/process-document`;
  EdgeRuntime.waitUntil(
    fetch(processUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
      },
      body: JSON.stringify(processPayload),
    }).then(async (r) => {
      if (!r.ok) {
        const txt = await r.text().catch(() => "");
        console.warn(`[website-context-builder] process-document responded ${r.status}: ${txt}`);
      } else {
        console.log(`[website-context-builder] process-document triggered for doc ${documentId}`);
      }
    }).catch((err) => {
      console.warn("[website-context-builder] process-document fire failed:", err);
    }),
  );

  return json({
    document_id: documentId,
    pages_crawled: pages.length,
    storage_path: storagePath,
    structured_context: structuredContext,
    structured_storage_path: structuredStoragePath,
  });
});
