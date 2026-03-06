// supabase/functions/embed/index.ts
// Auto-embed worker — processes batched embedding jobs from pgmq queue.
// Called on-demand by process-document via util.process_embeddings() → pg_net.
// Pattern: follows Supabase automatic-embeddings docs.
// See: https://supabase.com/docs/guides/ai/automatic-embeddings
//
// Dead-letter queue support — tracks retry count per job.
// After MAX_RETRIES failures, jobs are moved to 'embedding_jobs_dlq'
// and the parent document is marked 'partially_failed'.

import postgres from "https://deno.land/x/postgresjs@v3.4.5/mod.js";

const DB_URL = Deno.env.get("SUPABASE_DB_URL")!;
const MAX_RETRIES = 3;

// Lazy-init: creating the session at module scope caused 546 (boot resource
// limit exceeded) errors. Initialise on first use inside the handler instead.
// @ts-ignore — Supabase Edge Runtime built-in AI
let _session: InstanceType<typeof Supabase.ai.Session> | null = null;
function getSession() {
    if (!_session) {
        // @ts-ignore
        _session = new Supabase.ai.Session("gte-small");
    }
    return _session;
}

interface EmbeddingJob {
    id: number;
    schema: string;
    table: string;
    contentFunction: string;
    embeddingColumn: string;
    jobId: number;
    retryCount?: number;
}

Deno.serve(async (req: Request) => {
    try {
        const jobs: EmbeddingJob[] = await req.json();

        if (!Array.isArray(jobs) || jobs.length === 0) {
            return new Response(
                JSON.stringify({ error: "Expected non-empty array of embedding jobs" }),
                { status: 400, headers: { "Content-Type": "application/json" } }
            );
        }

        const sql = postgres(DB_URL, { prepare: false });
        const completed: number[] = [];
        const failed: { jobId: number; error: string }[] = [];
        const deadLettered: number[] = [];

        try {
            for (const job of jobs) {
                const retryCount = job.retryCount ?? 0;

                try {
                    // 1. Fetch content from the source table using the content function
                    const rows = await sql`
            SELECT ${sql(job.contentFunction)}(t) AS content
            FROM ${sql(job.schema)}.${sql(job.table)} t
            WHERE t.id = ${job.id}
          `;

                    if (!rows || rows.length === 0) {
                        console.warn(`[embed] No row found for id=${job.id} in ${job.schema}.${job.table}`);
                        // Still delete from queue — the row was probably deleted
                        completed.push(job.jobId);
                        continue;
                    }

                    const content = rows[0].content;

                    if (!content || content.trim().length === 0) {
                        console.warn(`[embed] Empty content for id=${job.id}, skipping embed`);
                        completed.push(job.jobId);
                        continue;
                    }

                    // 2. Generate embedding using built-in gte-small (lazy session)
                    const embedding = await getSession().run(content, {
                        mean_pool: true,
                        normalize: true,
                    });

                    // 3. Convert to Postgres array format
                    const embeddingStr = `[${Array.from(embedding).join(",")}]`;

                    // 4. Update the embedding column
                    await sql`
            UPDATE ${sql(job.schema)}.${sql(job.table)}
            SET ${sql(job.embeddingColumn)} = ${embeddingStr}::vector::halfvec(384)
            WHERE id = ${job.id}
          `;

                    // 4b. Check if all chunks for this document are now embedded;
                    //     if so, mark the parent document as 'completed'
                    if (job.table === "document_chunks") {
                        await sql`
              UPDATE vector_db.documents d
              SET status = 'completed', updated_at = now()
              WHERE d.id = (
                SELECT document_id FROM vector_db.document_chunks WHERE id = ${job.id}
              )
              AND NOT EXISTS (
                SELECT 1 FROM vector_db.document_chunks dc
                WHERE dc.document_id = d.id AND dc.embedding IS NULL
              )
              AND d.status != 'completed'
            `;
                    }

                    // 5. Track success
                    completed.push(job.jobId);
                } catch (jobErr) {
                    const nextRetry = retryCount + 1;
                    console.error(`[embed] Failed job id=${job.id} (attempt ${nextRetry}/${MAX_RETRIES}):`, jobErr);

                    if (nextRetry >= MAX_RETRIES) {
                        // Move to dead-letter queue
                        console.warn(`[embed] Job id=${job.id} exhausted retries, moving to DLQ`);
                        try {
                            await sql`
                SELECT pgmq.send(
                  'embedding_jobs_dlq',
                  ${sql.json({
                                id: job.id,
                                schema: job.schema,
                                table: job.table,
                                contentFunction: job.contentFunction,
                                embeddingColumn: job.embeddingColumn,
                                retryCount: nextRetry,
                                lastError: jobErr instanceof Error ? jobErr.message : String(jobErr),
                                failedAt: new Date().toISOString(),
                            })}::jsonb
                )
              `;

                            // Mark parent document as partially_failed
                            if (job.table === "document_chunks") {
                                await sql`
                  UPDATE vector_db.documents d
                  SET status = 'partially_failed', updated_at = now()
                  WHERE d.id = (
                    SELECT document_id FROM vector_db.document_chunks WHERE id = ${job.id}
                  )
                  AND d.status NOT IN ('completed', 'failed')
                `;
                            }
                        } catch (dlqErr) {
                            console.error(`[embed] Failed to send job ${job.id} to DLQ:`, dlqErr);
                        }
                        deadLettered.push(job.jobId);
                        // Delete from main queue even on DLQ — it's been transferred
                        completed.push(job.jobId);
                    } else {
                        // Re-queue with incremented retry count
                        try {
                            await sql`
                SELECT pgmq.send(
                  'embedding_jobs',
                  ${sql.json({
                                id: job.id,
                                schema: job.schema,
                                table: job.table,
                                contentFunction: job.contentFunction,
                                embeddingColumn: job.embeddingColumn,
                                retryCount: nextRetry,
                            })}::jsonb
                )
              `;
                        } catch (requeueErr) {
                            console.error(`[embed] Failed to re-queue job ${job.id}:`, requeueErr);
                        }
                        // Delete original message (re-queued with new msg_id)
                        completed.push(job.jobId);
                    }

                    failed.push({
                        jobId: job.jobId,
                        error: jobErr instanceof Error ? jobErr.message : String(jobErr),
                    });
                }
            }

            // 6. Delete completed jobs from pgmq queue
            if (completed.length > 0) {
                for (const jobId of completed) {
                    await sql`SELECT pgmq.delete('embedding_jobs', ${jobId})`;
                }
            }
        } finally {
            await sql.end();
        }

        return new Response(
            JSON.stringify({
                processed: completed.length - deadLettered.length,
                failed: failed.length,
                dead_lettered: deadLettered.length,
                errors: failed,
            }),
            {
                status: 200,
                headers: { "Content-Type": "application/json" },
            }
        );
    } catch (err) {
        console.error("[embed] Handler error:", err);
        return new Response(
            JSON.stringify({
                error: "Internal error",
                details: err instanceof Error ? err.message : String(err),
            }),
            { status: 500, headers: { "Content-Type": "application/json" } }
        );
    }
});
