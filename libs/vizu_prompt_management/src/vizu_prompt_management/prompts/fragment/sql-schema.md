---
name: fragment/sql-schema
category: system
version: 1
required_variables: []
optional_variables: {}
---

<!--
This file is the in-repo fallback for prompt `fragment/sql-schema`.
It is used when Langfuse is unreachable. The canonical content lives
in Langfuse under label `production` (see
docs/internal/llm-sql-allowlist.md and the Phase 0 / F0.5 audit).

Description: Analytics V2 star schema reference
-->

# DATABASE SCHEMA (Analytics V2 — Star Schema)

All tables in schema `analytics_v2`. Security filtering by `client_id` is applied AUTOMATICALLY — NEVER include it in queries.

## Fact: `analytics_v2.fato_transacoes`
| Column | Type | Notes |
|--------|------|-------|
| `transacao_id` | UUID | PK |
| `cliente_id` | UUID | FK → dim_clientes |
| `fornecedor_id` | UUID | FK → dim_fornecedores |
| `inventory_id` | UUID | FK → dim_inventory |
| `data_competencia_id` | INT | FK → dim_datas.data_id |
| `tipo_id` | INT | FK → dim_tipo_transacao |
| `categoria_id` | UUID | FK → dim_categoria |
| `documento` | TEXT | Document reference |
| `quantidade` | NUMERIC | Quantity |
| `valor` | NUMERIC | **Total amount (BRL)** — USE THIS for revenue |

## Dim: `analytics_v2.dim_clientes`
cliente_id UUID PK, nome, cpf_cnpj, endereco_cidade, endereco_uf, receita_total, total_pedidos, ticket_medio, dias_recencia, frequencia_mensal, pontuacao_cluster, nivel_cluster

## Dim: `analytics_v2.dim_fornecedores`
fornecedor_id UUID PK, nome, cnpj, endereco_cidade, endereco_uf, receita_total, total_pedidos_recebidos, ticket_medio, dias_recencia, frequencia_mensal

## Dim: `analytics_v2.dim_inventory`
inventory_id UUID PK, sku, nome (USE FOR ILIKE), receita_total, quantidade_total_vendida, preco_medio, total_pedidos, current_stock

## Dim: `analytics_v2.dim_datas`
data_id INT PK (YYYYMMDD), data DATE (USE FOR filtering), ano, mes, nome_mes, trimestre, dia_da_semana, e_fim_de_semana
⚠️ JOIN: fato_transacoes.data_competencia_id = dim_datas.data_id (USE ON, not USING)

## Dim: `analytics_v2.dim_tipo_transacao`
tipo_id INT PK, descricao, categoria, natureza_operacional, impacto_caixa

## JOIN REFERENCE
```
fato_transacoes.cliente_id        → dim_clientes.cliente_id         (USING works)
fato_transacoes.fornecedor_id     → dim_fornecedores.fornecedor_id  (USING works)
fato_transacoes.inventory_id      → dim_inventory.inventory_id      (USING works)
fato_transacoes.tipo_id           → dim_tipo_transacao.tipo_id      (USING works)
fato_transacoes.data_competencia_id → dim_datas.data_id             (⚠️ USE ON clause!)
```
