-- Migration: Polp ETL to fato_transacoes
-- Created: 2026-05-21

-- 1. Function: sync_polp_transactions
CREATE OR REPLACE FUNCTION analytics_v2.sync_polp_transactions(p_client_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, analytics_v2
AS $$
DECLARE
  v_synced  int := 0;
  v_skipped int := 0;
BEGIN
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
  ON CONFLICT (transacao_id, client_id) DO UPDATE SET
    valor          = EXCLUDED.valor,
    valor_unitario = EXCLUDED.valor_unitario,
    status         = EXCLUDED.status,
    tipo_transacao = COALESCE(analytics_v2.fato_transacoes.tipo_transacao, EXCLUDED.tipo_transacao),
    categoria      = COALESCE(analytics_v2.fato_transacoes.categoria,      EXCLUDED.categoria),
    subcategoria   = COALESCE(analytics_v2.fato_transacoes.subcategoria,   EXCLUDED.subcategoria),
    updated_at     = NOW();

  GET DIAGNOSTICS v_synced = ROW_COUNT;

  RETURN jsonb_build_object('synced', v_synced, 'client_id', p_client_id);
END;
$$;


-- 2. Function: enqueue_polp_sync
CREATE OR REPLACE FUNCTION analytics_v2.enqueue_polp_sync()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_cid uuid;
BEGIN
  FOR v_cid IN
    SELECT DISTINCT client_id
    FROM public.polp_integrations
    WHERE status != 'DELETED'
  LOOP
    PERFORM analytics_v2.sync_polp_transactions(v_cid);
  END LOOP;
END;
$$;


-- 3. pg_cron job every 6 hours
SELECT cron.unschedule('polp_sync_to_fato_6h') WHERE EXISTS (
  SELECT 1 FROM cron.job WHERE jobname = 'polp_sync_to_fato_6h'
);

SELECT cron.schedule(
  'polp_sync_to_fato_6h',
  '0 */6 * * *',
  $$SELECT analytics_v2.enqueue_polp_sync();$$
);
