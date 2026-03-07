# Upload Pipeline Overhaul — Implementation Plan

> **Created:** 2026-03-06
> **Status:** Ready for implementation
> **Branch:** `feat/inline-embed-pipeline`

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Root Cause Analysis](#2-root-cause-analysis)
3. [Architecture: Before vs After](#3-architecture-before-vs-after)
4. [Session 1 — Rewrite `process-document` EF](#session-1--rewrite-process-document-ef)
5. [Session 2 — Database Migration: Remove Triggers & Crons](#session-2--database-migration-remove-triggers--crons)
6. [Session 3 — Frontend Fixes](#session-3--frontend-fixes)
7. [Session 4 — Fix Stuck Production Data & Deploy](#session-4--fix-stuck-production-data--deploy)
8. [Session 5 — Update Docs & Tests](#session-5--update-docs--tests)
9. [Verification Checklist](#verification-checklist)
10. [Rollback Strategy](#rollback-strategy)

---

## 1. Problem Statement

When uploading a file via the dashboard:

- The loading spinner **never stops** — documents remain stuck in `status = 'processing'` forever.
- Only **some** chunks reach `vector_db.document_chunks`; **zero** get embeddings.
- Edge Function logs show repeated **546** and **500** errors from the `embed` EF.
- The `enrich-metadata` EF also shows intermittent **404** errors (before first deploy).

**Production state as of 2026-03-06:**

| Metric | Value |
|--------|-------|
| Stuck documents (`status = 'processing'`) | 2 (`analisedados_polen.md`, `brpolen_sobre_empresa.txt`) |
| Chunks inserted (total for stuck docs) | 9 (5 + 4) |
| Chunks with embeddings | **0** |
| `embedding_jobs` queue length | **36 messages stuck** (from 153 total) |
| `metadata_jobs` queue length | **9 messages stuck** (from 81 total) |
| `pg_cron` embedding/metadata jobs registered | **0** (migrations never applied to prod) |

---

## 2. Root Cause Analysis

### 2.1 Primary Cause: `embed` EF Boot Resource Limit (HTTP 546)

The `embed` Edge Function imports `postgres.js`, which is a heavy module. When `util.process_embeddings()` fires multiple `pg_net` HTTP requests in rapid succession (one per batch), Supabase tries to boot multiple Deno isolates concurrently. This exceeds the **546 boot resource limit**, causing most invocations to fail before they even start.

**Evidence from logs (chronological, most recent first):**

```
embed → 500  (1118ms)   ← handler error (likely DB connection or OpenAI issue)
embed → 500  (2480ms)
embed → 546  (2628ms)   ← boot resource limit exceeded
embed → 546  (2505ms)
embed → 546  (2723ms)
embed → 546  (3359ms)
embed → 546  (3142ms)
embed → 546  (4130ms)
embed → 500  (468ms)    ← many rapid 500s = cascading failure
embed → 500  (456ms)
embed → 500  (435ms)
...
```

The pattern is clear: `546` → Deno can't boot the isolate. When it occasionally does boot, subsequent `500`s follow (likely DB connection pool exhausted from parallel attempts).

### 2.2 Secondary Cause: Fire-and-Forget Architecture

The current pipeline uses a **fire-and-forget** model:

```
process-document EF
  ├─ INSERT chunks one-by-one (triggers fire → pgmq)
  ├─ SELECT util.process_embeddings()  ← fires pg_net HTTP requests
  ├─ SELECT util.process_metadata()    ← fires pg_net HTTP requests
  └─ RETURN 200 "processing"           ← immediately returns to frontend
```

`pg_net` HTTP calls are **asynchronous and non-blocking** — `process-document` doesn't wait for results. If the `embed` EF fails:

- No retry mechanism exists (cron jobs were never deployed to prod).
- Documents stay `processing` forever.
- The frontend polls indefinitely.
- Messages accumulate in pgmq with no consumer.

### 2.3 Contributing Factors

| Factor | Impact |
|--------|--------|
| **Chunks inserted one-by-one** (no transaction) | If EF times out mid-loop, orphan chunks remain. Not the current blocker, but a latent bug. |
| **Frontend swallows EF errors** (`console.warn` instead of `throw`) | User sees "upload succeeded" even if `process-document` returned 500. |
| **`partially_failed` not in frontend type** | Frontend only knows `pending \| processing \| completed \| failed`. A `partially_failed` document would stop polling but show incorrect UI. |
| **No stuck-document recovery** | No mechanism to detect or recover documents stuck in `processing` for extended periods. |

---

## 3. Architecture: Before vs After

### BEFORE (Current — Broken)

```
Frontend                  process-document EF          pgmq Queue              embed EF (BROKEN)
────────                  ────────────────────         ──────────              ────────────────
uploadFile()
  ├─ Storage.upload()
  ├─ documents.insert(status=processing)
  └─ invoke process-document ──→ download + parse + chunk
                                   │
                                   ├─ INSERT chunks 1-by-1 ──→ TRIGGER ──→ pgmq.send('embedding_jobs')
                                   │                           TRIGGER ──→ pgmq.send('metadata_jobs')
                                   │
                                   ├─ util.process_embeddings() ──→ pg_net ──→ embed EF → 546/500 💥
                                   ├─ util.process_metadata()  ──→ pg_net ──→ enrich-metadata EF
                                   └─ RETURN 200 (fire-and-forget)

pg_cron (NOT DEPLOYED): would retry every 10s/30s — but never registered in prod
```

**Result:** Document stuck in `processing`, 0 embeddings, infinite loading.

### AFTER (Target — Synchronous Inline)

```
Frontend                  process-document EF (does everything)
────────                  ──────────────────────────────────────
uploadFile()
  ├─ Storage.upload()
  ├─ documents.insert(status=processing)
  └─ invoke process-document ──→ download + parse + chunk
                                   │
                                   ├─ OpenAI embeddings API (batch all chunks in 1 call)
                                   ├─ OpenAI chat API (metadata enrichment, 5 concurrent)
                                   │
                                   ├─ BEGIN TRANSACTION
                                   │    DELETE old chunks
                                   │    INSERT ALL chunks WITH embeddings + metadata
                                   │    UPDATE document status='completed', chunk_count=N
                                   │  COMMIT
                                   │
                                   └─ RETURN 200 { status: "completed" }

No pgmq. No pg_net. No cron. No separate embed EF.
```

**Result:** Document fully searchable the moment the EF returns 200.

---

## Session 1 — Rewrite `process-document` EF

**Goal:** Make `process-document` a self-contained pipeline that downloads, parses, chunks, embeds, enriches metadata, and inserts — all in one synchronous call.

**File:** `supabase/functions/process-document/index.ts` (473 lines → ~500 lines)

### Task 1.1 — Add Embedding Generation Function

Copy the `generateEmbeddings()` function from `supabase/functions/embed/index.ts` (lines 22-48) into `process-document/index.ts`. It's a stateless utility — just an OpenAI API call.

```typescript
// ── Embedding ───────────────────────────────────────────────
const OPENAI_API_KEY = Deno.env.get("OPENAI_API_KEY")!;
const EMBEDDING_MODEL = "text-embedding-3-small";
const EMBEDDING_DIMENSIONS = 384;

async function generateEmbeddings(texts: string[]): Promise<number[][]> {
    const response = await fetch("https://api.openai.com/v1/embeddings", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${OPENAI_API_KEY}`,
        },
        body: JSON.stringify({
            model: EMBEDDING_MODEL,
            dimensions: EMBEDDING_DIMENSIONS,
            input: texts,
        }),
    });
    if (!response.ok) {
        const errBody = await response.text();
        throw new Error(`OpenAI embeddings API error ${response.status}: ${errBody}`);
    }
    const data = await response.json();
    return data.data
        .sort((a: { index: number }, b: { index: number }) => a.index - b.index)
        .map((item: { embedding: number[] }) => item.embedding);
}
```

**Where to add:** After the `OVERLAP_SENTENCES` constant (~line 50), before `splitIntoSentences`.

**Env var needed:** `OPENAI_API_KEY` — already set in Supabase secrets (used by existing `embed` EF). Verify with `supabase secrets list`.

### Task 1.2 — Add Metadata Enrichment Function

Copy the `callLLM()` function and its config constants from `supabase/functions/enrich-metadata/index.ts` (lines 19-109) into `process-document/index.ts`.

```typescript
// ── Metadata Enrichment ─────────────────────────────────────
const LLM_MODEL = Deno.env.get("METADATA_ENRICHMENT_MODEL") ?? "gpt-4.1-mini";
const LLM_MAX_TOKENS = Number(Deno.env.get("METADATA_ENRICHMENT_MAX_TOKENS") ?? "500");
const LLM_TEMPERATURE = Number(Deno.env.get("METADATA_ENRICHMENT_TEMPERATURE") ?? "0");

const METADATA_SYSTEM_PROMPT = `You are a document metadata classifier...`; // copy from enrich-metadata

const ALLOWED_THEMES = new Set([...]);  // copy from enrich-metadata

async function callMetadataLLM(content: string): Promise<EnrichedMetadata> { ... }
```

**Where to add:** Right after `generateEmbeddings()`.

### Task 1.3 — Rewrite `processDocument()` Core Logic

Replace the section from the chunk insertion loop through the `util.process_*` calls (approximately lines 320–385) with:

#### Step A: Generate embeddings in batch

```typescript
// 4. Generate embeddings for all chunks in a single API call
console.log(`[process-document] Generating embeddings for ${chunks.length} chunks...`);
const chunkTexts = chunks.map((c) => c.text);
const embeddings = await generateEmbeddings(chunkTexts);
console.log(`[process-document] Embeddings generated: ${embeddings.length}`);
```

OpenAI's embeddings API accepts arrays up to 2048 inputs. Our chunks are small files (<100KB → typically 5-30 chunks), so this will always be a single API call.

#### Step B: Enrich metadata in parallel (concurrency-limited)

```typescript
// 5. Enrich metadata via LLM (5 concurrent calls)
console.log(`[process-document] Enriching metadata...`);
const METADATA_CONCURRENCY = 5;
const enrichedMetadata: (EnrichedMetadata | null)[] = new Array(chunks.length).fill(null);

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
```

Metadata enrichment is **best-effort** — if an LLM call fails, the chunk is still inserted with its embedding. No document failure.

#### Step C: Transactional insert with embeddings + metadata

```typescript
// 6. Transactional insert: delete old chunks, insert new ones with embeddings
await sql.begin(async (tx) => {
    // Delete existing chunks (re-upload scenario)
    await tx`DELETE FROM vector_db.document_chunks WHERE document_id = ${documentId}::uuid`;

    // Batch insert all chunks with embeddings and metadata
    for (let i = 0; i < chunks.length; i++) {
        const chunk = chunks[i];
        const embedding = embeddings[i];
        const embeddingStr = `[${embedding.join(",")}]`;
        const enriched = enrichedMetadata[i];

        // Compute content hash
        const hashBuffer = await crypto.subtle.digest(
            "SHA-256",
            new TextEncoder().encode(chunk.text)
        );
        const contentHash = Array.from(new Uint8Array(hashBuffer))
            .map((b) => b.toString(16).padStart(2, "0"))
            .join("");

        const chunkClientId = docScope === "platform" ? null : clientId;

        // Merge enriched metadata with chunk metadata
        const mergedMetadata = enriched
            ? { ...chunk.metadata, ...enriched }
            : chunk.metadata;

        await tx`
            INSERT INTO vector_db.document_chunks
              (document_id, client_id, content, embedding, chunk_index, metadata, content_hash, scope, category)
            VALUES (
              ${documentId}::uuid,
              ${chunkClientId ? tx`${chunkClientId}::uuid` : tx`NULL`},
              ${chunk.text},
              ${embeddingStr}::vector::halfvec(384),
              ${chunk.index},
              ${tx.json(mergedMetadata)},
              ${contentHash},
              ${docScope},
              ${docCategory}
            )
            ON CONFLICT (document_id, content_hash) DO UPDATE
            SET content = EXCLUDED.content,
                chunk_index = EXCLUDED.chunk_index,
                metadata = EXCLUDED.metadata,
                embedding = EXCLUDED.embedding
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
```

**Why transaction:** If chunk 7 of 10 fails to insert, the entire operation rolls back. No orphan chunks, no stuck documents. Document goes to `failed` via the existing catch block.

**Why still loop inside tx:** `postgres.js` doesn't support multi-row INSERT with dynamic column count (embedding is a special type). The loop inside a transaction is still atomic.

#### Step D: Remove `util.process_*` calls

Delete these lines entirely (currently ~375-378):
```typescript
// DELETE THESE:
await sql`SELECT util.process_embeddings()`;
await sql`SELECT util.process_metadata()`;
```

#### Step E: Update the HTTP response

Change the response from `"processing"` to `"completed"`:

```typescript
return new Response(
    JSON.stringify({
        document_id,
        status: "completed",      // ← was "processing"
        chunk_count: chunks.length,
        message: "Document processed, embedded, and ready for search.",
    }),
    { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
);
```

### Task 1.4 — Add `beforeunload` Safety Net

Following Supabase best practices from the [automatic-embeddings guide](https://supabase.com/docs/guides/ai/automatic-embeddings), add a `beforeunload` handler to catch Deno worker termination.

Since we're inside `Deno.serve`, the approach is: in the handler, wrap the main call in `Promise.race` with a `catchUnload` promise that rejects on `beforeunload`:

```typescript
function catchUnload(): Promise<never> {
    return new Promise((_resolve, reject) => {
        addEventListener("beforeunload", (ev: any) => {
            reject(new Error(`Worker terminated: ${ev.detail?.reason ?? "unknown"}`));
        });
    });
}

// In HTTP handler:
await Promise.race([
    processDocument(document_id, storage_path, client_id, file_name, file_type),
    catchUnload(),
]);
```

This way, if the Deno isolate hits wall-clock limit mid-processing, the catch block fires and the document is marked `failed` with a descriptive error message.

### Task 1.5 — Remove Supabase Client for DB Writes

Currently `processDocument` creates two clients: `createClient(...)` (for Storage download) and `postgres(...)` (for SQL). After the rewrite, we still need both — Storage for file download, postgres for SQL. No change needed here.

### Summary of `process-document/index.ts` Changes

| Section | Lines (approx) | Action |
|---------|----------------|--------|
| Imports | 1-14 | No change |
| Constants | 15-50 | Add `OPENAI_API_KEY`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS` |
| `generateEmbeddings()` | NEW | Add after constants |
| Metadata LLM config | NEW | Add `LLM_MODEL`, `ALLOWED_THEMES`, `callMetadataLLM()` |
| `processDocument()` — download + parse + chunk | 240-315 | No change |
| `processDocument()` — chunk insertion | 316-370 | **REPLACE**: batch embed → batch enrich → transactional INSERT with embeddings |
| `processDocument()` — util.process_* calls | 371-385 | **DELETE** |
| `processDocument()` — catch/finally | 386-400 | No change |
| HTTP handler — response | 450-460 | Change status to `"completed"` |
| HTTP handler — safety | 445-447 | Add `Promise.race` with `catchUnload()` |

---

## Session 2 — Database Migration: Remove Triggers & Crons

**Goal:** Remove all trigger-based queue infrastructure from the hot path. Keep queues and utility functions for manual recovery.

**File:** Create `supabase/migrations/20260306_remove_embed_and_metadata_triggers.sql`

### Task 2.1 — Drop Embedding Trigger

```sql
-- ============================================================
-- Remove automatic embedding/metadata queue triggers
-- Embeddings and metadata are now generated inline by process-document EF.
-- ============================================================

-- 1. Drop the trigger that queued embedding jobs on chunk insert.
--    Chunks are now inserted WITH embeddings by process-document.
DROP TRIGGER IF EXISTS embed_chunk_on_insert ON vector_db.document_chunks;
```

**Source:** Originally created in `supabase/migrations/20260305_create_vector_db_schema.sql` line 213-216.

The trigger function `vector_db.queue_embedding_if_null()` stays — it's harmless without the trigger and could be useful for manual re-embedding.

### Task 2.2 — Drop Metadata Enrichment Trigger

```sql
-- 2. Drop the trigger that queued metadata enrichment jobs on chunk insert.
--    Metadata is now enriched inline by process-document.
DROP TRIGGER IF EXISTS enrich_metadata_on_insert ON vector_db.document_chunks;
```

**Source:** Originally created in `supabase/migrations/20260305_hybrid_retriever_schema.sql` line 330-332.

The trigger function `vector_db.queue_metadata_if_null()` stays for the same reason.

### Task 2.3 — Unschedule pg_cron Jobs (Safety)

The cron jobs were never registered in production (confirmed: `SELECT * FROM cron.job` returns only `refresh-analytics-mvs-daily`). But add safety `unschedule` calls in case they exist in any other environment:

```sql
-- 3. Remove cron schedules (safety — they may not exist in all environments)
DO $$
BEGIN
  PERFORM cron.unschedule('process-embeddings');
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'process-embeddings cron not found, skipping';
END;
$$;

DO $$
BEGIN
  PERFORM cron.unschedule('process-metadata');
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'process-metadata cron not found, skipping';
END;
$$;
```

### Task 2.4 — Keep the `clear_chunk_embedding_on_update` Trigger

The trigger that clears `embedding = NULL` on content update (`clear_chunk_embedding_on_update`) should **stay**. It's still useful if someone manually updates chunk content — it ensures the stale embedding is cleared. However, since we no longer have automatic re-embedding, we should document that:

```sql
-- NOTE: clear_chunk_embedding_on_update trigger is kept intentionally.
-- If chunk content is updated manually, it clears the embedding.
-- Re-embedding must be done manually (re-upload the document via dashboard).
```

### Task 2.5 — Keep Queues, Functions, and DLQs

**DO NOT DROP:**

- `pgmq` queues: `embedding_jobs`, `embedding_jobs_dlq`, `metadata_jobs`, `metadata_jobs_dlq`
- `util.process_embeddings()` function
- `util.process_metadata()` function
- `util.invoke_edge_function()` function
- `embed` and `enrich-metadata` Edge Functions (keep deployed but dormant)

These serve as an **escape hatch** — if you ever need to manually re-embed chunks or re-enrich metadata, you can:

```sql
-- Manual re-embed example:
SELECT pgmq.send('embedding_jobs', jsonb_build_object(
  'id', chunk_id, 'schema', 'vector_db', 'table', 'document_chunks',
  'contentFunction', 'vector_db.chunk_content_fn', 'embeddingColumn', 'embedding'
));
SELECT util.process_embeddings();
```

### Complete Migration File

```sql
-- 20260306_remove_embed_and_metadata_triggers.sql
-- ============================================================
-- Remove automatic embedding/metadata queue triggers.
-- Reason: process-document EF now generates embeddings and
-- enriches metadata inline (single synchronous pipeline).
-- No cron jobs. No pgmq for the hot path.
-- ============================================================

-- 1. Drop embedding trigger
DROP TRIGGER IF EXISTS embed_chunk_on_insert ON vector_db.document_chunks;

-- 2. Drop metadata enrichment trigger
DROP TRIGGER IF EXISTS enrich_metadata_on_insert ON vector_db.document_chunks;

-- 3. Remove cron schedules (safety)
DO $$ BEGIN PERFORM cron.unschedule('process-embeddings');
EXCEPTION WHEN OTHERS THEN NULL; END; $$;

DO $$ BEGIN PERFORM cron.unschedule('process-metadata');
EXCEPTION WHEN OTHERS THEN NULL; END; $$;

-- 4. Purge stale queue messages from prior failed runs
SELECT pgmq.purge('embedding_jobs');
SELECT pgmq.purge('metadata_jobs');

-- NOTE: The following are intentionally KEPT for manual recovery:
--   - pgmq queues: embedding_jobs, metadata_jobs, *_dlq
--   - Functions: util.process_embeddings(), util.process_metadata()
--   - Trigger functions: vector_db.queue_embedding_if_null(), vector_db.queue_metadata_if_null()
--   - Edge Functions: embed, enrich-metadata (deployed but dormant)
--   - Trigger: clear_chunk_embedding_on_update (clears embedding on content update)
```

---

## Session 3 — Frontend Fixes

### Task 3.1 — Stop Swallowing EF Errors in `uploadSimpleFile()`

**File:** `apps/vizu_dashboard/src/services/knowledgeBaseService.ts`
**Lines:** ~207-208

**Before:**
```typescript
if (fnError)
    console.warn("Aviso: Edge Function retornou erro:", fnError.message);
```

**After:**
```typescript
if (fnError)
    throw new Error(`Erro ao processar documento: ${fnError.message}`);
```

Similarly for `uploadComplexFile()` (~lines 264-266):

**Before:**
```typescript
} catch (err) {
    console.warn("Erro ao chamar file_upload_api:", err);
}
```

**After:**
```typescript
} catch (err) {
    throw new Error(`Erro ao processar documento complexo: ${err instanceof Error ? err.message : String(err)}`);
}
```

### Task 3.2 — Add `partially_failed` to Frontend Types

**File:** `apps/vizu_dashboard/src/services/knowledgeBaseService.ts`
**Line:** ~20

**Before:**
```typescript
status: "pending" | "processing" | "completed" | "failed";
```

**After:**
```typescript
status: "pending" | "processing" | "completed" | "failed" | "partially_failed";
```

### Task 3.3 — Add Stuck-Document Timeout in Polling Hook

**File:** `apps/vizu_dashboard/src/hooks/useKnowledgeBase.ts`
**Lines:** ~41-55

Documents should now transition to `completed` quickly (under 30 seconds total). Add a safety timeout to stop polling and show a stale state:

```typescript
const POLL_INTERVAL_MS = 5_000;
const MAX_PROCESSING_MS = 5 * 60 * 1000; // 5 minutes

// In the useEffect for polling:
const hasInProgress = documents.some((d) => {
    if (d.status !== "pending" && d.status !== "processing") return false;
    // Safety timeout: if stuck for more than MAX_PROCESSING_MS, stop polling
    const elapsed = Date.now() - new Date(d.updated_at).getTime();
    return elapsed < MAX_PROCESSING_MS;
});
```

### Task 3.4 — Add `partially_failed` Badge + Retry Button in Admin Page

**File:** `apps/vizu_dashboard/src/pages/admin/AdminKnowledgeBasePage.tsx`

#### Add StatusBadge case (after `case "failed":`)

```typescript
case "partially_failed":
    return (
        <Tooltip label={doc.error_message || "Alguns chunks falharam"}>
            <Badge colorScheme="orange" fontSize="xs" cursor="help">
                ⚠️ Parcial
            </Badge>
        </Tooltip>
    );
```

#### Add retry function + button

Add a `retryDocument` function to `knowledgeBaseService.ts`:

```typescript
export async function retryDocument(doc: KBDocument): Promise<void> {
    // 1. Delete existing chunks (will be re-created)
    await supabase
        .schema("vector_db")
        .from("document_chunks")
        .delete()
        .eq("document_id", doc.id);

    // 2. Reset document status
    await supabase
        .schema("vector_db")
        .from("documents")
        .update({ status: "processing", error_message: null, chunk_count: 0, updated_at: new Date().toISOString() })
        .eq("id", doc.id);

    // 3. Re-invoke process-document
    const { error } = await supabase.functions.invoke("process-document", {
        body: {
            document_id: doc.id,
            storage_path: doc.storage_path,
            client_id: doc.client_id,
            file_name: doc.file_name,
            file_type: doc.file_type,
        },
    });

    if (error) throw new Error(`Erro ao reprocessar: ${error.message}`);
}
```

In `AdminKnowledgeBasePage.tsx`, add a retry `IconButton` in the actions column for documents with `status === "failed" || status === "partially_failed"`.

---

## Session 4 — Fix Stuck Production Data & Deploy

### Task 4.1 — Deploy Updated `process-document` EF

```bash
cd /Users/lucascruz/Documents/GitHub/vizu-mono
supabase functions deploy process-document --no-verify-jwt
```

**Before deploying**, verify `OPENAI_API_KEY` is set in Supabase secrets:

```bash
supabase secrets list | grep OPENAI
```

### Task 4.2 — Apply Database Migration

```bash
supabase db push
# OR manually apply:
supabase migration up
```

This will:
- Drop the `embed_chunk_on_insert` and `enrich_metadata_on_insert` triggers
- Unschedule any cron jobs (safety)
- Purge stale pgmq messages

### Task 4.3 — Fix Stuck Documents

After deploying the new EF and migration, re-process the 2 stuck documents:

```sql
-- Check current stuck documents
SELECT id, file_name, status, chunk_count, storage_path, client_id, file_type
FROM vector_db.documents
WHERE status IN ('processing', 'pending');
```

Then use the frontend retry button, or manually via SQL + EF invoke:

```sql
-- 1. Delete orphan chunks
DELETE FROM vector_db.document_chunks WHERE document_id IN (
    SELECT id FROM vector_db.documents WHERE status = 'processing'
);

-- 2. Reset status
UPDATE vector_db.documents
SET status = 'processing', chunk_count = 0, error_message = NULL, updated_at = now()
WHERE status = 'processing';
```

Then invoke `process-document` for each via `supabase functions invoke` or the dashboard retry button.

### Task 4.4 — Deploy Frontend

```bash
cd apps/vizu_dashboard
pnpm build
# Deploy based on your setup (Docker, Vercel, etc.)
```

### Task 4.5 — Verify Queues Are Empty

```sql
-- Should show queue_length = 0
SELECT * FROM pgmq.metrics('embedding_jobs');
SELECT * FROM pgmq.metrics('metadata_jobs');
```

---

## Session 5 — Update Docs & Tests

### Task 5.1 — Update `HYBRID_RETRIEVER_AS_BUILT.md`

Key sections to update:

1. **§2.1 Document Ingestion Flow** — Replace the flow diagram. Remove the pgmq/trigger/cron chain. Show inline embed + enrich.
2. **§3.2 Functions & Triggers** table — Mark `embed_chunk_on_insert` and `enrich_metadata_on_insert` as dropped.
3. **§3.5 pgmq Queues** — Note these are now dormant (manual recovery only).
4. **§7.1 Quick Tuning Guide** — Remove "Metadata batch interval" row (no more cron).
5. **§4.1 process-document** — Document the new inline embedding + metadata flow.

### Task 5.2 — Update Tests

**File:** `libs/vizu_rag_factory/tests/unit/test_factory.py`

Existing tests mock the HTTP layer and should pass unchanged. Run:

```bash
poetry run pytest libs/vizu_rag_factory/tests/ -v
```

If any tests reference `util.process_embeddings()` or trigger behavior, update them.

### Task 5.3 — Lint

```bash
cd apps/vizu_dashboard
pnpm lint --fix
```

---

## Verification Checklist

After full deployment, verify:

| # | Check | Command / Action | Expected |
|---|-------|-----------------|----------|
| 1 | Upload small TXT file via dashboard | Upload `test.txt` with a few paragraphs | Status transitions to `completed` within 30s |
| 2 | All chunks have embeddings | `SELECT COUNT(*) FILTER (WHERE embedding IS NULL) FROM vector_db.document_chunks WHERE document_id = '<id>'` | 0 |
| 3 | Metadata enriched | `SELECT metadata->>'theme' FROM vector_db.document_chunks WHERE document_id = '<id>' LIMIT 1` | Non-null theme |
| 4 | FTS vector generated | `SELECT fts IS NOT NULL FROM vector_db.document_chunks WHERE document_id = '<id>' LIMIT 1` | true |
| 5 | No cron jobs for embedding/metadata | `SELECT * FROM cron.job WHERE command LIKE '%process_embeddings%' OR command LIKE '%process_metadata%'` | 0 rows |
| 6 | Embedding queue stays empty | `SELECT queue_length FROM pgmq.metrics('embedding_jobs')` | 0 |
| 7 | Metadata queue stays empty | `SELECT queue_length FROM pgmq.metrics('metadata_jobs')` | 0 |
| 8 | Triggers are gone | `SELECT tgname FROM pg_trigger WHERE tgrelid = 'vector_db.document_chunks'::regclass AND tgname IN ('embed_chunk_on_insert', 'enrich_metadata_on_insert')` | 0 rows |
| 9 | Hybrid search returns results | Use dashboard chat to ask about uploaded content | Relevant answer returned |
| 10 | Retry button works | Click retry on a failed document | Document re-processes to `completed` |
| 11 | Error displayed on failure | Upload a 0-byte file | Error message shown in UI, document marked `failed` |
| 12 | Previously stuck docs fixed | Check `analisedados_polen.md` and `brpolen_sobre_empresa.txt` | Both `completed` with embeddings |

---

## Rollback Strategy

If the new pipeline introduces issues:

1. **Re-enable triggers** (reverse migration):
   ```sql
   CREATE TRIGGER embed_chunk_on_insert AFTER INSERT ON vector_db.document_chunks
     FOR EACH ROW EXECUTE FUNCTION vector_db.queue_embedding_if_null();
   CREATE TRIGGER enrich_metadata_on_insert AFTER INSERT ON vector_db.document_chunks
     FOR EACH ROW EXECUTE FUNCTION vector_db.queue_metadata_if_null();
   ```

2. **Register cron jobs** (if needed):
   ```sql
   SELECT cron.schedule('process-embeddings', '10 seconds', $$ SELECT util.process_embeddings(); $$);
   SELECT cron.schedule('process-metadata', '30 seconds', $$ SELECT util.process_metadata(); $$);
   ```

3. **Roll back `process-document` EF** — deploy previous version from git:
   ```bash
   git checkout HEAD~1 -- supabase/functions/process-document/index.ts
   supabase functions deploy process-document --no-verify-jwt
   ```

The rollback restores the trigger-based async pipeline. Note that the `embed` EF 546 errors would return, so this buys time but doesn't fix the root cause.

---

## Appendix A — File Reference

| File | Session | Action |
|------|---------|--------|
| `supabase/functions/process-document/index.ts` | 1 | **Major rewrite** — inline embedding + metadata |
| `supabase/migrations/20260306_remove_embed_and_metadata_triggers.sql` | 2 | **New file** — drop triggers, unschedule crons |
| `apps/vizu_dashboard/src/services/knowledgeBaseService.ts` | 3 | **Edit** — throw on EF error, add `partially_failed`, add `retryDocument()` |
| `apps/vizu_dashboard/src/hooks/useKnowledgeBase.ts` | 3 | **Edit** — stuck-document timeout |
| `apps/vizu_dashboard/src/pages/admin/AdminKnowledgeBasePage.tsx` | 3 | **Edit** — partially_failed badge, retry button |
| `docs/HYBRID_RETRIEVER_AS_BUILT.md` | 5 | **Edit** — update architecture docs |
| `supabase/functions/embed/index.ts` | — | **Keep deployed, dormant** |
| `supabase/functions/enrich-metadata/index.ts` | — | **Keep deployed, dormant** |

## Appendix B — Timing Estimates

| Stage | Current Time | Expected After |
|-------|-------------|----------------|
| Storage upload | ~1s | ~1s (no change) |
| `process-document` — parse + chunk | ~2-5s | ~2-5s (no change) |
| OpenAI embedding (batch) | N/A (was async) | ~1-3s (single API call for ≤30 chunks) |
| Metadata enrichment (5 concurrent) | N/A (was async) | ~2-4s (LLM calls, 2-6 chunks per batch) |
| Chunk insertion (transactional) | ~1-3s (one-by-one) | ~1-2s (same, but atomic) |
| **Total end-to-end** | **∞ (stuck)** | **~8-15s** |

The Supabase Edge Function timeout is **150s** on Pro plans. Our worst case (large file, 30 chunks) should complete in ~15s — 10x safety margin.
