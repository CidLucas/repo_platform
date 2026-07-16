-- 20260716000000_sbm_curated_expires.sql
-- Adiciona as colunas curated + expires_at à shared_business_memory.
--
-- Contexto: o código (sbm_to_lightrag_synthesis, memory_confirm_item) e o
-- índice de 20260619000005 sempre assumiram essas colunas, e o header do
-- 20260619000005 aponta 20260619000002_shared_memory_integrity.sql como a
-- migration que as criaria — mas aquela migration só cria trigger/view.
-- As colunas nunca foram definidas em nenhuma migration do repo.
--
-- Backfill: curated=true para conhecimento que as rotinas da plataforma já
-- produzem (snapshots e fatos de sistema), EXCETO estado operacional do
-- routine engine (checkpoint:*, current_state:* — Issue #21 DD-04), que é
-- dump de state, não conhecimento. Sem o backfill a primeira síntese
-- semanal SBM → LightRAG não teria material.
--
-- Aplicada em prod em 2026-07-15 (sessão Claude, autorizada por Lucas).

BEGIN;

ALTER TABLE public.shared_business_memory
    ADD COLUMN IF NOT EXISTS curated boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS expires_at timestamptz;

COMMENT ON COLUMN public.shared_business_memory.curated IS
    'Fato confirmado como conhecimento (via confirmação humana ou backfill de sistema). '
    'A síntese semanal SBM → LightRAG só lê curated=true.';
COMMENT ON COLUMN public.shared_business_memory.expires_at IS
    'Expiração do fato — NULL = não expira. A síntese ignora fatos expirados.';

-- Backfill: snapshots e fatos de sistema são conhecimento; checkpoints não.
UPDATE public.shared_business_memory
SET curated = true
WHERE curated = false
  AND (entity_type = 'snapshot' OR source = 'system')
  AND key NOT LIKE 'checkpoint:%'
  AND key NOT LIKE 'current_state:%';

-- Índices de 20260619000005 (sem CONCURRENTLY — tabela pequena, dentro da tx)
CREATE INDEX IF NOT EXISTS idx_sbm_synthesis_weekly
    ON public.shared_business_memory (client_id, curated, expires_at)
    WHERE curated = true AND expires_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_sbm_entity_temporal
    ON public.shared_business_memory (client_id, entity_type, entity_name, updated_at DESC);

COMMIT;
