-- Migration: Remove legacy embedding queue infrastructure
-- Reason: process-document EF handles all embedding inline via Cohere.
-- The embed EF, pgmq queues, and related functions are no longer used.
-- Triggers feeding the queue were already removed in 20260306_remove_embed_and_metadata_triggers.sql
-- Cron jobs were already removed in 20260306_drop_embedding_cron_jobs.sql

-- 1. Drop the stale trigger on document_chunks
DROP TRIGGER IF EXISTS clear_chunk_embedding_on_update ON vector_db.document_chunks;

-- 2. Drop trigger/queue-related functions
DROP FUNCTION IF EXISTS vector_db.clear_chunk_embedding_on_update();
DROP FUNCTION IF EXISTS vector_db.queue_embedding_if_null();
DROP FUNCTION IF EXISTS vector_db.chunk_content_fn(vector_db.document_chunks);
DROP FUNCTION IF EXISTS util.process_embeddings(integer, integer, integer);

-- 3. Drop pgmq queues (both empty — verified before migration)
SELECT pgmq.drop_queue('embedding_jobs');
SELECT pgmq.drop_queue('embedding_jobs_dlq');
