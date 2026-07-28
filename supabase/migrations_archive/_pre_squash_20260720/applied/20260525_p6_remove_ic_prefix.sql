-- ============================================================================
-- Sprint 2 / A5 — Remove `ic-` prefix from integration_tokens.provider
-- ============================================================================
-- Contexto:
--   Algumas integrações chegaram a ser persistidas com o prefixo de UI `ic-`
--   (ex.: `ic-monday`, `ic-slack`, `ic-notion`) enquanto os módulos Python
--   (agents, edge functions, libs) consultam o provider SEM prefixo.
--   Mismatch silencioso => o token está salvo mas o módulo não acha.
--
-- Auditoria em 2026-05-25 (DB de produção):
--   SELECT provider, count(*) FROM integration_tokens
--   WHERE provider LIKE 'ic-%' GROUP BY 1;
--   -> 0 rows.
--
--   Hoje não há linhas com `ic-`. Esta migration é DEFENSIVA: garante que se
--   alguma escrita futura voltar com prefixo, fica normalizada na próxima
--   janela. Também serve como contrato explícito do esquema.
--
-- NÃO APLICAR AUTOMATICAMENTE. Revisar e aplicar via psql/Supabase Studio.
-- ============================================================================

BEGIN;

-- 1) Atualiza linhas SEM conflito: para cada (client_id, provider, account_email)
--    com `ic-`, troca para versão sem prefixo, desde que não haja já uma linha
--    com a versão limpa (evita violar a UNIQUE composta).
UPDATE integration_tokens AS it
SET provider = REPLACE(it.provider, 'ic-', '')
WHERE it.provider LIKE 'ic-%'
  AND NOT EXISTS (
    SELECT 1 FROM integration_tokens t2
    WHERE t2.client_id     = it.client_id
      AND t2.provider      = REPLACE(it.provider, 'ic-', '')
      AND t2.account_email = it.account_email
  );

-- 2) Auditoria pós-update: lista o que sobrou com `ic-` (esses são conflitos
--    reais — o cliente já tem token sem prefixo e um duplicado com prefixo).
--    Imprima no console do psql; trate manualmente (decidir qual é o oficial).
DO $$
DECLARE
  rec record;
  leftover_count int := 0;
BEGIN
  FOR rec IN
    SELECT client_id, provider, account_email, created_at
    FROM integration_tokens
    WHERE provider LIKE 'ic-%'
    ORDER BY client_id, provider
  LOOP
    leftover_count := leftover_count + 1;
    RAISE NOTICE '[ic-prefix-leftover] client=% provider=% account=% created=%',
      rec.client_id, rec.provider, rec.account_email, rec.created_at;
  END LOOP;
  RAISE NOTICE '[ic-prefix-leftover] total restante=%', leftover_count;
END$$;

-- 3) (Opcional) Após confirmar 0 leftovers em todos os clientes, adicionar
--    constraint para impedir futuras gravações com prefixo:
-- ALTER TABLE integration_tokens
--   ADD CONSTRAINT integration_tokens_provider_no_ic_prefix
--   CHECK (provider NOT LIKE 'ic-%');

COMMIT;
