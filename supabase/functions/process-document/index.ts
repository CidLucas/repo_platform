// supabase/functions/process-document/index.ts
// Lightweight file parser — downloads file, parses text, chunks, and inserts
// into document_chunks (WITHOUT embedding). Embeddings are handled asynchronously
// by the pgmq trigger (queue_embedding_if_null) → pg_cron → embed Edge Function.
//
// Request: POST { document_id, storage_path, client_id, file_name, file_type }
// Response: 200 OK { document_id, status: "processing", chunk_count }

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import postgres from "https://deno.land/x/postgresjs@v3.4.5/mod.js";
// pdf-parse: import from lib/ subpath to skip test-file loading that breaks in Deno
import pdfParse from "npm:pdf-parse@1.1.1/lib/pdf-parse.js";
import mammoth from "npm:mammoth@1.8.0";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const DB_URL = Deno.env.get("SUPABASE_DB_URL")!;

const corsHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers":
        "authorization, x-client-info, apikey, content-type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
};

// ── Token Estimation ────────────────────────────────────────
// gte-small uses a BPE tokenizer. We approximate token count using a
// heuristic: ~4 chars per token for Latin text, ~2 for CJK/complex scripts.
// This avoids shipping a full tokenizer in the Edge Function while staying
// safely within the model's 512-token limit.

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

// Token-aware limits (gte-small max_seq_length = 512 tokens)
const TARGET_TOKENS = 400; // target tokens per chunk (leaves headroom for overlap + special tokens)
const OVERLAP_SENTENCES = 2; // number of trailing sentences to overlap

function splitIntoSentences(text: string): string[] {
    // Split on sentence boundaries: period/exclamation/question followed by
    // whitespace, OR double-newline paragraph breaks.
    return text
        .split(/(?<=[.!?])\s+|(?:\n\n+)/)
        .map((s) => s.trim())
        .filter((s) => s.length > 0);
}

function chunkText(
    text: string,
    metadata: Record<string, unknown> = {}
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

            if (candidateTokens > TARGET_TOKENS && currentText.length > 0) {
                // Adding this sentence would exceed target — flush what we have
                break;
            }

            currentText = candidate;
            currentTokens = candidateTokens;
            sentIdx++;

            // If a single sentence already exceeds the target, flush it alone
            if (currentTokens > TARGET_TOKENS) {
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
        default:
            return null;
    }
}

// ── Background Processing ───────────────────────────────────

async function processDocument(
    documentId: string,
    storagePath: string,
    clientId: string,
    fileName: string,
    fileType: string
) {
    const supabase = createClient(SUPABASE_URL, SERVICE_ROLE_KEY, {
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
        const parsedText = await parser(buffer);

        if (!parsedText || parsedText.trim().length === 0) {
            const hint = fileType.toLowerCase() === "pdf"
                ? " O PDF pode conter apenas imagens/gráficos sem texto extraível. Tente enviar um PDF com texto selecionável."
                : "";
            throw new Error(
                `Nenhum conteúdo de texto extraído do arquivo.${hint}`
            );
        }
        console.log(`[process-document] Parsed: ${parsedText.length} chars`);

        // 3. Chunk text
        const chunks = chunkText(parsedText, {
            source_file: fileName,
            file_type: fileType,
            document_id: documentId,
            document_title: fileName.replace(/\.[^.]+$/, ''),
            total_chars: parsedText.length,
        });
        console.log(`[process-document] Chunked: ${chunks.length} chunks`);

        if (chunks.length === 0) {
            throw new Error("No chunks generated from file content");
        }

        // 4. Delete existing chunks for this document (re-upload scenario)
        //    Then insert fresh chunks. Deduplication is handled by content_hash
        //    unique constraint per (document_id, content_hash).
        await sql`
      DELETE FROM vector_db.document_chunks
      WHERE document_id = ${documentId}::uuid
    `;

        // 5. Insert chunks WITHOUT embedding — the trigger
        //    `embed_on_insert` fires and queues each chunk
        //    into pgmq → pg_cron → embed Edge Function
        for (const chunk of chunks) {
            // Compute SHA-256 content hash for deduplication
            const hashBuffer = await crypto.subtle.digest(
                "SHA-256",
                new TextEncoder().encode(chunk.text)
            );
            const contentHash = Array.from(new Uint8Array(hashBuffer))
                .map((b) => b.toString(16).padStart(2, "0"))
                .join("");

            await sql`
        INSERT INTO vector_db.document_chunks
          (document_id, client_id, content, chunk_index, metadata, content_hash)
        VALUES (
          ${documentId}::uuid,
          ${clientId}::uuid,
          ${chunk.text},
          ${chunk.index},
          ${sql.json(chunk.metadata)},
          ${contentHash}
        )
        ON CONFLICT (document_id, content_hash) DO UPDATE
        SET content = EXCLUDED.content,
            chunk_index = EXCLUDED.chunk_index,
            metadata = EXCLUDED.metadata,
            embedding = NULL
      `;
        }

        // 5. Update document: status=processing (will become 'completed'
        //    when the embed function finishes all chunks), set chunk_count
        await sql`
      UPDATE vector_db.documents
      SET status = 'processing',
          chunk_count = ${chunks.length},
          updated_at = now()
      WHERE id = ${documentId}::uuid
    `;

        console.log(
            `[process-document] Completed parsing: ${fileName}, ${chunks.length} chunks inserted (embedding queued via pgmq)`
        );
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

// ── HTTP Handler ────────────────────────────────────────────

Deno.serve(async (req: Request) => {
    // CORS preflight
    if (req.method === "OPTIONS") {
        return new Response("ok", { headers: corsHeaders });
    }

    try {
        const body = await req.json();
        const { document_id, storage_path, client_id, file_name, file_type } = body;

        // Validate required fields
        if (!document_id || !storage_path || !client_id || !file_name || !file_type) {
            return new Response(
                JSON.stringify({
                    error:
                        "Missing required fields: document_id, storage_path, client_id, file_name, file_type",
                }),
                {
                    status: 400,
                    headers: { ...corsHeaders, "Content-Type": "application/json" },
                }
            );
        }

        // Validate file type is supported for simple processing
        const parser = getParser(file_type);
        if (!parser) {
            return new Response(
                JSON.stringify({
                    error: `Unsupported file type for simple processing: ${file_type}. Use file_upload_api for complex files.`,
                }),
                {
                    status: 422,
                    headers: { ...corsHeaders, "Content-Type": "application/json" },
                }
            );
        }

        // Process synchronously — parsing + chunking is fast (no embedding)
        console.log(`[process-document] Starting processing for ${file_name}`);
        await processDocument(document_id, storage_path, client_id, file_name, file_type);
        console.log(`[process-document] Completed processing for ${file_name}`);

        return new Response(
            JSON.stringify({
                document_id,
                status: "processing",
                message:
                    "Document parsed and chunked. Embeddings are being generated asynchronously.",
            }),
            {
                status: 200,
                headers: { ...corsHeaders, "Content-Type": "application/json" },
            }
        );
    } catch (err) {
        console.error("[process-document] Handler error:", err);
        return new Response(
            JSON.stringify({
                error: "Internal error",
                details: err instanceof Error ? err.message : String(err),
            }),
            {
                status: 500,
                headers: { ...corsHeaders, "Content-Type": "application/json" },
            }
        );
    }
});
