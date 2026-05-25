-- Migration: rewrite sync_polp_transactions with batching
-- Problem: original does a single INSERT...SELECT of all polp_transactions,
--          which holds the pooler connection for minutes with large volumes.
-- Solution: loop in batches of p_batch_size rows ordered by polp_transaction_id.
--           Each LOOP iteration is its own statement but shares the transaction
--           (plpgsql limitation with pooler). Caller should use direct connection
--           (DATABASE_URL_DIRECT, port 5432) to avoid transaction-mode timeout.

CREATE OR REPLACE FUNCTION analytics_v2.sync_polp_transactions(
    p_client_id  uuid,
    p_batch_size int DEFAULT 500
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_synced        int := 0;
    v_batch_synced  int;
    v_last_id       bigint := 0;
BEGIN
    LOOP
        INSERT INTO analytics_v2.fato_transacoes (
            transacao_id,
            client_id,
            data_competencia_id,
            customer_id,
            fornecedor_id,
            produto_id,
            documento,
            quantidade,
            valor_unitario,
            valor,
            status,
            tipo_transacao,
            tipo_lancamento,
            categoria,
            subcategoria,
            updated_at
        )
        SELECT
            'polp_' || pt.polp_transaction_id::text,
            pt.client_id,
            dd.data_id,
            NULL::bigint,
            NULL::bigint,
            NULL::bigint,
            'polp_' || pt.polp_transaction_id::text,
            1,
            ABS(pt.amount),
            ABS(pt.amount),
            COALESCE(pt.status, 'confirmed'),
            CASE
              WHEN pt.type = 'CREDIT' THEN 'venda'
              WHEN pt.type = 'DEBIT'  THEN 'compra'
              ELSE NULL
            END,
            'bancario',
            pt.category->>'name',
            pt.category->>'description',
            NOW()
        FROM public.polp_transactions pt
        LEFT JOIN analytics_v2.dim_datas dd
            ON dd.data_id = to_char(pt.date, 'YYYYMMDD')::bigint
        WHERE pt.client_id = p_client_id
          AND pt.status IS DISTINCT FROM 'deleted'
          AND pt.polp_transaction_id > v_last_id
        ORDER BY pt.polp_transaction_id
        LIMIT p_batch_size
        ON CONFLICT (transacao_id, client_id) DO UPDATE SET
            valor          = EXCLUDED.valor,
            valor_unitario = EXCLUDED.valor_unitario,
            status         = EXCLUDED.status,
            tipo_transacao = COALESCE(analytics_v2.fato_transacoes.tipo_transacao, EXCLUDED.tipo_transacao),
            categoria      = COALESCE(analytics_v2.fato_transacoes.categoria,      EXCLUDED.categoria),
            subcategoria   = COALESCE(analytics_v2.fato_transacoes.subcategoria,   EXCLUDED.subcategoria),
            updated_at     = NOW();

        GET DIAGNOSTICS v_batch_synced = ROW_COUNT;
        v_synced := v_synced + v_batch_synced;

        EXIT WHEN v_batch_synced < p_batch_size;

        -- Advance cursor: find the max polp_transaction_id processed in this batch
        SELECT MAX(pt.polp_transaction_id)
          INTO v_last_id
          FROM public.polp_transactions pt
         WHERE pt.client_id = p_client_id
           AND pt.status IS DISTINCT FROM 'deleted'
           AND pt.polp_transaction_id > v_last_id
         ORDER BY pt.polp_transaction_id
         LIMIT p_batch_size;
    END LOOP;

    RETURN jsonb_build_object('synced', v_synced, 'client_id', p_client_id);
END;
$$;

COMMENT ON FUNCTION analytics_v2.sync_polp_transactions(uuid, int) IS
  'Syncs polp_transactions -> fato_transacoes in batches. '
  'Use direct connection (port 5432) for large volumes. '
  'Caller: enqueue_polp_sync or edge function polp-sync-worker.';
