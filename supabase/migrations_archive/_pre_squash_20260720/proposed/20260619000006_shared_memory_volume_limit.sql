-- =============================================================================
-- Migration: 20260619000006_shared_memory_volume_limit.sql
-- Issue: #32 — Fase 4: Política de retenção e prune da shared memory
-- Task: T4.4b — Trigger BEFORE INSERT: volume limit (50 registros/entidade)
--
-- Purpose:
--   1. Trigger function check_shared_memory_volume_limit — conta registros
--      ativos por (client_id, entity_type, entity_name) e rejeita INSERT
--      quando count >= 50.
--   2. Trigger trg_shared_memory_volume_limit — executa a verificação
--      BEFORE INSERT.
--
-- Design decisions (DD-03 / DQ-01):
--   - Limite fixo de 50 registros ativos por entidade.
--   - Registros arquivados (archived=true OU soft_delete_at IS NOT NULL)
--     são excluídos da contagem.
--   - source='curated' e ttl_tier='curated' são isentos do limite
--     (registros curados não têm restrição de volume).
--   - A verificação é feita no banco (não no código Python) como safety net
--     — mesmo que o código tente inserir, o trigger bloqueia.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Trigger function: check_shared_memory_volume_limit
-- ---------------------------------------------------------------------------
-- Conta registros ativos (não-arquivados, não-soft-deleted) para a mesma
-- entidade (client_id, entity_type, entity_name). Se count >= 50, rejeita
-- o INSERT com exceção 'volume_limit_exceeded'.
--
-- Curated entries (source='curated' ou ttl_tier='curated') são isentas.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.check_shared_memory_volume_limit()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    _record_count INTEGER;
BEGIN
    -- Curated entries are exempt from volume limit
    IF NEW.source = 'curated' OR NEW.ttl_tier = 'curated' THEN
        RETURN NEW;
    END IF;

    -- Count active (non-archived, non-soft-deleted) records for this entity
    SELECT COUNT(*) INTO _record_count
    FROM public.shared_business_memory
    WHERE client_id = NEW.client_id
      AND entity_type = NEW.entity_type
      AND entity_name = NEW.entity_name
      AND (archived IS NOT TRUE)
      AND (soft_delete_at IS NULL);

    -- Reject if the entity already has 50+ active records
    IF _record_count >= 50 THEN
        RAISE EXCEPTION 'volume_limit_exceeded: Maximum of 50 active records per entity reached for client % (entity: %/%)',
            NEW.client_id, NEW.entity_type, NEW.entity_name;
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION public.check_shared_memory_volume_limit() IS
    'Fase 4 — Volume limit trigger function. '
    'Counts active (non-archived, non-soft-deleted) records per entity '
    '(client_id, entity_type, entity_name) and rejects INSERT when count >= 50. '
    'Curated entries (source=''curated'' or ttl_tier=''curated'') bypass the check. '
    'Exception message: ''volume_limit_exceeded'' with client and entity details.';

-- ---------------------------------------------------------------------------
-- 2. Trigger: trg_shared_memory_volume_limit
-- ---------------------------------------------------------------------------

DROP TRIGGER IF EXISTS trg_shared_memory_volume_limit
    ON public.shared_business_memory;

CREATE TRIGGER trg_shared_memory_volume_limit
    BEFORE INSERT ON public.shared_business_memory
    FOR EACH ROW
    EXECUTE FUNCTION public.check_shared_memory_volume_limit();

COMMENT ON TRIGGER trg_shared_memory_volume_limit
    ON public.shared_business_memory IS
    'Fase 4 — Enforces 50-record volume limit per entity (client, entity_type, entity_name). '
    'Active records only (excludes archived and soft-deleted). '
    'Curated entries (source=''curated'' or ttl_tier=''curated'') bypass the check.';

COMMIT;
