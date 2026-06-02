---
name: fragment/sql-examples
category: system
version: 1
required_variables: []
optional_variables: {}
---

<!--
This file is the in-repo fallback for prompt `fragment/sql-examples`.
It is used when Langfuse is unreachable. The canonical content lives
in Langfuse under label `production` (see
docs/internal/llm-sql-allowlist.md and the Phase 0 / F0.5 audit).

Description: SQL query pattern examples
-->

# SQL QUERY PATTERNS

```sql
-- Receita últimos 30 dias
SELECT SUM(f.valor) AS receita, COUNT(*) AS transacoes
FROM analytics_v2.fato_transacoes f
JOIN analytics_v2.dim_datas d ON f.data_competencia_id = d.data_id
WHERE d.data >= CURRENT_DATE - INTERVAL '30 days';

-- Top 10 fornecedores por receita
SELECT s.nome, SUM(f.valor) AS receita, COUNT(*) AS pedidos
FROM analytics_v2.fato_transacoes f
JOIN analytics_v2.dim_fornecedores s ON f.fornecedor_id = s.fornecedor_id
GROUP BY s.nome ORDER BY receita DESC LIMIT 10;

-- Tendência mensal (últimos 12 meses)
SELECT d.ano, d.mes, SUM(f.valor) AS receita
FROM analytics_v2.fato_transacoes f
JOIN analytics_v2.dim_datas d ON f.data_competencia_id = d.data_id
WHERE d.data >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY d.ano, d.mes ORDER BY d.ano, d.mes;

-- Faturamento mês atual vs mês anterior
WITH cur AS (
  SELECT SUM(f.valor) AS receita
  FROM analytics_v2.fato_transacoes f
  JOIN analytics_v2.dim_datas d ON f.data_competencia_id = d.data_id
  WHERE d.ano = EXTRACT(YEAR FROM CURRENT_DATE)
    AND d.mes = EXTRACT(MONTH FROM CURRENT_DATE)
), prev AS (
  SELECT SUM(f.valor) AS receita
  FROM analytics_v2.fato_transacoes f
  JOIN analytics_v2.dim_datas d ON f.data_competencia_id = d.data_id
  WHERE d.ano = EXTRACT(YEAR FROM CURRENT_DATE - INTERVAL '1 month')
    AND d.mes = EXTRACT(MONTH FROM CURRENT_DATE - INTERVAL '1 month')
)
SELECT cur.receita AS mes_atual, prev.receita AS mes_anterior
FROM cur CROSS JOIN prev;

-- Receita por categoria
SELECT f.categoria, SUM(f.valor) AS receita
FROM analytics_v2.fato_transacoes f
GROUP BY f.categoria ORDER BY receita DESC;

-- Últimas transações
SELECT f.transacao_id, d.data, s.nome AS fornecedor, f.valor, f.categoria
FROM analytics_v2.fato_transacoes f
JOIN analytics_v2.dim_datas d ON f.data_competencia_id = d.data_id
JOIN analytics_v2.dim_fornecedores s ON f.fornecedor_id = s.fornecedor_id
ORDER BY d.data DESC LIMIT 10;
```
