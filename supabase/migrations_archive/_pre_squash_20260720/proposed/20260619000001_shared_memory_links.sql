-- =============================================================================
-- Migration: shared_memory_links
-- Purpose: Explicit semantic links between shared_business_memory entities.
--   Enables relationship queries like "which contacts work_for this supplier"
--   or "which skills use this policy preference".
--
-- Design:
--   - Separate link table (not a JSONB field on shared_business_memory)
--     to enable efficient join, filter, and traversal queries.
--   - Links reference entities by (entity_type, entity_name) — same taxonomy
--     as shared_business_memory (skill, client, contact, supplier, user).
--   - link_type is free-form text enabling any relationship: "works_for",
--     "applies_to", "prefers", "reports_to", "depends_on", etc.
--   - UNIQUE constraint prevents duplicate links between the same pair
--     with the same link_type.
--   - client_id isolation via RLS (identical pattern to shared_business_memory).
--   - Optional source_memory_id / target_memory_id to link specific memory
--     records (not just entity-level links).
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.shared_memory_links (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    client_id   uuid NOT NULL
                    REFERENCES public.clientes_blu(client_id)
                    ON DELETE CASCADE,

    -- Source entity (the subject of the relationship)
    source_entity_type text NOT NULL
                        CHECK (source_entity_type IN (
                            'skill', 'client', 'contact', 'supplier', 'user'
                        )),
    source_entity_name text NOT NULL,

    -- Target entity (the object of the relationship)
    target_entity_type text NOT NULL
                        CHECK (target_entity_type IN (
                            'skill', 'client', 'contact', 'supplier', 'user'
                        )),
    target_entity_name text NOT NULL,

    -- The type of relationship (free-form, application-defined)
    link_type text NOT NULL
              CHECK (length(link_type) >= 2 AND length(link_type) <= 128),

    -- Optional: link specific memory records (by id) for more granular linking
    source_memory_id uuid
                     REFERENCES public.shared_business_memory(id)
                     ON DELETE SET NULL,
    target_memory_id uuid
                     REFERENCES public.shared_business_memory(id)
                     ON DELETE SET NULL,

    -- Metadata
    source     text NOT NULL DEFAULT 'manual'
                   CHECK (source IN (
                       'manual', 'memory_agent', 'specialist', 'migration', 'system'
                   )),
    confidence numeric NOT NULL DEFAULT 1.0
                       CHECK (confidence >= 0.0 AND confidence <= 1.0),
    metadata   jsonb NOT NULL DEFAULT '{}'::jsonb,

    created_at timestamptz NOT NULL DEFAULT now(),

    -- Uniqueness: one link of a given type between the same pair
    CONSTRAINT uq_shared_memory_link
        UNIQUE (client_id, source_entity_type, source_entity_name,
                link_type, target_entity_type, target_entity_name)
);

COMMENT ON TABLE public.shared_memory_links IS
    'Explicit semantic links between shared_business_memory entities. '
    'Enables relationship queries across entity types.';
COMMENT ON COLUMN public.shared_memory_links.link_type IS
    'Relationship label: e.g. works_for, applies_to, prefers, reports_to, depends_on';
COMMENT ON COLUMN public.shared_memory_links.source_memory_id IS
    'Optional: link a specific memory record (not just entity-level)';
COMMENT ON COLUMN public.shared_memory_links.target_memory_id IS
    'Optional: link to a specific memory record (not just entity-level)';

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------

-- Primary query: find all links for a source entity (outgoing)
CREATE INDEX IF NOT EXISTS idx_sml_source
    ON public.shared_memory_links (client_id, source_entity_type, source_entity_name);

-- Reverse query: find all links pointing to a target entity (incoming)
CREATE INDEX IF NOT EXISTS idx_sml_target
    ON public.shared_memory_links (client_id, target_entity_type, target_entity_name);

-- Filter by link_type (e.g. all "works_for" relationships for a client)
CREATE INDEX IF NOT EXISTS idx_sml_type
    ON public.shared_memory_links (client_id, link_type);

-- Memory-level lookups
CREATE INDEX IF NOT EXISTS idx_sml_source_memory
    ON public.shared_memory_links (source_memory_id)
    WHERE source_memory_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_sml_target_memory
    ON public.shared_memory_links (target_memory_id)
    WHERE target_memory_id IS NOT NULL;

-- ---------------------------------------------------------------------------
-- Row-Level Security
-- ---------------------------------------------------------------------------

ALTER TABLE public.shared_memory_links ENABLE ROW LEVEL SECURITY;

CREATE POLICY "sml_client_all"
    ON public.shared_memory_links
    AS PERMISSIVE FOR ALL
    TO authenticated
    USING (client_id = public.get_my_client_id())
    WITH CHECK (client_id = public.get_my_client_id());

-- ---------------------------------------------------------------------------
-- Grants
-- ---------------------------------------------------------------------------

GRANT ALL ON public.shared_memory_links TO authenticated;
GRANT ALL ON public.shared_memory_links TO service_role;

-- ---------------------------------------------------------------------------
-- Auto-update trigger for client_id consistency
-- ---------------------------------------------------------------------------

-- Ensure link_type is stored lowercase for consistent querying
CREATE OR REPLACE FUNCTION public.normalize_shared_memory_link()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.link_type := lower(trim(NEW.link_type));
    NEW.source_entity_name := lower(trim(NEW.source_entity_name));
    NEW.target_entity_name := lower(trim(NEW.target_entity_name));
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_sml_normalize
    BEFORE INSERT OR UPDATE ON public.shared_memory_links
    FOR EACH ROW
    EXECUTE FUNCTION public.normalize_shared_memory_link();
