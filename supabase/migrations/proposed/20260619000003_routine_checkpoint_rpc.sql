-- 20260619000003_routine_checkpoint_rpc.sql
-- Issue #21: Routine Engine Checkpoint em Shared Memory
-- T2.1.1 + T2.1.4: RPC upsert + get_routine_checkpoints
--
-- Design:
--   DD-01: entity_type='routine'
--   DD-04: Key pattern checkpoint:run:{exec_id}:step:{N} + current_state:{routine_id}
--   Checkpoint duplo: result_metadata (HITL) + shared_business_memory (cross-agent)
--   State completo (não diff)
--
-- NÃO aplicar automaticamente. Lucas revisa.

BEGIN;

-- ===========================================================================
-- 1. Expandir entity_type CHECK constraint para incluir 'routine'
-- ===========================================================================

ALTER TABLE public.shared_business_memory
    DROP CONSTRAINT IF EXISTS shared_business_memory_entity_type_check;

ALTER TABLE public.shared_business_memory
    ADD CONSTRAINT shared_business_memory_entity_type_check
    CHECK (entity_type IN (
        'skill', 'client', 'contact', 'supplier', 'user',
        'agent_result', 'agent_metadata', 'routine'
    ));

COMMENT ON COLUMN public.shared_business_memory.entity_type IS
    'Entity taxonomy: skill | client | contact | supplier | user | agent_result | agent_metadata | routine';

-- ===========================================================================
-- 2. RPC: upsert_routine_checkpoint
--    Upserta 3 keys no shared_business_memory a cada checkpoint.
-- ===========================================================================

CREATE OR REPLACE FUNCTION public.upsert_routine_checkpoint(
    p_client_id    uuid,
    p_routine_id   text,
    p_exec_id      uuid,
    p_step_number  int,
    p_state_value  jsonb
) RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    -- Key 1: Histórico por step (nunca sobrescrito — step único por execução)
    INSERT INTO public.shared_business_memory
        (client_id, entity_type, entity_name, key, value, source, confidence)
    VALUES
        (p_client_id, 'routine', p_routine_id,
         format('checkpoint:run:%s:step:%s', p_exec_id, p_step_number),
         p_state_value, 'system', 1.0)
    ON CONFLICT (client_id, entity_type, entity_name, key)
    DO NOTHING;  -- step nunca deve colidir

    -- Key 2: Current state (sobrescreve a cada execução)
    INSERT INTO public.shared_business_memory
        (client_id, entity_type, entity_name, key, value, source, confidence)
    VALUES
        (p_client_id, 'routine', p_routine_id,
         format('current_state:%s', p_routine_id),
         p_state_value, 'system', 1.0)
    ON CONFLICT (client_id, entity_type, entity_name, key)
    DO UPDATE SET
        value      = EXCLUDED.value,
        updated_at = now();

    -- Key 3: Última execução (timestamp + exec_id + last_step — útil para dashboards)
    INSERT INTO public.shared_business_memory
        (client_id, entity_type, entity_name, key, value, source, confidence)
    VALUES
        (p_client_id, 'routine', p_routine_id,
         format('last_execution:%s', p_routine_id),
         jsonb_build_object(
             'exec_id',     p_exec_id,
             'last_step',   p_step_number,
             'completed_at', now()
         ),
         'system', 1.0)
    ON CONFLICT (client_id, entity_type, entity_name, key)
    DO UPDATE SET
        value      = EXCLUDED.value,
        updated_at = now();
END;
$$;

COMMENT ON FUNCTION public.upsert_routine_checkpoint IS
    'Checkpoint de execução de rotina em shared_business_memory. '
    'Upserta 3 keys: checkpoint:run:{exec_id}:step:{N} (histórico), '
    'current_state:{routine_id} (estado atual), '
    'last_execution:{routine_id} (timestamp da última execução).';

-- ===========================================================================
-- 3. Função: get_routine_checkpoints (debugging / T2.1.4)
--    Retorna os últimos N checkpoints de uma rotina.
-- ===========================================================================

CREATE OR REPLACE FUNCTION public.get_routine_checkpoints(
    p_routine_id text,
    p_limit      int DEFAULT 10
) RETURNS TABLE(
    key        text,
    value      jsonb,
    created_at timestamptz,
    updated_at timestamptz
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT key, value, created_at, updated_at
    FROM public.shared_business_memory
    WHERE entity_type = 'routine'
      AND entity_name = p_routine_id
    ORDER BY updated_at DESC
    LIMIT p_limit;
$$;

COMMENT ON FUNCTION public.get_routine_checkpoints IS
    'Retorna os últimos N checkpoints de uma rotina para debugging. '
    'Ordenado por updated_at DESC. Útil para inspecionar o histórico de execução.';

COMMIT;
