# Test Cases — 2.4 platform_ops (definir_meta)
**Gerado em:** 2026-06-02 09:44
**Skill:** platform_ops | **Expected Tool:** definir_meta | **Agent:** platform

## TC1 — Formal, explicit, specific metric
> "Preciso definir uma meta de faturamento de R$80.000 para este mês de junho."

**Expected:** route to platform agent → call `definir_meta` with dimension=financeiro, target=80000

## TC2 — Informal, implicit goal-setting intent
> "cara, quero bater 100 clientes ativos até o fim do mês"

**Expected:** route to platform agent → call `definir_meta` with dimension=clientes, target=100

## TC3 — Formal, updating existing goal
> "Atualize minha meta de faturamento para R$120.000 — consegui superar o objetivo anterior."

**Expected:** route to platform agent → call `definir_meta` (update existing)

## TC4 — Informal, vague but intent clear
> "minha meta pra esse trimestre é reduzir os custos em 15%"

**Expected:** route to platform agent → elicit clarification or call `definir_meta` with dimension=compras/custos

## TC5 — Formal, listing then creating a new goal
> "Quero ver minhas metas atuais e depois adicionar uma nova meta de vendas de 500 pedidos para julho."

**Expected:** route to platform agent → call `listar_metas` then `definir_meta`
