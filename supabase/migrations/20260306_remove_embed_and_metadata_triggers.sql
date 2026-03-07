-- 20260306_remove_embed_and_metadata_triggers.sql
-- ============================================================
-- Remove automatic embedding/metadata queue triggers.
-- Reason: process-document EF now generates embeddings and
-- enriches metadata inline (single synchronous pipeline).
-- No cron jobs. No pgmq for the hot path.
-- ============================================================

-- 1. Drop embedding trigger (queued embedding jobs on chunk insert)
--    Chunks are now inserted WITH embeddings by process-document.
DROP TRIGGER IF EXISTS embed_chunk_on_insert ON vector_db.document_chunks;

-- 2. Drop metadata enrichment trigger (queued metadata jobs on chunk insert)
--    Metadata is now enriched inline by process-document.
DROP TRIGGER IF EXISTS enrich_metadata_on_insert ON vector_db.document_chunks;

-- 3. Remove cron schedules (safety — they may not exist in all environments)
DO $$ BEGIN
  PERFORM cron.unschedule('process-embeddings');
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'process-embeddings cron not found, skipping';
END; $$;

DO $$ BEGIN
  PERFORM cron.unschedule('process-metadata');
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'process-metadata cron not found, skipping';
END; $$;

-- 4. Purge stale queue messages from prior failed runs
SELECT pgmq.purge_queue('embedding_jobs');
SELECT pgmq.purge_queue('metadata_jobs');

-- NOTE: The following are intentionally KEPT for manual recovery:
--   - pgmq queues: embedding_jobs, metadata_jobs, *_dlq
--   - Functions: util.process_embeddings(), util.process_metadata()
--   - Trigger functions: vector_db.queue_embedding_if_null(), vector_db.queue_metadata_if_null()
--   - Edge Functions: embed, enrich-metadata (deployed but dormant)
--   - Trigger: clear_chunk_embedding_on_update (clears embedding on content update)
--   - Trigger: generate_fts_on_insert_or_update (generates FTS vector)
