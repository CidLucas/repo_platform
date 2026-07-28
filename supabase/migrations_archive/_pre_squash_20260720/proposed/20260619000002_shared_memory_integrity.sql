-- =============================================================================
-- Migration: 20260619000002_shared_memory_integrity.sql
-- Issue: #20 — Validação de integridade da shared memory
--
-- Purpose:
--   1. Trigger function validate_memory_insert — validação semântica
--      antes de INSERT/UPDATE na shared_business_memory.
--   2. Trigger trg_validate_memory_insert — executa a validação.
--   3. View valid_shared_memory — filtra registros com integridade OK.
--
-- Design decisions:
--   - DB triggers complementam tool-level validation (safety net).
--   - Mensagens de erro explícitas (não genéricas) para facilitar debug.
--   - View é read-only e não depende de RLS (usa WHERE no nível SQL).
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Trigger function: validate_memory_insert
-- ---------------------------------------------------------------------------
-- Valida que key, category e value estão presentes e válidos antes de
-- INSERT ou UPDATE. Lança exceção com mensagem específica em caso de falha.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.validate_memory_insert()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    _valid_categories text[] := ARRAY[
        'knowledge', 'rag', 'documents', 'memory-agent',
        'context', 'decision', 'preference'
    ];
BEGIN
    -- 1. key não pode ser vazio (string trimming)
    IF NEW.key IS NULL OR trim(NEW.key) = '' THEN
        RAISE EXCEPTION 'shared_business_memory.key não pode ser vazio ou nulo. entity_type=%, entity_name=%',
            NEW.entity_type, NEW.entity_name;
    END IF;

    -- 2. category deve estar no conjunto permitido (quando informado)
    IF NEW.category IS NOT NULL AND NOT (NEW.category = ANY (_valid_categories)) THEN
        RAISE EXCEPTION 'shared_business_memory.category inválido: "%". Permitidos: %',
            NEW.category, array_to_string(_valid_categories, ', ');
    END IF;

    -- 3. value não pode ser nulo (SQL NULL, não JSON null)
    IF NEW.value IS NULL THEN
        RAISE EXCEPTION 'shared_business_memory.value não pode ser nulo. key=%, entity_type=%',
            NEW.key, NEW.entity_type;
    END IF;

    -- 4. confidence deve estar no range [0, 1] (safety net — já tem CHECK na tabela)
    IF NEW.confidence < 0.0 OR NEW.confidence > 1.0 THEN
        RAISE EXCEPTION 'shared_business_memory.confidence fora do range [0,1]: %', NEW.confidence;
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION public.validate_memory_insert() IS
    'Valida key (não-vazio), category (conjunto permitido), value (não-nulo) e confidence [0,1]. '
    'Lança exceção com mensagem específica em caso de falha.';

-- ---------------------------------------------------------------------------
-- 2. Trigger: trg_validate_memory_insert
-- ---------------------------------------------------------------------------

DROP TRIGGER IF EXISTS trg_validate_memory_insert
    ON public.shared_business_memory;

CREATE TRIGGER trg_validate_memory_insert
    BEFORE INSERT OR UPDATE ON public.shared_business_memory
    FOR EACH ROW
    EXECUTE FUNCTION public.validate_memory_insert();

COMMENT ON TRIGGER trg_validate_memory_insert
    ON public.shared_business_memory IS
    'Valida integridade semântica antes de INSERT/UPDATE: key, category, value, confidence.';

-- ---------------------------------------------------------------------------
-- 3. View: valid_shared_memory
-- ---------------------------------------------------------------------------
-- Retorna apenas registros com integridade OK:
--   - key não-vazio (garantido pela CHECK + trigger)
--   - category válida (quando informada, dentro do conjunto permitido)
--   - value não-nulo
--   - confidence no range [0, 1]
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW public.valid_shared_memory AS
SELECT
    id,
    client_id,
    entity_type,
    entity_name,
    key,
    category,
    value,
    source,
    confidence,
    metadata,
    created_at,
    updated_at
FROM public.shared_business_memory
WHERE
    key IS NOT NULL
    AND trim(key) <> ''
    AND value IS NOT NULL
    AND (
        category IS NULL
        OR category IN (
            'knowledge', 'rag', 'documents', 'memory-agent',
            'context', 'decision', 'preference'
        )
    )
    AND confidence >= 0.0
    AND confidence <= 1.0;

COMMENT ON VIEW public.valid_shared_memory IS
    'Registros de shared_business_memory com integridade OK: key não-vazio, '
    'category válida (ou nula), value não-nulo, confidence [0,1]. '
    'Use esta view para queries que exigem dados íntegros.';

-- ---------------------------------------------------------------------------
-- Grants
-- ---------------------------------------------------------------------------

GRANT SELECT ON public.valid_shared_memory TO authenticated;
GRANT SELECT ON public.valid_shared_memory TO service_role;

COMMIT;
