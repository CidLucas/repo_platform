-- supabase migration: merge configuracao_negocio fields into cliente_vizu
-- Add new columns
ALTER TABLE IF EXISTS public.cliente_vizu
  ADD COLUMN IF NOT EXISTS horario_funcionamento jsonb;

ALTER TABLE IF EXISTS public.cliente_vizu
  ADD COLUMN IF NOT EXISTS prompt_base text;

ALTER TABLE IF EXISTS public.cliente_vizu
  ADD COLUMN IF NOT EXISTS ferramenta_rag_habilitada boolean DEFAULT false NOT NULL;

ALTER TABLE IF EXISTS public.cliente_vizu
  ADD COLUMN IF NOT EXISTS ferramenta_sql_habilitada boolean DEFAULT false NOT NULL;

ALTER TABLE IF EXISTS public.cliente_vizu
  ADD COLUMN IF NOT EXISTS ferramenta_agendamento_habilitada boolean DEFAULT false NOT NULL;

ALTER TABLE IF EXISTS public.cliente_vizu
  ADD COLUMN IF NOT EXISTS collection_rag text;

-- Copy data from legacy configuracao_negocio if it exists
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'configuracao_negocio') THEN
    UPDATE public.cliente_vizu cv
    SET horario_funcionamento = cn.horario_funcionamento,
        prompt_base = cn.prompt_base,
        ferramenta_rag_habilitada = COALESCE(cn.ferramenta_rag_habilitada, false),
        ferramenta_sql_habilitada = COALESCE(cn.ferramenta_sql_habilitada, false),
        ferramenta_agendamento_habilitada = COALESCE(cn.ferramenta_agendamento_habilitada, false),
        collection_rag = cn.collection_rag
    FROM public.configuracao_negocio cn
    WHERE cn.cliente_vizu_id = cv.id;
  END IF;
END
$$;

-- Note: Do NOT drop the legacy table here. Remove it in a follow-up migration
-- after the application has been deployed to read the new columns.
