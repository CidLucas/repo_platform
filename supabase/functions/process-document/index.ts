// supabase/functions/process-document/index.ts
// Self-contained document processing pipeline — downloads file, parses text,
// chunks, generates embeddings (Cohere), enriches metadata (Ollama Cloud LLM), and inserts
// everything into document_chunks in a single transaction.
//
// No pgmq, no cron, no separate embed/enrich-metadata Edge Functions.
// Document is fully searchable the moment this EF returns 200.
//
// Request: POST { document_id, storage_path, client_id, file_name, file_type }
// Response: 200 OK { document_id, status: "completed", chunk_count }

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import postgres from "https://deno.land/x/postgresjs@v3.4.5/mod.js";
// pdf-parse: import from lib/ subpath to skip test-file loading that breaks in Deno
import pdfParse from "npm:pdf-parse@1.1.1/lib/pdf-parse.js";
import mammoth from "npm:mammoth@1.8.0";
import XLSX from "npm:xlsx@0.18.5";
import JSZip from "npm:jszip@3.10.1";
import { corsHeaders, json } from "../_shared/cors.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
if (!SUPABASE_SERVICE_ROLE_KEY) throw new Error("SUPABASE_SERVICE_ROLE_KEY nao configurada");
const DB_URL = Deno.env.get("SUPABASE_DB_URL")!;
if (!SUPABASE_URL) throw new Error("SUPABASE_URL nao configurada");

// ── Knowledge Document Category Mapping ────────────────────────────────────
// Maps vector_db.documents.category values → knowledge_document_types.id.
// Used to auto-populate client_knowledge_documents when a file is processed.
// Only recognised categories are mapped; unknown ones are silently skipped.
const CATEGORY_TO_DOC_TYPE: Record<string, string> = {
  rh:           "folha_pagamento",
  folha:        "folha_pagamento",
  contrato:     "contrato_fornecimento",
  nf:           "fatura_nota_fiscal",
  fiscal:       "fatura_nota_fiscal",
  organograma:  "organograma",
  producao:     "ficha_tecnica",
  receita:      "ficha_tecnica",
  dre:          "dre_mensal",
  financeiro:   "fluxo_caixa_diario",
  catalogo:     "catalogo_produtos",
  preco:        "politica_preco",
};

// ── Token Estimation ────────────────────────────────────────
// Cohere embed-multilingual-light-v3.0 uses a BPE tokenizer. We approximate
// token count using a heuristic: ~4 chars per token for Latin text, ~2 for
// CJK/complex scripts. This avoids shipping a full tokenizer in the Edge
// Function while staying safely within the model's 512-token limit.

function estimateTokens(text: string): number {
    // Count CJK-heavy characters (each roughly 1 token)
    const cjk = text.match(/[\u3000-\u9fff\uac00-\ud7af]/g)?.length ?? 0;
    const rest = text.length - cjk;
    // Latin/mixed text averages ~3.5 chars/token; CJK ~1 char/token
    return Math.ceil(rest / 3.5) + cjk;
}

// ── Chunking Algorithm ──────────────────────────────────────

interface Chunk {
    text: string;
    index: number;
    metadata: Record<string, unknown>;
}

// Token-aware limits (embed-multilingual-light-v3.0 max_seq_length = 512 tokens)
// Default is 400. Callers can override via request body `target_tokens` (max 500).
// Structured docs (e.g. context reports) benefit from smaller values (~100 tokens)
// for more granular retrieval — roughly one business section per chunk.
const DEFAULT_TARGET_TOKENS = 400;
const OVERLAP_SENTENCES = 2; // number of trailing sentences to overlap

// ── Embedding (Cohere) ──────────────────────────────────────
const CO_API_KEY = Deno.env.get("CO_API_KEY")!;
if (!CO_API_KEY) throw new Error("CO_API_KEY nao configurada");
const COHERE_EMBEDDING_MODEL = "embed-multilingual-light-v3.0"; // 384 dims, matches halfvec(384), supports Portuguese
const EMBEDDING_DIMENSIONS = 384; // matches halfvec(384) column

// Ollama Cloud config — used ONLY for metadata enrichment LLM
const OLLAMA_CLOUD_BASE_URL = Deno.env.get("OLLAMA_CLOUD_BASE_URL") ?? "https://ollama.com";
const OLLAMA_CLOUD_API_KEY = Deno.env.get("OLLAMA_CLOUD_API_KEY")!;

async function generateEmbeddings(texts: string[]): Promise<number[][]> {
    // Cohere v2/embed accepts max 96 texts per call
    const BATCH_SIZE = 96;
    const allEmbeddings: number[][] = [];

    for (let i = 0; i < texts.length; i += BATCH_SIZE) {
        const batch = texts.slice(i, i + BATCH_SIZE);
        const response = await fetch("https://api.cohere.com/v2/embed", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${CO_API_KEY}`,
            },
            body: JSON.stringify({
                model: COHERE_EMBEDDING_MODEL,
                texts: batch,
                input_type: "search_document",
                embedding_types: ["float"],
            }),
        });

        if (!response.ok) {
            const errBody = await response.text();
            throw new Error(`Cohere embeddings API error ${response.status}: ${errBody}`);
        }

        const data = await response.json();
        // v2 response: { embeddings: { float: [[...], [...]] } }
        allEmbeddings.push(...data.embeddings.float);
    }

    return allEmbeddings;
}

// ── Metadata Enrichment ─────────────────────────────────────
const LLM_MODEL = Deno.env.get("METADATA_ENRICHMENT_MODEL") ?? "gpt-oss:20b";
const LLM_MAX_TOKENS = Number(Deno.env.get("METADATA_ENRICHMENT_MAX_TOKENS") ?? "500");
const LLM_TEMPERATURE = Number(Deno.env.get("METADATA_ENRICHMENT_TEMPERATURE") ?? "0");

const METADATA_SYSTEM_PROMPT = Deno.env.get("METADATA_ENRICHMENT_SYSTEM_PROMPT") ?? `You are a document metadata classifier. Given a text chunk, extract structured metadata.

Respond in JSON only — no markdown fences, no explanation:
{
  "word_cloud": ["term1", "term2", ...],
  "theme": "one_of_controlled_list",
  "usage_context": "one sentence describing when this content is useful"
}

Rules:
- word_cloud: 10-15 most salient terms from the text (Portuguese or English as found).
- theme: MUST be exactly one of: statistical_analysis, tax_regulation, business_operations, financial_reporting, data_engineering, customer_service, product_knowledge, legal_compliance, market_analysis, human_resources, sales_strategy, operational_procedures, general
- usage_context: A single sentence in the same language as the text.`;

interface EnrichedMetadata {
    word_cloud: string[];
    theme: string;
    usage_context: string;
}

const ALLOWED_THEMES = new Set([
    "statistical_analysis",
    "tax_regulation",
    "business_operations",
    "financial_reporting",
    "data_engineering",
    "customer_service",
    "product_knowledge",
    "legal_compliance",
    "market_analysis",
    "human_resources",
    "sales_strategy",
    "operational_procedures",
    "general",
]);

async function callMetadataLLM(content: string): Promise<EnrichedMetadata> {
    const response = await fetch(
        `${OLLAMA_CLOUD_BASE_URL}/api/chat`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${OLLAMA_CLOUD_API_KEY}`,
            },
            body: JSON.stringify({
                model: LLM_MODEL,
                stream: false,
                options: {
                    temperature: LLM_TEMPERATURE,
                    num_predict: LLM_MAX_TOKENS,
                },
                messages: [
                    { role: "system", content: METADATA_SYSTEM_PROMPT },
                    { role: "user", content: `TEXT:\n${content}` },
                ],
            }),
        }
    );

    if (!response.ok) {
        const errBody = await response.text();
        throw new Error(`Ollama LLM API error ${response.status}: ${errBody}`);
    }

    const data = await response.json();
    const rawContent = data.message.content;

    // Strip markdown fences if present (e.g. ```json ... ```)
    const cleaned = rawContent
        .replace(/^```(?:json)?\s*/i, "")
        .replace(/\s*```\s*$/, "")
        .trim();

    const raw = JSON.parse(cleaned);

    // Validate and sanitize
    const result: EnrichedMetadata = {
        word_cloud: Array.isArray(raw.word_cloud)
            ? raw.word_cloud.filter((t: unknown) => typeof t === "string").slice(0, 15)
            : [],
        theme: ALLOWED_THEMES.has(raw.theme) ? raw.theme : "general",
        usage_context:
            typeof raw.usage_context === "string"
                ? raw.usage_context.slice(0, 500)
                : "",
    };

    return result;
}

function splitIntoSentences(text: string): string[] {
    // Split on multiple boundary types for better chunking:
    // 1. Sentence-ending punctuation (.!?) followed by whitespace
    // 2. Double-newline paragraph breaks
    // 3. Single newlines (common in markdown, bullet lists, section breaks)
    // 4. Markdown headers (# lines)
    // 5. Numbered list items ("1. ", "2. ") at line start
    // 6. Bullet points (- or * at line start)
    return text
        .split(
            /(?<=[.!?])\s+|\n\n+|\n(?=\s*[-*•]\s)|\n(?=\s*\d+[.)\s])|\n(?=#{1,6}\s)|\n/
        )
        .map((s) => s.trim())
        .filter((s) => s.length > 0);
}

function chunkText(
    text: string,
    metadata: Record<string, unknown> = {},
    targetTokens: number = DEFAULT_TARGET_TOKENS
): Chunk[] {
    // 1. Split entire text into sentences
    const sentences = splitIntoSentences(text);
    if (sentences.length === 0) return [];

    const chunks: Chunk[] = [];
    let chunkIndex = 0;
    let charOffset = 0;
    let sentIdx = 0;

    const flushChunk = (chunkText: string) => {
        const trimmed = chunkText.trim();
        if (trimmed.length === 0) return;
        const startIdx = text.indexOf(trimmed, Math.max(0, charOffset - trimmed.length - 100));
        const charStart = startIdx >= 0 ? startIdx : charOffset;
        const charEnd = charStart + trimmed.length;
        chunks.push({
            text: trimmed,
            index: chunkIndex++,
            metadata: {
                ...metadata,
                chunk_index: chunkIndex - 1,
                char_start: charStart,
                char_end: charEnd,
                estimated_tokens: estimateTokens(trimmed),
            },
        });
        charOffset = charEnd;
    };

    while (sentIdx < sentences.length) {
        let currentText = "";
        let currentTokens = 0;
        const startSentIdx = sentIdx;

        // Accumulate sentences until we hit the token target
        while (sentIdx < sentences.length) {
            const candidate = currentText
                ? currentText + " " + sentences[sentIdx]
                : sentences[sentIdx];
            const candidateTokens = estimateTokens(candidate);

            if (candidateTokens > targetTokens && currentText.length > 0) {
                // Adding this sentence would exceed target — flush what we have
                break;
            }

            currentText = candidate;
            currentTokens = candidateTokens;
            sentIdx++;

            // If a single sentence already exceeds the target, flush it alone
            if (currentTokens > targetTokens) {
                break;
            }
        }

        flushChunk(currentText);

        // C2: Sentence-boundary overlap — back up by OVERLAP_SENTENCES
        // so the next chunk starts with the last N sentences of this one
        if (sentIdx < sentences.length) {
            const backtrack = Math.min(OVERLAP_SENTENCES, sentIdx - startSentIdx);
            sentIdx = sentIdx - backtrack;
        }
    }

    // Set total_chunks on all chunk metadata
    const totalChunks = chunks.length;
    for (const chunk of chunks) {
        chunk.metadata.total_chunks = totalChunks;
    }

    return chunks;
}

// ── File Parsers ────────────────────────────────────────────

async function parseTxtMd(data: Uint8Array): Promise<string> {
    return new TextDecoder().decode(data);
}

async function parseCsv(data: Uint8Array): Promise<string> {
    const text = new TextDecoder().decode(data);
    const lines = text.split("\n").filter((l) => l.trim().length > 0);
    if (lines.length === 0) return "";

    const headers = lines[0].split(",").map((h) => h.trim());
    const rows = lines.slice(1);

    return rows
        .map((row) => {
            const values = row.split(",");
            return headers
                .map((h, i) => `${h}: ${(values[i] || "").trim()}`)
                .join(", ");
        })
        .join("\n");
}

async function parseJson(data: Uint8Array): Promise<string> {
    const text = new TextDecoder().decode(data);
    const parsed = JSON.parse(text);

    if (Array.isArray(parsed)) {
        return parsed.map((entry) => JSON.stringify(entry)).join("\n\n");
    }
    if (typeof parsed === "object") {
        return Object.entries(parsed)
            .map(([key, value]) => `${key}: ${JSON.stringify(value)}`)
            .join("\n\n");
    }
    return String(parsed);
}

async function parseXmlHtml(data: Uint8Array): Promise<string> {
    const text = new TextDecoder().decode(data);
    // Strip tags, collapse whitespace
    return text
        .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, "")
        .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, "")
        .replace(/<[^>]+>/g, " ")
        .replace(/&nbsp;/g, " ")
        .replace(/&amp;/g, "&")
        .replace(/&lt;/g, "<")
        .replace(/&gt;/g, ">")
        .replace(/\s+/g, " ")
        .trim();
}

async function parsePdf(data: Uint8Array): Promise<string> {
    console.log(`[process-document] Parsing PDF (${data.byteLength} bytes) with pdf-parse`);
    try {
        const result = await pdfParse(data);
        const text = result?.text || "";
        console.log(`[process-document] pdf-parse result: ${text.length} chars, ${result?.numpages ?? '?'} pages`);
        return text;
    } catch (err) {
        console.error(`[process-document] pdf-parse failed:`, err);
        throw new Error(`PDF parsing failed: ${err instanceof Error ? err.message : String(err)}`);
    }
}

async function parseDocx(data: Uint8Array): Promise<string> {
    const result = await mammoth.extractRawText({ buffer: data });
    return result.value || "";
}

async function parseXlsx(data: Uint8Array): Promise<string> {
    const workbook = XLSX.read(data, { type: "array" });
    const sheets = workbook.SheetNames.map(name => {
        const sheet = workbook.Sheets[name];
        const csv = XLSX.utils.sheet_to_csv(sheet);
        return `## ${name}\n${csv}`;
    });
    return sheets.join("\n\n");
}

async function parsePptx(data: Uint8Array): Promise<string> {
    const zip = await JSZip.loadAsync(data);
    const slideFiles = Object.keys(zip.files)
        .filter(name => /^ppt\/slides\/slide\d+\.xml$/.test(name))
        .sort();
    const slides: string[] = [];
    for (const file of slideFiles) {
        const xml = await zip.files[file].async("text");
        const texts = xml.match(/<a:t[^>]*>([^<]*)<\/a:t>/g) || [];
        const slideText = texts
            .map(t => t.replace(/<[^>]+>/g, ""))
            .join(" ");
        slides.push(slideText);
    }
    return slides.join("\n\n");
}

function getParser(
    fileType: string
): ((data: Uint8Array) => Promise<string>) | null {
    const type = fileType.toLowerCase().replace(/^\./, "");
    switch (type) {
        case "txt":
        case "md":
            return parseTxtMd;
        case "csv":
            return parseCsv;
        case "json":
            return parseJson;
        case "xml":
        case "html":
        case "htm":
            return parseXmlHtml;
        case "pdf":
            return parsePdf;
        case "docx":
            return parseDocx;
        case "xlsx":
            return parseXlsx;
        case "pptx":
            return parsePptx;
        default:
            return null;
    }
}

// ── Document Processing Pipeline ────────────────────────────

async function processDocument(
    documentId: string,
    storagePath: string,
    clientId: string,
    fileName: string,
    fileType: string,
    targetTokens: number = DEFAULT_TARGET_TOKENS,
    skipMetadataEnrichment: boolean = false,
    preExtractedText: string | null = null
) {
    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, {
        auth: { autoRefreshToken: false, persistSession: false },
    });
    const sql = postgres(DB_URL, { prepare: false });

    try {
        console.log(`[process-document] Starting: ${fileName} (type=${fileType}, doc=${documentId})`);

        // Mark as processing
        await sql`
      UPDATE vector_db.documents
      SET status = 'processing', updated_at = now()
      WHERE id = ${documentId}::uuid
    `;

        // Fetch scope + category from parent document (for denormalization into chunks)
        const [docRow] = await sql`
      SELECT scope, category FROM vector_db.documents WHERE id = ${documentId}::uuid
    `;
        const docScope = docRow?.scope ?? 'client';
        const docCategory = docRow?.category ?? null;

        // 1 & 2. Get text: either from pre_extracted_text or by downloading + parsing
        let parsedText: string;
        if (preExtractedText && preExtractedText.trim().length > 0) {
            console.log(`[process-document] Using pre_extracted_text: ${preExtractedText.length} chars (skipping download+parse)`);
            parsedText = preExtractedText;
        } else {
            // 1. Download file from Storage
            console.log(`[process-document] Downloading from storage: ${storagePath}`);
            const { data: fileData, error: downloadError } = await supabase.storage
                .from("knowledge-base")
                .download(storagePath);

            if (downloadError || !fileData) {
                throw new Error(
                    `Failed to download file: ${downloadError?.message || "no data"}`
                );
            }

            const buffer = new Uint8Array(await fileData.arrayBuffer());
            console.log(`[process-document] Downloaded: ${buffer.byteLength} bytes`);

            // 2. Parse file
            const parser = getParser(fileType);
            if (!parser) {
                throw new Error(`Unsupported file type: ${fileType}`);
            }
            console.log(`[process-document] Parsing with ${fileType} parser...`);
            parsedText = await parser(buffer);

            if (!parsedText || parsedText.trim().length === 0) {
                const hint = fileType.toLowerCase() === "pdf"
                    ? " O PDF pode conter apenas imagens/gráficos sem texto extraível. Tente enviar um PDF com texto selecionável."
                    : "";
                throw new Error(
                    `Nenhum conteúdo de texto extraído do arquivo.${hint}`
                );
            }
            console.log(`[process-document] Parsed: ${parsedText.length} chars`);
        }

        // 3. Chunk text
        const chunks = chunkText(parsedText, {
            source_file: fileName,
            file_type: fileType,
            document_id: documentId,
            document_title: fileName.replace(/\.[^.]+$/, ''),
            total_chars: parsedText.length,
        }, targetTokens);
        console.log(`[process-document] Chunked: ${chunks.length} chunks`);

        if (chunks.length === 0) {
            throw new Error("No chunks generated from file content");
        }

        // 4. Generate embeddings for all chunks in a single API call
        console.log(`[process-document] Generating embeddings for ${chunks.length} chunks...`);
        const chunkTexts = chunks.map((c) => c.text);
        const embeddings = await generateEmbeddings(chunkTexts);
        console.log(`[process-document] Embeddings generated: ${embeddings.length}`);

        // 5. Enrich metadata via LLM (5 concurrent calls)
        // Skip when caller sets skip_metadata_enrichment=true (e.g. structured generated docs
        // like context reports where the category/theme are already known).
        const enrichedMetadata: (EnrichedMetadata | null)[] = new Array(chunks.length).fill(null);
        if (skipMetadataEnrichment) {
            console.log(`[process-document] Skipping metadata enrichment (skip_metadata_enrichment=true)`);
        } else {
            console.log(`[process-document] Enriching metadata...`);
            const METADATA_CONCURRENCY = 5;
            for (let i = 0; i < chunks.length; i += METADATA_CONCURRENCY) {
                const batch = chunks.slice(i, i + METADATA_CONCURRENCY);
                const results = await Promise.allSettled(
                    batch.map((chunk) => callMetadataLLM(chunk.text.slice(0, 2000)))
                );
                results.forEach((result, idx) => {
                    if (result.status === "fulfilled") {
                        enrichedMetadata[i + idx] = result.value;
                    } else {
                        console.warn(`[process-document] Metadata enrichment failed for chunk ${i + idx}:`, result.reason);
                        // Non-fatal — chunk will be inserted without enrichment
                    }
                });
            }
            console.log(`[process-document] Metadata enriched: ${enrichedMetadata.filter(Boolean).length}/${chunks.length}`);
        }

        // 6. Transactional insert: delete old chunks, insert new ones with embeddings + metadata
        await sql.begin(async (tx: ReturnType<typeof postgres>) => {
            // Delete existing chunks (re-upload scenario)
            await tx`DELETE FROM vector_db.document_chunks WHERE document_id = ${documentId}::uuid`;

            // Batch insert all chunks with embeddings and metadata
            for (let i = 0; i < chunks.length; i++) {
                const chunk = chunks[i];
                const embedding = embeddings[i];
                const embeddingStr = `[${embedding.join(",")}]`;
                const enriched = enrichedMetadata[i];

                // Compute SHA-256 content hash for deduplication
                const hashBuffer = await crypto.subtle.digest(
                    "SHA-256",
                    new TextEncoder().encode(chunk.text)
                );
                const contentHash = Array.from(new Uint8Array(hashBuffer))
                    .map((b) => b.toString(16).padStart(2, "0"))
                    .join("");

                // client_id is NULL for platform-scoped documents
                const chunkClientId = docScope === 'platform' ? null : clientId;

                // Merge enriched metadata with chunk metadata
                const mergedMetadata = enriched
                    ? { ...chunk.metadata, ...enriched }
                    : chunk.metadata;

                // Extract enriched fields for first-class columns
                // (also kept in JSONB metadata for backward compat)
                const chunkTheme = enriched?.theme ?? null;
                const chunkWordCloud = enriched?.word_cloud?.length
                    ? enriched.word_cloud
                    : null;
                const chunkUsageContext = enriched?.usage_context || null;

                await tx`
                    INSERT INTO vector_db.document_chunks
                        (document_id, client_id, content, chunk_index, metadata, content_hash, scope, category, embedding,
                         theme, word_cloud, usage_context)
                    VALUES (
                        ${documentId}::uuid,
                        ${chunkClientId ? tx`${chunkClientId}::uuid` : tx`NULL`},
                        ${chunk.text},
                        ${chunk.index},
                        ${tx.json(mergedMetadata)},
                        ${contentHash},
                        ${docScope},
                        ${docCategory},
                        ${embeddingStr}::vector::halfvec(384),
                        ${chunkTheme},
                        ${chunkWordCloud},
                        ${chunkUsageContext}
                    )
                    ON CONFLICT (document_id, content_hash) DO UPDATE
                    SET content = EXCLUDED.content,
                        chunk_index = EXCLUDED.chunk_index,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding,
                        theme = EXCLUDED.theme,
                        word_cloud = EXCLUDED.word_cloud,
                        usage_context = EXCLUDED.usage_context
                `;
            }

            // Update document to completed
            await tx`
                UPDATE vector_db.documents
                SET status = 'completed',
                    chunk_count = ${chunks.length},
                    updated_at = now()
                WHERE id = ${documentId}::uuid
            `;
        });

        console.log(
            `[process-document] Completed: ${fileName}, ${chunks.length} chunks inserted with embeddings + metadata`
        );

        // ── Best-effort: upsert knowledge document inventory ──────────────────
        // Map vector_db.documents.category → knowledge_document_types.id so
        // coverage scores update automatically when files are processed.
        if (docCategory) {
          const docTypeId = CATEGORY_TO_DOC_TYPE[docCategory.toLowerCase()] ?? null;
          if (docTypeId) {
            await supabase
              .from("client_knowledge_documents")
              .upsert(
                {
                  client_id: clientId,
                  document_type_id: docTypeId,
                  status: "complete",
                  source: "upload",
                  vector_document_id: documentId,
                  updated_at: new Date().toISOString(),
                },
                { onConflict: "client_id,document_type_id" },
              )
              .then(({ error }) => {
                if (error) {
                  console.warn("[process-document] Knowledge document upsert failed:", error.message);
                }
              });
          }
        }
    } catch (err) {
        console.error(`[process-document] Error processing ${fileName}:`, err);
        // Mark document as failed
        await sql`
      UPDATE vector_db.documents
      SET status = 'failed',
          error_message = ${err instanceof Error ? err.message : String(err)
            },
          updated_at = now()
      WHERE id = ${documentId}::uuid
    `.catch((e: Error) =>
                console.error("[process-document] Failed to update error status:", e)
            );
    } finally {
        await sql.end();
    }
}

// ── Safety: Catch Deno Isolate Termination ─────────────────

function catchUnload(): Promise<never> {
    return new Promise((_resolve, reject) => {
        addEventListener("beforeunload", (ev: Event) => {
            reject(new Error("Deno isolate terminated (beforeunload) — document will be marked failed"));
        });
    });
}

// ── HTTP Handler ────────────────────────────────────────────

Deno.serve(async (req: Request) => {
    // CORS preflight
    if (req.method === "OPTIONS") {
        return new Response("ok", { headers: corsHeaders });
    }

    try {
        const body = await req.json();
        const { document_id, storage_path, client_id, file_name, file_type, target_tokens, skip_metadata_enrichment, pre_extracted_text = null } = body;

        // Validate required fields
        if (!document_id || !storage_path || !client_id || !file_name || !file_type) {
            return json(
                { error: "Missing required fields: document_id, storage_path, client_id, file_name, file_type" },
                400,
            );
        }

        // Validate file type — skip parser check when pre_extracted_text is provided
        if (!pre_extracted_text) {
            const parser = getParser(file_type);
            if (!parser) {
                return json(
                    { error: `Unsupported file type for direct processing: ${file_type}. Upload complex files (PPTX, XLSX, scanned PDFs) via the document intelligence tools.` },
                    422,
                );
            }
        }

        // Clamp target_tokens: must be between 50 and 500 (Cohere max = 512)
        const resolvedTargetTokens = typeof target_tokens === "number"
            ? Math.min(Math.max(Math.round(target_tokens), 50), 500)
            : DEFAULT_TARGET_TOKENS;
        const resolvedSkipEnrichment = skip_metadata_enrichment === true;

        // Process synchronously — parse, chunk, embed, enrich, insert in one call
        console.log(`[process-document] Starting processing for ${file_name} (target_tokens=${resolvedTargetTokens})`);
        await Promise.race([
            processDocument(document_id, storage_path, client_id, file_name, file_type, resolvedTargetTokens, resolvedSkipEnrichment, pre_extracted_text),
            catchUnload(),
        ]);
        console.log(`[process-document] Completed processing for ${file_name}`);

        return json({
            document_id,
            status: "completed",
            chunk_count: 0, // actual count already persisted in DB
            message: "Document processed, embedded, and ready for search.",
        });
    } catch (err) {
        console.error("[process-document] Handler error:", err);
        return json(
            { error: "Internal error", details: err instanceof Error ? err.message : String(err) },
            500,
        );
    }
});
