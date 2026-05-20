-- =============================================================================
-- Migration: Phase 2 — analytics_v2 tables baseline
-- Date: 2026-04-28
-- Purpose: Create analytics_v2 dimension, fact, and job table structures
-- =============================================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS analytics_v2;

-- -----------------------------------------------------------------------------
-- dim_datas
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics_v2.dim_datas (
  data_id              BIGINT  PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  data                 DATE    NOT NULL UNIQUE,
  ano                  INTEGER NOT NULL,
  mes                  INTEGER NOT NULL,
  dia                  INTEGER NOT NULL,
  numero_dia_semana    INTEGER,
  numero_semana_ano    INTEGER,
  numero_semestre      INTEGER,
  periodo_trimestral   TEXT,
  created_at           TIMESTAMPTZ DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- dim_clientes
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics_v2.dim_clientes (
  client_id           BIGINT  PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  client_id            UUID    REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  cpf_cnpj             TEXT,
  nome                 TEXT,
  telefone             TEXT,
  endereco_cidade      TEXT,
  endereco_uf          TEXT,
  total_pedidos        BIGINT  DEFAULT 0,
  receita_total        NUMERIC(15,2) DEFAULT 0,
  ticket_medio         NUMERIC(15,2) DEFAULT 0,
  quantidade_total     NUMERIC DEFAULT 0,
  frequencia_mensal    NUMERIC,
  dias_recencia        INTEGER,
  data_primeira_compra DATE,
  data_ultima_compra   DATE,
  pontuacao_cluster    NUMERIC,
  nivel_cluster        TEXT,
  atualizado_em        TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_dim_clientes_client ON analytics_v2.dim_clientes(client_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_clientes_cpf_cnpj ON analytics_v2.dim_clientes(client_id, cpf_cnpj) WHERE cpf_cnpj IS NOT NULL;

-- -----------------------------------------------------------------------------
-- dim_fornecedores
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics_v2.dim_fornecedores (
  fornecedor_id               BIGINT  PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  client_id                   UUID    REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  cnpj                        TEXT,
  nome                        TEXT,
  telefone                    TEXT,
  endereco_cidade             TEXT,
  endereco_uf                 TEXT,
  total_pedidos_recebidos     BIGINT  DEFAULT 0,
  receita_total               NUMERIC(15,2) DEFAULT 0,
  ticket_medio                NUMERIC(15,2) DEFAULT 0,
  total_produtos_fornecidos   BIGINT  DEFAULT 0,
  frequencia_mensal           NUMERIC,
  dias_recencia               INTEGER,
  data_primeira_transacao     DATE,
  data_ultima_transacao       DATE,
  pontuacao_cluster           NUMERIC,
  nivel_cluster               TEXT,
  atualizado_em               TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_dim_forn_client ON analytics_v2.dim_fornecedores(client_id);

-- -----------------------------------------------------------------------------
-- dim_inventory
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics_v2.dim_inventory (
  inventory_id               BIGINT  PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  client_id                  UUID    REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  sku                        TEXT,
  nome                       TEXT,
  quantidade_total_vendida   NUMERIC DEFAULT 0,
  receita_total              NUMERIC(15,2) DEFAULT 0,
  preco_medio                NUMERIC(15,2) DEFAULT 0,
  total_pedidos              BIGINT  DEFAULT 0,
  quantidade_media_por_pedido NUMERIC,
  frequencia_mensal          NUMERIC,
  dias_recencia              INTEGER,
  data_ultima_venda          DATE,
  pontuacao_cluster          NUMERIC,
  nivel_cluster              TEXT,
  created_at                 TIMESTAMPTZ DEFAULT now(),
  updated_at                 TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_dim_inv_client ON analytics_v2.dim_inventory(client_id);

-- -----------------------------------------------------------------------------
-- fato_transacoes
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics_v2.fato_transacoes (
  transacao_id          TEXT    NOT NULL,
  client_id             UUID    NOT NULL REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  data_competencia_id   BIGINT  REFERENCES analytics_v2.dim_datas(data_id) ON DELETE SET NULL,
  client_id            BIGINT  REFERENCES analytics_v2.dim_clientes(client_id) ON DELETE SET NULL,
  fornecedor_id         BIGINT  REFERENCES analytics_v2.dim_fornecedores(fornecedor_id) ON DELETE SET NULL,
  produto_id            BIGINT  REFERENCES analytics_v2.dim_inventory(inventory_id) ON DELETE SET NULL,
  documento             TEXT,
  quantidade            NUMERIC,
  valor_unitario        NUMERIC(15,2),
  valor                 NUMERIC(15,2),
  status                TEXT,
  created_at            TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (transacao_id, client_id)
);
CREATE INDEX IF NOT EXISTS idx_fato_client ON analytics_v2.fato_transacoes(client_id);
CREATE INDEX IF NOT EXISTS idx_fato_data ON analytics_v2.fato_transacoes(data_competencia_id);
CREATE INDEX IF NOT EXISTS idx_fato_cliente_dim ON analytics_v2.fato_transacoes(client_id);
CREATE INDEX IF NOT EXISTS idx_fato_fornecedor ON analytics_v2.fato_transacoes(fornecedor_id);

-- -----------------------------------------------------------------------------
-- reg_jobs
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics_v2.reg_jobs (
  job_id        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id     UUID        REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  job_type      TEXT        NOT NULL DEFAULT 'bigquery_sync'
                CHECK (job_type IN ('bigquery_sync','connector_sync','analytics_etl','custom')),
  credential_id BIGINT      REFERENCES public.credencial_servico_externo(id) ON DELETE SET NULL,
  resource_type TEXT,
  sync_mode     TEXT        DEFAULT 'incremental' CHECK (sync_mode IN ('incremental','full')),
  status        TEXT        NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','running','completed','failed','cancelled')),
  input_params  JSONB       DEFAULT '{}',
  output        JSONB,
  rows_inserted BIGINT      DEFAULT 0,
  progress_pct  INTEGER     DEFAULT 0,
  error_message TEXT,
  started_at    TIMESTAMPTZ,
  completed_at  TIMESTAMPTZ,
  duration_seconds NUMERIC,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_reg_jobs_client_status ON analytics_v2.reg_jobs(client_id, status);
CREATE INDEX IF NOT EXISTS idx_reg_jobs_created ON analytics_v2.reg_jobs(created_at DESC);

COMMIT;
