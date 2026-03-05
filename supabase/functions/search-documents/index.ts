// supabase/functions/search-documents/index.ts
// Retrieval endpoint — embeds query text and searches vector_db.document_chunks.
// Called by Python backend (service_role key) or frontend (user JWT).
//
// Request:  POST { query, client_id, match_count?, match_threshold? }
// Response: { results: [{ id, document_id, content, metadata, similarity }] }

import postgres from "https://deno.land/x/postgresjs@v3.4.5/mod.js";

const DB_URL = Deno.env.get("SUPABASE_DB_URL")!;

// @ts-ignore — Supabase Edge Runtime built-in AI
const session = new Supabase.ai.Session("gte-small");

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
            match_threshold = 0.5,
            document_ids = null,
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

        // 1. Embed query text using gte-small (same model as storage)
        const queryEmbedding = await session.run(query, {
            mean_pool: true,
            normalize: true,
        });

        const embeddingStr = `[${Array.from(queryEmbedding).join(",")}]`;

        // 2. Build document_ids array parameter (NULL if not provided)
        const docIdsParam = document_ids && Array.isArray(document_ids) && document_ids.length > 0
            ? `{${document_ids.join(",")}}`
            : null;

        // 3. Call vector_db.match_documents RPC via direct Postgres
        const results = await sql`
      SELECT *
      FROM vector_db.match_documents(
        ${client_id}::uuid,
        ${embeddingStr}::vector::halfvec(384),
        ${match_count}::int,
        ${match_threshold}::float,
        ${docIdsParam}::uuid[]
      )
    `;

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
