# Métricas da Analytics Strip por Sala

**Fonte de dados:** `analytics_v2.fato_transacoes` (join `dim_datas`, `dim_clientes`, `dim_inventory`)
**Função DB:** `analytics_v2.get_context_metrics_for_client(p_client_id uuid, p_period text)`
**Wrapper público:** `public.get_my_context_metrics(p_period text DEFAULT '30d')`
**API frontend:** `getContextMetrics(period?)` em `apps/blu_v3/src/api/analytics.ts`

---

## Parâmetro de Período

O usuário pode selecionar o período via pills na sala (30d / 90d / 1 ano). O valor é passado diretamente como `p_period`.

| `p_period` | Janela atual (`n` meses) | Janela de comparação |
|---|---|---|
| `30d` (padrão) | Mês de referência (1 mês) | Mês imediatamente anterior |
| `90d` | Últimos 3 meses | 3 meses antes disso |
| `1y` | Últimos 12 meses | 12 meses antes disso |
| qualquer outro | 1 mês (fallback) | Mês anterior |

**Mês de referência (`ref_month`):** mês atual se já houver dados; caso contrário, o último mês com dados.

**Filtro base:** `dd.data < CURRENT_DATE` — exclui o dia de hoje para evitar distorção por dados parciais.

---

## Campos retornados por métrica

| Campo | Descrição |
|---|---|
| `current_value` | Valor agregado na janela atual |
| `prev_month_value` | Mesmo agregado na janela de comparação (período anterior) |
| `mom_pct` | `(current - prev) / prev * 100` — variação entre as duas janelas |
| `avg_6m` | Média dos últimos 6 meses completos (sempre mensal, independente do período selecionado) |
| `vs_6m_avg_pct` | `(current - avg_6m) / avg_6m * 100` |
| `streak_months` | Meses consecutivos na mesma direção (positivo = crescendo, negativo = caindo) |

> `avg_6m` e `streak_months` são sempre calculados sobre `complete_months` (histórico completo), **não** são filtrados pelo `p_period`.
> As métricas estáticas (`receita_ytd`, `skus_total`, `clientes_base_total`, `clientes_ativos_90d`, `recencia_media_dias`) retornam `prev_month_value`, `avg_6m`, `mom_pct`, `vs_6m_avg_pct` e `streak_months` como `NULL` / `0`.

---

## Sala Financeiro (`dimension: finance`)

### `receita_liquida` — Receita Líquida (R$)
```
current_value = SUM(ft.valor) sobre todos os meses da janela atual
```
Soma total de valor de transações no período. Métrica **aditiva** — acumula os meses da janela.

---

### `ticket_medio` — Ticket Médio (R$)
```
current_value = SUM(receita) / SUM(total_pedidos)  [na janela atual]
               = 0 se total_pedidos = 0
```
Receita total dividida pelo número total de pedidos únicos no período. Recalculado diretamente pela janela (não é média de tickets mensais).

---

### `total_pedidos` — Total de Pedidos (count)
```
current_value = SUM( COUNT(DISTINCT ft.transacao_id) por mês ) sobre a janela atual
```
Soma de pedidos únicos mês a mês. Métrica **aditiva**.

---

### `receita_ytd` — Receita Acumulada (YTD) (R$)
```
current_value = SUM(ft.valor)
  WHERE EXTRACT(YEAR FROM dd.data) = EXTRACT(YEAR FROM CURRENT_DATE)
    AND dd.data < CURRENT_DATE
```
Sempre acumula desde 1º de janeiro do ano corrente até ontem. **Ignora `p_period`** — janela fixa anual.
Não tem `prev_month_value`, `avg_6m`, `mom_pct` nem `streak_months`.

---

## Sala Clientes (`dimension: commercial`)

### `clientes_unicos` — Clientes Únicos (count)
```
current_value = clientes_unicos do mês mais recente na janela (current_latest)
             = COUNT(DISTINCT ft.customer_id) naquele mês
```
Métrica de **snapshot** — pega o valor do mês mais recente da janela, não acumula.

---

### `clientes_novos` — Clientes Novos (count)
```
current_value = SUM(clientes_novos por mês) na janela atual
clientes_novos_M = COUNT(customers) cujo primeiro pedido foi no mês M
                 = COUNT(*) FROM first_purchases WHERE first_month = M
```
Acumula os novos clientes de cada mês dentro da janela. Métrica **aditiva**.

---

### `clientes_recorrentes` — Clientes Recorrentes (count)
```
current_value = SUM(clientes_recorrentes por mês) na janela atual
clientes_recorrentes_M = COUNT(customers que compraram em M E em M-1)
```
Cliente recorrente = comprou no mês M **e** também no mês M−1. Métrica **aditiva** sobre a janela.

---

### `taxa_recorrencia_perc` — Taxa de Recorrência (%)
```
taxa_recorrencia_perc_M = ROUND(clientes_recorrentes_M / clientes_unicos_(M-1) * 100, 1)
                        = 0 se clientes_unicos_(M-1) = 0

current_value = AVG(taxa_recorrencia_perc_M) sobre os meses da janela atual
```
Proporção de clientes que repetiram compra em relação à base do mês anterior. Calculada mês a mês e depois **média** da janela.

---

### `receita_por_cliente` — Receita por Cliente (R$)
```
current_value = SUM(receita) / MAX(clientes_unicos)  [na janela]
             = 0 se clientes_unicos = 0
```
Receita total do período dividida pelo pico de clientes únicos na janela.

---

### `frequencia_media` — Frequência Média de Compra (count)
```
current_value = SUM(total_pedidos) / MAX(clientes_unicos)  [na janela]
             = 0 se clientes_unicos = 0
```
Quantos pedidos, em média, cada cliente fez no período.

---

### `concentracao_top3_clientes_perc` — Concentração Top 3 Clientes (%)
```
-- por mês:
concentracao_M = SUM(receita dos 3 maiores clientes no mês M) / SUM(receita total no mês M) * 100

current_value = AVG(concentracao_M) sobre os meses da janela atual
```
Participação dos 3 clientes de maior receita no total. Calcula por mês e tira **média** da janela.

---

### `clientes_base_total` — Total de Clientes (base) (count)
```
current_value = COUNT(*) FROM analytics_v2.dim_clientes WHERE client_id = p_client_id
```
Total histórico de clientes cadastrados na dimensão (sem filtro de período). **Sem comparação, avg_6m ou streak.**

---

### `clientes_ativos_90d` — Clientes Ativos (últimos 90 dias) (count)
```
current_value = COUNT(*) FROM analytics_v2.dim_clientes
  WHERE client_id = p_client_id
    AND dias_recencia IS NOT NULL
    AND dias_recencia <= 90
```
Sempre janela de 90 dias fixos (campo `dias_recencia` pré-calculado na dim). **Ignora `p_period`**. **Sem comparação, avg_6m ou streak.**

---

### `recencia_media_dias` — Recência Média da Base (dias) (days)
```
current_value = ROUND(AVG(dias_recencia), 0)
  FROM analytics_v2.dim_clientes
  WHERE client_id = p_client_id AND dias_recencia IS NOT NULL
```
Média de dias desde a última compra de todos os clientes da base. Campo estático da `dim_clientes`. **Sem comparação, avg_6m ou streak.**

---

## Sala Compras — Supply (`dimension: supply`)

### `fornecedores_ativos` — Fornecedores Ativos (count)
```
current_value = fornecedores_ativos do mês mais recente na janela (current_latest)
             = COUNT(DISTINCT ft.fornecedor_id) naquele mês
```
Snapshot do mês mais recente da janela, **não acumula**.

---

### `receita_por_fornecedor` — Receita por Fornecedor (R$)
```
current_value = SUM(receita) / MAX(fornecedores_ativos)  [na janela]
             = 0 se fornecedores_ativos = 0
```
Receita total do período dividida pelo pico de fornecedores ativos.

---

### `concentracao_top1_fornecedor_perc` — Concentração Top Fornecedor (%)
```
-- por mês:
top1_M = MAX(receita de um único fornecedor no mês M) / SUM(receita total no mês M) * 100

current_value = AVG(top1_M) sobre os meses da janela atual
```
Participação do **maior** fornecedor na receita total. Calculada por mês e **média** na janela.

---

### `concentracao_top3_fornecedores_perc` — Concentração Top 3 Fornecedores (%)
```
-- por mês:
top3_M = SUM(receita dos 3 maiores fornecedores no mês M) / SUM(receita total no mês M) * 100

current_value = AVG(top3_M) sobre os meses da janela atual
```
Participação dos 3 maiores fornecedores. Calculada por mês e **média** na janela.

---

## Sala Compras — Inventory (`dimension: inventory`)

### `skus_ativos` — SKUs Ativos no Mês (count)
```
current_value = skus_ativos do mês mais recente na janela (current_latest)
             = COUNT(DISTINCT ft.produto_id) naquele mês
```
Snapshot do mês mais recente da janela, **não acumula**.

---

### `quantidade_vendida` — Quantidade Vendida (count)
```
current_value = SUM(ft.quantidade) sobre os meses da janela atual
```
Soma de unidades vendidas no período. Métrica **aditiva**.

---

### `receita_por_sku` — Receita por SKU Ativo (R$)
```
current_value = SUM(receita) / MAX(skus_ativos)  [na janela]
             = 0 se skus_ativos = 0
```
Receita total dividida pelo pico de SKUs distintos com venda na janela.

---

### `concentracao_top3_produtos_perc` — Concentração Top 3 Produtos (%)
```
-- por mês:
top3_M = SUM(receita dos 3 maiores SKUs no mês M) / SUM(receita total no mês M) * 100

current_value = AVG(top3_M) sobre os meses da janela atual
```
Participação dos 3 SKUs de maior receita no total. Por mês e **média** na janela.

---

### `skus_total` — Total de SKUs (catálogo) (count)
```
current_value = COUNT(*) FROM analytics_v2.dim_inventory WHERE client_id = p_client_id
```
Total de produtos no catálogo (tabela de inventário, sem filtro de período). **Sem comparação, avg_6m ou streak.**

---

## Sala Estratégia (`dimension: estrategia`)

Sem métricas — a dimensão `estrategia` está configurada no frontend mas não existe no backend.
A função `get_context_metrics_for_client` não produz linhas com esse valor; o painel fica sempre vazio.

---

## Notas de implementação

- **Comportamento de snapshot vs. aditivo:** métricas como `clientes_unicos`, `skus_ativos` e `fornecedores_ativos` representam a realidade do **mês mais recente** da janela. Métricas como `receita_liquida`, `total_pedidos` e `clientes_novos` **acumulam** todos os meses da janela.
- **Métricas estáticas** (`receita_ytd`, `skus_total`, `clientes_base_total`, `clientes_ativos_90d`, `recencia_media_dias`) não participam do cálculo de `mom_pct`, `avg_6m` ou `streak_months`.
- **`avg_6m` e `streak_months`** são sempre calculados sobre `complete_months` (todo o histórico de meses fechados), independente do `p_period` selecionado.
- Componente de renderização: `apps/blu_v3/src/components/shared/KpiMetricsPanel.tsx`
- API: `apps/blu_v3/src/api/analytics.ts` → `getContextMetrics(period?)`
