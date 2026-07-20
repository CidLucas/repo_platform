-- Alinha public.shared_business_memory com os writers Python
-- (context_report._write_to_shared_memory e onboarding_shared_memory_hook):
--   1. coluna `category`  — escrita como 'context' em todos os upserts
--   2. coluna `version`   — escrita como 1 em todos os upserts
--   3. entity_type CHECK  — aceitar 'snapshot' (context_report escreve
--      entity_type='snapshot' para resumo/indicadores mensais)
--
-- Sem isso, todo upsert falha com PGRST204 ("Could not find the 'category'
-- column") e a memória compartilhada nunca é gravada.
--
-- Extraído da migration proposta 20260619000000_shared_business_memory.sql
-- (que recria a tabela inteira — aqui aplicamos apenas o delta, pois a
-- tabela já existe em prod com outra forma).

ALTER TABLE public.shared_business_memory
    ADD COLUMN IF NOT EXISTS category text
        CHECK (category IN (
            'knowledge', 'rag', 'documents', 'memory-agent',
            'context', 'decision', 'preference'
        ));

ALTER TABLE public.shared_business_memory
    ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1;

ALTER TABLE public.shared_business_memory
    DROP CONSTRAINT IF EXISTS shared_business_memory_entity_type_check;

ALTER TABLE public.shared_business_memory
    ADD CONSTRAINT shared_business_memory_entity_type_check
    CHECK (entity_type = ANY (ARRAY[
        'skill'::text, 'client'::text, 'contact'::text, 'supplier'::text,
        'user'::text, 'agent_result'::text, 'agent_metadata'::text,
        'routine'::text, 'snapshot'::text
    ]));

COMMENT ON COLUMN public.shared_business_memory.category IS
    'Semantic category for filtering and routing: knowledge | rag | documents | memory-agent | context | decision | preference';

CREATE INDEX IF NOT EXISTS idx_sbm_category
    ON public.shared_business_memory (client_id, category)
    WHERE category IS NOT NULL;

-- PostgREST precisa recarregar o schema cache para enxergar as colunas novas
NOTIFY pgrst, 'reload schema';
