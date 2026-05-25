-- Migration: fix fato_compras FK cascade + client offboarding function
-- Problem: analytics_v2.fato_compras had NO ACTION on client delete → orphan rows
-- Solution: 1) fix the FK; 2) create offboard_client() that deletes in batches

-- ============================================================
-- 1. Fix FK: fato_compras → clientes_blu (NO ACTION → CASCADE)
-- ============================================================
ALTER TABLE analytics_v2.fato_compras
    DROP CONSTRAINT fato_compras_client_id_fkey;

ALTER TABLE analytics_v2.fato_compras
    ADD CONSTRAINT fato_compras_client_id_fkey
    FOREIGN KEY (client_id)
    REFERENCES clientes_blu(client_id)
    ON DELETE CASCADE;

-- ============================================================
-- 2. Function: offboard_client_batch(p_client_id uuid, p_table text, p_batch_size int)
--    Deletes ONE batch from a specific table for the given client.
--    Returns number of rows deleted in this batch.
--
--    ⚠️  DESIGN: plpgsql LOOP does NOT commit between iterations — the entire
--    function runs in a single transaction, which holds the pooler connection
--    and blocks other tenants just like a plain DELETE.
--    The correct pattern is to call this function repeatedly from the
--    application layer (Python/edge function) until it returns 0, committing
--    between each call. This gives the pooler connection back after each batch.
--
--    Offboarding order (caller must follow):
--      1. Loop offboard_client_batch for each big table until 0
--         (analytics_v2.dim_inventory, fato_transacoes, fato_compras,
--          dim_clientes, dim_fornecedores, client_routine_executions,
--          messages, frontend_events, notifications)
--      2. DELETE FROM clientes_blu WHERE client_id = ? (cascade handles rest)
--      3. Delete auth.users via Supabase Admin API (psql cannot touch auth schema)
-- ============================================================
CREATE OR REPLACE FUNCTION public.offboard_client_batch(
    p_client_id  uuid,
    p_schema     text,
    p_table      text,
    p_batch_size int DEFAULT 10000
)
RETURNS int
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_deleted int;
BEGIN
    EXECUTE format(
        'WITH rows AS (
            SELECT ctid FROM %I.%I
            WHERE client_id = $1
            LIMIT $2
        )
        DELETE FROM %I.%I
        WHERE ctid IN (SELECT ctid FROM rows)',
        p_schema, p_table, p_schema, p_table
    ) USING p_client_id, p_batch_size;

    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    RETURN v_deleted;
END;
$$;

COMMENT ON FUNCTION public.offboard_client_batch(uuid, text, text, int) IS
'Delete one batch of rows for a client from a specific table.
Call repeatedly from the application until it returns 0, then DELETE FROM clientes_blu.
This releases the pooler connection between batches — safe for multi-tenant production.
Example: SELECT offboard_client_batch(''<uuid>'', ''analytics_v2'', ''dim_inventory'', 10000);';
