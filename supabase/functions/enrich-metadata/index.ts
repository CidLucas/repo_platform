// supabase/functions/enrich-metadata/index.ts
// Metadata enrichment worker — processes batched metadata jobs from pgmq queue.
// Called on-demand by process-document via util.process_metadata() → pg_net.
//
// For each chunk, calls OpenAI gpt-4.1-mini to extract:
//   - word_cloud: top 10-15 salient terms
//   - theme: one of controlled vocabulary values
//   - usage_context: one-sentence description of when the chunk is useful
//
// Merges extracted metadata into existing document_chunks.metadata JSONB.
// On failure after MAX_RETRIES → metadata_jobs_dlq.

import postgres from "https://deno.land/x/postgresjs@v3.4.5/mod.js";

const DB_URL = Deno.env.get("SUPABASE_DB_URL")!;
const OPENAI_API_KEY = Deno.env.get("OPENAI_API_KEY")!;
const MAX_RETRIES = 3;

// ── LLM Config (env-driven, defaults match vizu_llm_service.LLMSettings) ──
const LLM_MODEL = Deno.env.get("METADATA_ENRICHMENT_MODEL") ?? "gpt-4.1-mini";
const LLM_MAX_TOKENS = Number(Deno.env.get("METADATA_ENRICHMENT_MAX_TOKENS") ?? "500");
const LLM_TEMPERATURE = Number(Deno.env.get("METADATA_ENRICHMENT_TEMPERATURE") ?? "0");

// ── System Prompt ──────────────────────────────────────────
// IMPORTANT: This prompt is mirrored in vizu_prompt_management.templates.METADATA_ENRICHMENT_PROMPT.
// Keep both in sync when editing. The Python version is the source of truth for documentation,
// but this Edge Function reads the prompt directly for performance (no cross-language import).
const SYSTEM_PROMPT = Deno.env.get("METADATA_ENRICHMENT_SYSTEM_PROMPT") ?? `You are a document metadata classifier. Given a text chunk, extract structured metadata.

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

interface MetadataJob {
    chunk_id: number;
    document_id: string;
    content: string;
    jobId: number;
    retryCount?: number;
}

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

async function callLLM(content: string): Promise<EnrichedMetadata> {
    const response = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${OPENAI_API_KEY}`,
        },
        body: JSON.stringify({
            model: LLM_MODEL,
            temperature: LLM_TEMPERATURE,
            max_tokens: LLM_MAX_TOKENS,
            response_format: { type: "json_object" },
            messages: [
                { role: "system", content: SYSTEM_PROMPT },
                { role: "user", content: `TEXT:\n${content}` },
            ],
        }),
    });

    if (!response.ok) {
        const errBody = await response.text();
        throw new Error(`OpenAI API error ${response.status}: ${errBody}`);
    }

    const data = await response.json();
    const raw = JSON.parse(data.choices[0].message.content);

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

Deno.serve(async (req: Request) => {
    try {
        const jobs: MetadataJob[] = await req.json();

        if (!Array.isArray(jobs) || jobs.length === 0) {
            return new Response(
                JSON.stringify({ error: "Expected non-empty array of metadata jobs" }),
                { status: 400, headers: { "Content-Type": "application/json" } }
            );
        }

        const sql = postgres(DB_URL, { prepare: false });
        const completed: number[] = [];
        const failed: { jobId: number; error: string }[] = [];
        const deadLettered: number[] = [];

        try {
            // Process jobs in parallel (LLM calls are I/O-bound)
            const MAX_CONCURRENCY = 5;

            async function processJob(job: MetadataJob) {
                const retryCount = job.retryCount ?? 0;

                if (!job.content || job.content.trim().length === 0) {
                    console.warn(
                        `[enrich-metadata] Empty content for chunk_id=${job.chunk_id}, skipping`
                    );
                    completed.push(job.jobId);
                    return;
                }

                // 1. Call LLM to extract metadata
                const enriched = await callLLM(job.content);

                // 2. Merge into existing metadata JSONB
                await sql`
            UPDATE vector_db.document_chunks
            SET metadata = COALESCE(metadata, '{}'::jsonb) || ${sql.json(enriched)}::jsonb
            WHERE id = ${job.chunk_id}
          `;

                // 3. Mark completed
                completed.push(job.jobId);
                console.log(
                    `[enrich-metadata] Enriched chunk_id=${job.chunk_id}, theme=${enriched.theme}`
                );
            }

            async function processWithRetry(job: MetadataJob) {
                try {
                    await processJob(job);
                } catch (jobErr) {
                    const nextRetry = (job.retryCount ?? 0) + 1;
                    console.error(
                        `[enrich-metadata] Failed chunk_id=${job.chunk_id} (attempt ${nextRetry}/${MAX_RETRIES}):`,
                        jobErr
                    );

                    if (nextRetry >= MAX_RETRIES) {
                        console.warn(
                            `[enrich-metadata] chunk_id=${job.chunk_id} exhausted retries, moving to DLQ`
                        );
                        try {
                            await sql`
                SELECT pgmq.send(
                  'metadata_jobs_dlq',
                  ${sql.json({
                                chunk_id: job.chunk_id,
                                document_id: job.document_id,
                                retryCount: nextRetry,
                                lastError:
                                    jobErr instanceof Error ? jobErr.message : String(jobErr),
                                failedAt: new Date().toISOString(),
                            })}::jsonb
                )
              `;
                        } catch (dlqErr) {
                            console.error(
                                `[enrich-metadata] Failed to send chunk_id=${job.chunk_id} to DLQ:`,
                                dlqErr
                            );
                        }
                        deadLettered.push(job.jobId);
                        completed.push(job.jobId);
                    } else {
                        try {
                            await sql`
                SELECT pgmq.send(
                  'metadata_jobs',
                  ${sql.json({
                                chunk_id: job.chunk_id,
                                document_id: job.document_id,
                                content: job.content,
                                retryCount: nextRetry,
                            })}::jsonb
                )
              `;
                            completed.push(job.jobId);
                        } catch (requeueErr) {
                            console.error(
                                `[enrich-metadata] Failed to re-queue chunk_id=${job.chunk_id}:`,
                                requeueErr
                            );
                        }

                        failed.push({
                            jobId: job.jobId,
                            error:
                                jobErr instanceof Error ? jobErr.message : String(jobErr),
                        });
                    }
                }
            }

            // Process in batches of MAX_CONCURRENCY to avoid overwhelming the LLM API
            for (let i = 0; i < jobs.length; i += MAX_CONCURRENCY) {
                const batch = jobs.slice(i, i + MAX_CONCURRENCY);
                await Promise.allSettled(batch.map(processWithRetry));
            }

            // Delete all completed messages from the queue
            if (completed.length > 0) {
                for (const jobId of completed) {
                    await sql`SELECT pgmq.delete('metadata_jobs', ${jobId}::bigint)`;
                }
            }
        } finally {
            await sql.end();
        }

        return new Response(
            JSON.stringify({
                processed: completed.length,
                failed: failed.length,
                deadLettered: deadLettered.length,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
        );
    } catch (err) {
        console.error("[enrich-metadata] Handler error:", err);
        return new Response(
            JSON.stringify({
                error: "Internal error",
                details: err instanceof Error ? err.message : String(err),
            }),
            { status: 500, headers: { "Content-Type": "application/json" } }
        );
    }
});
