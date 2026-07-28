-- =====================================================================
-- 20260720000003_consolidate_get_indicators_overload.sql
-- Resolve a ambiguidade "function get_indicators_for_client is not unique".
--
-- Existiam duas sobrecargas: (uuid, text, text) e
-- (uuid, text, text, int DEFAULT 0). Como o 4o argumento tem default, a de
-- 4 args é superconjunto exato da de 3 (offset=0 reproduz o comportamento
-- antigo) e seu corpo é o mais completo (lógica de janela com p_offset_days).
-- Qualquer chamada com 3 args — posicional ou via PostgREST por nomes —
-- resolve para a de 4 args preenchendo o default.
--
-- Dropamos a redundante de 3 args. DROP com tipos explícitos é inequívoco
-- (assinatura de 3 args != 4 args). Nenhum caller no código nem função no
-- banco depende da assinatura de 3 args (verificado 2026-07-20).
-- =====================================================================

BEGIN;

DROP FUNCTION IF EXISTS analytics_v2.get_indicators_for_client(uuid, text, text);

COMMIT;
