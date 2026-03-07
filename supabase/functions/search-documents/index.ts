// supabase/functions/search-documents/index.ts
// Retrieval endpoint — embeds query text and searches vector_db.document_chunks.
// Called by Python backend (service_role key) or frontend (user JWT).
//
// Supports two modes:
//   - semantic (legacy): pure cosine-similarity via match_documents RPC
//   - hybrid (default):  semantic + keyword fusion via hybrid_match_documents RPC
//
// Request:  POST { query, client_id, match_count?, match_threshold?,
//                  search_mode?, fusion_strategy?, keyword_weight?, vector_weight?,
//                  scope?, categories?, document_ids? }
// Response: { results: [{ id, document_id, content, metadata, similarity,
//                         keyword_score?, combined_score?, scope?, category? }] }
//
// Uses Cohere embed-multilingual-light-v3.0 (384 dimensions) for query embedding,
// matching the process-document EF that generates stored vectors.

import postgres from "https://deno.land/x/postgresjs@v3.4.5/mod.js";

const DB_URL = Deno.env.get("SUPABASE_DB_URL")!;
const CO_API_KEY = Deno.env.get("CO_API_KEY")!;

// ── Embedding Config (Cohere) ──────────────────────────────
const COHERE_EMBEDDING_MODEL = "embed-multilingual-light-v3.0"; // 384 dims, supports Portuguese
const EMBEDDING_DIMENSIONS = 384; // matches halfvec(384) column

async function generateEmbedding(text: string): Promise<number[]> {
    const response = await fetch("https://api.cohere.com/v2/embed", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${CO_API_KEY}`,
        },
        body: JSON.stringify({
            model: COHERE_EMBEDDING_MODEL,
            texts: [text],
            input_type: "search_query",
            embedding_types: ["float"],
        }),
    });

    if (!response.ok) {
        const errBody = await response.text();
        throw new Error(`Cohere embeddings API error ${response.status}: ${errBody}`);
    }

    const data = await response.json();
    // v2 response: { embeddings: { float: [[...]] } }
    return data.embeddings.float[0];
}

const corsHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers":
        "authorization, x-client-info, apikey, content-type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
};

Deno.serve(async (req: Request) => {
    // CORS preflight
    if (req.method === "OPTIONS") {
        return new Response("ok", { headers: corsHeaders });
    }

    const sql = postgres(DB_URL, { prepare: false });

    try {
        const body = await req.json();
        const {
            query,
            client_id,
            match_count = 5,
            match_threshold = 0.3,
            document_ids = null,
            // Hybrid parameters (Phase 3)
            search_mode = "hybrid",
            fusion_strategy = "rrf",
            keyword_weight = 0.4,
            vector_weight = 0.6,
            scope = ["platform", "client"],
            categories = null,
        } = body;

        // Validate required fields
        if (!query || !client_id) {
            return new Response(
                JSON.stringify({ error: "Missing required fields: query, client_id" }),
                {
                    status: 400,
                    headers: { ...corsHeaders, "Content-Type": "application/json" },
                }
            );
        }

        // Validate search_mode
        const validModes = new Set(["semantic", "hybrid"]);
        if (!validModes.has(search_mode)) {
            return new Response(
                JSON.stringify({ error: `Invalid search_mode: ${search_mode}. Must be 'semantic' or 'hybrid'.` }),
                {
                    status: 400,
                    headers: { ...corsHeaders, "Content-Type": "application/json" },
                }
            );
        }

        // Validate fusion_strategy
        const validStrategies = new Set(["rrf", "weighted"]);
        if (!validStrategies.has(fusion_strategy)) {
            return new Response(
                JSON.stringify({ error: `Invalid fusion_strategy: ${fusion_strategy}. Must be 'rrf' or 'weighted'.` }),
                {
                    status: 400,
                    headers: { ...corsHeaders, "Content-Type": "application/json" },
                }
            );
        }

        // ── Logging: incoming parameters ──────────────────────────
        console.log("[search-documents] Incoming params:", JSON.stringify({
            query: query.slice(0, 120),
            client_id,
            search_mode,
            match_count,
            match_threshold,
            fusion_strategy,
            keyword_weight,
            vector_weight,
            scope,
            categories,
            document_ids,
        }));

        // 1. Embed query text using Cohere multilingual (same model as storage)
        const embedStart = performance.now();
        const queryEmbedding = await generateEmbedding(query);
        const embedMs = (performance.now() - embedStart).toFixed(1);

        // ── Logging: embedding sanity check ─────────────────────
        console.log(`[search-documents] Cohere embed completed in ${embedMs}ms — dims=${queryEmbedding.length}, first5=[${queryEmbedding.slice(0, 5).map((v: number) => v.toFixed(6)).join(", ")}]`);

        const embeddingStr = `[${queryEmbedding.join(",")}]`;

        // 2. Build document_ids array parameter (NULL if not provided)
        const docIdsParam = document_ids && Array.isArray(document_ids) && document_ids.length > 0
            ? `{${document_ids.join(",")}}`
            : null;

        let results;

        const sqlStart = performance.now();

        if (search_mode === "semantic") {
            // ── Legacy path: pure cosine similarity via match_documents ──
            results = await sql`
              SELECT *
              FROM vector_db.match_documents(
                ${client_id}::uuid,
                ${embeddingStr}::vector::halfvec(384),
                ${match_count}::int,
                ${match_threshold}::float,
                ${docIdsParam}::uuid[]
              )
            `;
        } else {
            // ── Hybrid path: semantic + keyword fusion via hybrid_match_documents ──
            // Build scope array param
            const scopeParam = Array.isArray(scope) && scope.length > 0
                ? `{${scope.join(",")}}`
                : "{platform,client}";

            // Build categories array param (NULL if not provided)
            const categoriesParam = categories && Array.isArray(categories) && categories.length > 0
                ? `{${categories.join(",")}}`
                : null;

            results = await sql`
              SELECT *
              FROM vector_db.hybrid_match_documents(
                ${client_id}::uuid,
                ${embeddingStr}::vector::halfvec(384),
                ${query},
                ${match_count}::int,
                ${match_threshold}::float,
                ${docIdsParam}::uuid[],
                ${scopeParam}::text[],
                ${categoriesParam}::text[],
                ${fusion_strategy},
                ${keyword_weight}::float,
                ${vector_weight}::float
              )
            `;
        }

        const sqlMs = (performance.now() - sqlStart).toFixed(1);

        // ── Logging: result diagnostics ─────────────────────────
        console.log(`[search-documents] SQL RPC completed in ${sqlMs}ms — result_count=${results.length}`);
        if (results.length > 0) {
            const top3 = results.slice(0, 3).map((r: Record<string, unknown>, i: number) => ({
                rank: i + 1,
                similarity: r.similarity,
                keyword_score: r.keyword_score,
                combined_score: r.combined_score,
                content_preview: typeof r.content === "string" ? r.content.slice(0, 60) : "",
            }));
            console.log("[search-documents] Top-3 results:", JSON.stringify(top3));
        } else {
            console.warn("[search-documents] EMPTY RESULTS — no chunks matched.", JSON.stringify({
                query: query.slice(0, 120),
                client_id,
                search_mode,
                match_threshold,
            }));
        }

        return new Response(
            JSON.stringify({ results }),
            {
                status: 200,
                headers: { ...corsHeaders, "Content-Type": "application/json" },
            }
        );
    } catch (err) {
        console.error("[search-documents] Handler error:", err);
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
    } finally {
        await sql.end();
    }
});
