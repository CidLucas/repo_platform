// supabase/functions/embed/index.ts
// Auto-embed worker — processes batched embedding jobs from pgmq queue.
// Called internally by pg_net via the pg_cron scheduled job.
// Pattern: follows Supabase automatic-embeddings docs exactly.
// See: https://supabase.com/docs/guides/ai/automatic-embeddings

import postgres from "https://deno.land/x/postgresjs@v3.4.5/mod.js";

const DB_URL = Deno.env.get("SUPABASE_DB_URL")!;

// @ts-ignore — Supabase Edge Runtime built-in AI
const session = new Supabase.ai.Session("gte-small");

interface EmbeddingJob {
    id: number;
    schema: string;
    table: string;
    contentFunction: string;
    embeddingColumn: string;
    jobId: number;
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

        try {
            for (const job of jobs) {
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

                    // 2. Generate embedding using built-in gte-small
                    const embedding = await session.run(content, {
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
                    console.error(`[embed] Failed job id=${job.id}:`, jobErr);
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
                processed: completed.length,
                failed: failed.length,
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
