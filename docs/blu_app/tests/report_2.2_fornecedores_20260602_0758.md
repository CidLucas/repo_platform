# QA Report — 2.2 fornecedores
**Run date:** 2026-06-02 07:58  
**Skill tested:** compras_ops (ID 2.2)  
**Expected tool:** add_supplier  
**Expected agent:** compras  
**Tester client:** 6446d4fa-b845-4d1b-b3a3-ceed2dda6d44  

---

## 1. Summary

| Metric | Value |
|---|---|
| Pass rate | 0/5 |
| Root cause | `ROUTING_CONFIG` (frontdesk table mismatch) + `PROMPT_STATIC` (skill:compras_ops:system 404) |
| Draft written | YES — `skill:compras_ops:system` v1 (created from scratch) + `agents/frontdesk` v23 |
| Context issues | None blocking — context service not the cause |

All 5 TCs were misrouted to `context-gatherer` instead of `compras`. Two layered failures:
1. **Langfuse 404**: `skill:compras_ops:system` not published → compras agent runs with empty system prompt (even if routed correctly, it would hallucinate)
2. **Frontdesk routing table**: Row `"Cadastrar ou atualizar fornecedor, produto, cliente (escrita)" → data-entry` overrides the supplier-management domain, sending all supplier-CRUD intents to `data-entry` (which maps to `context-gatherer`)

---

## 2. Context Service — Client 6446d4fa

| Section | Status | Notes |
|---|---|---|
| company_profile | Not checked (not blocking) | Routing failure precedes context use |
| brand_voice | Not checked | — |
| team_structure | Not checked | — |
| policies | Not checked | — |
| data_schema | Not checked | — |
| available_tools | Not checked | — |

**Context service diagnosis**: `CONTEXT_MISSING` is NOT the root cause here. The failures are upstream: routing table and missing Langfuse prompt.

**Default system prompt override**: Not present (compras uses skill:compras_ops:system via Langfuse, which is 404 → empty).

---

## 3. TC Results

| TC | Message (excerpt) | HTTP | Agent routed | Tool called | Expected | Result |
|---|---|---|---|---|---|---|
| TC1 | Quero cadastrar um novo fornecedor chamado Distribuidora Alfa… | 200 | context-gatherer | *(none)* | compras / add_supplier | ❌ FAIL |
| TC2 | Preciso adicionar um fornecedor: Impressões Rápidas LTDA… | 200 | context-gatherer | *(none)* | compras / add_supplier | ❌ FAIL |
| TC3 | adiciona aí: Tech Supplies Comércio… | 200 | context-gatherer | *(none)* | compras / add_supplier | ❌ FAIL |
| TC4 | Cadastra o fornecedor Forno & Chama Equipamentos… | 200 | context-gatherer | *(none)* | compras / add_supplier | ❌ FAIL |
| TC5 | Preciso incluir no sistema a empresa Metal Works Indústria… | 200 | context-gatherer | *(none)* | compras / add_supplier | ❌ FAIL |

### Agent responses observed

- TC1: Confirmed fields back to user, asked for confirmation — but as context-gatherer, not compras (no tool call)
- TC2: "Desculpe, ocorreu um erro" — silent failure in context-gatherer  
- TC3: "Vou registrar os dados para garantir que o contexto esteja atualizado" — KB write intent, not add_supplier
- TC4: Offered to "registrar" the info — context-gatherer storing text, not calling add_supplier
- TC5: "Entendi que você deseja cadastrar... Para confirmar..." — asked for confirmation but no tool execution

---

## 4. Root Cause Breakdown

| TC | Root Cause | Class | Priority |
|---|---|---|---|
| TC1 | Frontdesk routing table maps supplier CRUD → data-entry (context-gatherer) | `ROUTING_CONFIG` | P1 |
| TC2 | Same + context-gatherer crashes silently on write | `ROUTING_CONFIG` | P1 |
| TC3 | Same | `ROUTING_CONFIG` | P1 |
| TC4 | Same | `ROUTING_CONFIG` | P1 |
| TC5 | Same | `ROUTING_CONFIG` | P1 |
| All | `skill:compras_ops:system` 404 in Langfuse → empty system prompt even if correctly routed | `PROMPT_STATIC` | P1 |

### Detailed diagnosis

**Root Cause 1 — Frontdesk routing table (ROUTING_CONFIG)**

In `agents/frontdesk` (Langfuse production v22), the routing table contains:
```
| Cadastrar ou atualizar fornecedor, produto, cliente (escrita) | `data-entry` |
```
This catches all supplier registration intents ("cadastrar fornecedor", "adicionar fornecedor") and routes to `data-entry` instead of `compras`. The `_SLUG_ALIASES` in `common_module.py` correctly maps `"fornecedor" → "compras"` and `"add_supplier" → "compras"`, but this is only consulted AFTER the frontdesk LLM calls `route_to_specialist`. The frontdesk LLM, guided by the routing table, emits `data-entry` as the slug, which `_SLUG_ALIASES` maps to `context-gatherer`.

**Root Cause 2 — Missing Langfuse prompt (PROMPT_STATIC)**

`skill:compras_ops:system` returns 404 in Langfuse. Builtin fallback is disabled per the May-2026 loader fix. The `compras` agent would run with an empty system prompt, causing hallucinated responses even if routing worked. This is a pre-existing gap: the builtin template (`SKILL_COMPRAS_OPS`) in `templates.py` is correct but was never published to Langfuse.

---

## 5. Prompt Improvements Applied

### Fix 1: `skill:compras_ops:system` — CREATED FROM SCRATCH (v1 draft)

**Previous state:** 404 (not in Langfuse)  

**New draft written to Langfuse:**
```
Você é o **Especialista de Compras** da **{{ nome_empresa }}** — responsável pelo ciclo completo de procurement e gestão de fornecedores.

[Identity header + company_profile variable]

<Instructions>
1. Gestão de fornecedores: list_suppliers, add_supplier (name obrigatório), update_supplier, remove_supplier
2. Cadastro: confirmar dados antes de criar, então chamar add_supplier
3. Lista de compras: parse → validate → optimize → generate_po_report
4. RFQ: dispatch_rfq → check_rfq_responses → suggest_counter_offer
5. Pedidos: create_purchase_order (com confirmação) → approve_purchase_order (idem)
</Instructions>

<Tool Rules>
- add_supplier: name obrigatório; apresentar confirmação antes de criar
- create_purchase_order / approve_purchase_order: SEMPRE requer confirmação explícita
- Nunca pular validate_buying_list antes de optimize_allocation
</Tool Rules>

<Constraints>
- Não enviar RFQs sem rfq_requests ativo
- Máximo 6 turnos por cotação
- Se sem fornecedores cadastrados, orientar usuário a usar add_supplier
</Constraints>

<Output Format>
- Cadastro: "✅ Fornecedor **[Nome]** cadastrado com sucesso! ID: [id]"
- Listagem: tabela Markdown Nome | Email | Telefone | Categorias | Prazo
- RFQ: tabela com Fornecedor | Preço | Prazo | Condições
</Output Format>
```
**Action required:** Promote `skill:compras_ops:system` draft v1 → `production` in Langfuse UI.

---

### Fix 2: `agents/frontdesk` — Routing table updated (v23 draft)

**Previous (production v22):**
```
| Cadastrar ou atualizar fornecedor, produto, cliente (escrita) | `data-entry` |
```

**New (draft v23):**
```
| Cadastrar ou atualizar fornecedor (add_supplier, gestão de cadastro de fornecedores) | `compras` |
| Registrar transação, venda, despesa, produto ou cliente (escrita no ledger) | `data-entry` |
```

This splits the broad "write ops" row into:
- Supplier CRUD → `compras` (correct specialist)
- Ledger / transaction writes → `data-entry` (keeps the existing path)

**Action required:** Promote `agents/frontdesk` draft v23 → `production` in Langfuse UI. Then rebuild/restart is NOT needed (prompt is loaded dynamically). Test with TC1-TC5 after promotion.

---

## 6. Manual Fixes Needed

| Fix | Type | File / Location | Priority |
|---|---|---|---|
| Publish `skill:compras_ops:system` to production | Langfuse promotion | Langfuse UI → Prompts → skill:compras_ops:system → promote v1 draft | P1 |
| Publish `agents/frontdesk` v23 to production | Langfuse promotion | Langfuse UI → Prompts → agents/frontdesk → promote v23 draft | P1 |
| Confirm builtin `SKILL_COMPRAS_OPS` in `_L3_SKILL_TEMPLATE_MAP` | Code audit | `libs/blu_prompt_management/src/blu_prompt_management/templates.py` | P2 |

**Note:** No source code modifications required for these fixes — both are pure Langfuse prompt updates.

---

## 7. Re-run Results (TC2 and TC4)

| TC | 1st run | Re-run | Consistent? |
|---|---|---|---|
| TC2 | context-gatherer, no tool | context-gatherer, no tool | ✅ Deterministic FAIL |
| TC4 | context-gatherer, no tool | context-gatherer, no tool | ✅ Deterministic FAIL |

Re-runs confirm the failure is **deterministic** (not flaky). Both runs route to `context-gatherer`. The fix is architectural (routing table + missing Langfuse prompt), not probabilistic.

---

## 8. Next Recommended Actions

1. **[IMMEDIATE P1]** Promote `agents/frontdesk` draft v23 to `production` in Langfuse UI — this fixes the routing table. After promotion, supplier CRUD intents will correctly reach the `compras` agent.

2. **[IMMEDIATE P1]** Promote `skill:compras_ops:system` draft v1 to `production` — prevents empty system prompt when `compras` agent runs the skill.

3. **[VERIFY]** After promotions, re-run all 5 TCs manually to confirm: `agent_slug = "compras"` and `tool_calls` contains `add_supplier`.

4. **[P2 — code audit]** Verify that `SKILL_COMPRAS_OPS` is included in `_L3_SKILL_TEMPLATES` list in `templates.py` so the builtin fallback works if Langfuse becomes unavailable again.

5. **[NEXT CRON]** Proceed to 2.3 `platform_ops` (criar_rotina).
