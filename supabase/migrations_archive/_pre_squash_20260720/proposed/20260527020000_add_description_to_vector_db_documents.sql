-- Migration: add description column to vector_db.documents
-- Context: knowledgeBaseService.ts inserts description (optional) but column was missing
-- PGRST204 error on upload to knowledge base

ALTER TABLE vector_db.documents
  ADD COLUMN IF NOT EXISTS description text;

COMMENT ON COLUMN vector_db.documents.description IS 'Optional user-provided description of the document';
