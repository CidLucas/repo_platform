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
-- Top 10 fornecedores por receita
SELECT f2.nome, SUM(f.valor) as receita
FROM analytics_v2.fato_transacoes f
JOIN analytics_v2.dim_fornecedores f2 USING (fornecedor_id)
GROUP BY f2.nome ORDER BY receita DESC LIMIT 10;

-- Top 10 cidades por receita
SELECT c.endereco_cidade as cidade, SUM(f.valor) as receita
FROM analytics_v2.fato_transacoes f
JOIN analytics_v2.dim_clientes c USING (cliente_id)
WHERE c.endereco_cidade IS NOT NULL
GROUP BY c.endereco_cidade ORDER BY receita DESC LIMIT 10;

-- Tendência mensal (últimos 12 meses)
SELECT d.nome_mes, d.ano, SUM(f.valor) as receita
FROM analytics_v2.fato_transacoes f
JOIN analytics_v2.dim_datas d ON f.data_competencia_id = d.data_id
WHERE d.data >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY d.ano, d.mes, d.nome_mes ORDER BY d.ano, d.mes;
```
