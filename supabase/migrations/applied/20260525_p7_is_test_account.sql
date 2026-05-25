-- ============================================================================
-- Sprint 2 / B1 — Add is_test_account flag em clientes_blu
-- ============================================================================
-- Contexto:
--   Precisamos separar clientes "de teste" (QA interno, demos, contas
--   sintéticas usadas em fixtures) dos clientes de produção sem deletar
--   ou movê-los pra outra tabela.
--
--   Hoje a view `active_clientes_blu` retorna todos os clientes não
--   soft-deletados, misturando produção e teste. Métricas, billing e
--   alertas estão contaminados.
--
-- Decisões:
--   - boolean NOT NULL DEFAULT false (todos atuais viram "não-teste")
--   - Nova view `production_clientes_blu` para consumo de
--     dashboards/billing/cron
--   - `active_clientes_blu` permanece intacto (compat); quem quiser teste
--     pode filtrar `WHERE is_test_account = true` explicitamente
--
-- Auditoria 2026-05-25: coluna não existe em clientes_blu (confirmado via \d).
--
-- NÃO APLICAR AUTOMATICAMENTE.
-- ============================================================================

BEGIN;

-- 1) Coluna
ALTER TABLE public.clientes_blu
  ADD COLUMN IF NOT EXISTS is_test_account boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN public.clientes_blu.is_test_account IS
  'TRUE para contas internas de teste/QA/demo. Excluídas de production_clientes_blu, '
  'métricas agregadas, billing e alertas. Default false (clientes reais).';

-- 2) Índice parcial (otimiza filtro mais comum: "somente produção")
CREATE INDEX IF NOT EXISTS idx_clientes_blu_is_test_account
  ON public.clientes_blu (is_test_account)
  WHERE is_test_account = true;

-- 3) View de produção (sem testes, sem soft-deleted)
-- Nota: consulta clientes_blu direto pois active_clientes_blu enumera colunas
-- explicitamente e não expõe automaticamente colunas novas.
CREATE OR REPLACE VIEW public.production_clientes_blu AS
  SELECT *
  FROM public.clientes_blu
  WHERE deleted_at IS NULL
    AND is_test_account = false;

COMMENT ON VIEW public.production_clientes_blu IS
  'Subset de active_clientes_blu excluindo contas marcadas como teste. '
  'Use em dashboards, billing, métricas de retenção e alertas operacionais. '
  'Para auditoria/QA, consulte clientes_blu ou active_clientes_blu diretamente.';

-- 4) Grants (espelhar permissões da view de origem)
GRANT SELECT ON public.production_clientes_blu TO anon, authenticated, service_role;

COMMIT;
