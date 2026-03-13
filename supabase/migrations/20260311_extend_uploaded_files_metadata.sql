-- Migration: Extend uploaded_files_metadata for standalone agent sessions
-- Purpose: Add session_id and columns_schema to link CSV files to standalone agent sessions
-- Date: 2026-03-11

-- Link files to standalone agent sessions (NULL = legacy upload, not linked to any session)
ALTER TABLE public.uploaded_files_metadata
    ADD COLUMN IF NOT EXISTS session_id UUID REFERENCES standalone_agent_sessions(id) ON DELETE SET NULL;

-- Store detected CSV column schema for agent context
-- Format: [{name: "col", type: "text|numeric|date|boolean", sample: [...]}]
ALTER TABLE public.uploaded_files_metadata
    ADD COLUMN IF NOT EXISTS columns_schema JSONB;

-- Index for session-based lookups
CREATE INDEX IF NOT EXISTS idx_uploaded_files_session ON uploaded_files_metadata(session_id)
    WHERE session_id IS NOT NULL;
