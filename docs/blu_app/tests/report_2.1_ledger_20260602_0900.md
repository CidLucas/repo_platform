# Report 2.1 — ledger — 2026-06-02 09:00

## 1. Summary

| Field | Value |
|---|---|
| Skill | 2.1 `ledger` |
| Agent slug | `data-entry` |
| Expected tool | `register_transaction` |
| Pass rate | **0/5 (0%)** |
| Draft prompt written | **NO** — root cause is P0 code bug, not prompt |
| Context issues | None confirmed (not the bottleneck) |
| Run date | 2026-06-02 09:00 |

All 5 test cases routed to `context-gatherer` instead of `data-entry`. Root cause is a **P0 ROUTING_CONFIG** bug in `_SLUG_ALIASES` in `common_module.py`.

---

## 2. Context Service (Step 3)

### 3a — Prompt Loader

| Prompt key | Status |
|---|---|
| `skill:ledger:system` | ✅ EXISTS (type=str, production label) — contains HITL workflow, register_transaction rules |
| `agents/data-entry` | ✅ EXISTS (type=str, production label) — rich PT-BR prompt with XML sections |
| `agents/frontdesk` | `'LoadedPrompt' object is not subscriptable` (type=chat issue in loader — known bug) |

**Note:** The loader's `'LoadedPrompt' object is not subscriptable` error on `agents/frontdesk` confirms the type=chat bug is still present and may affect frontdesk behavior.

### 3b — Tool Description

`register_transaction` is defined in `context_module.py` (line ~949). Tool exists and is correctly registered.

### 3c — Skill Routing in skills.py

`ledger` skill (line 496): `required_tool_names=["register_transaction", "execute_sql"]`, `prompt_name="skill:ledger:system"`, assigned to `data-entry` agent via `skill_slugs=["ledger", ...]`.

### 3d — Context Service

Not executed (ContextService requires Redis — docker exec approach used instead).

---

## 3. TC Results Table

| TC | Message (summary) | HTTP | Routed to | Expected | Tool called | Result |
|---|---|---|---|---|---|---|
| TC1 | Registrar venda R$4.800 Construtora Alfa | 200 | `context-gatherer` | `data-entry` | none | ❌ FAIL |
| TC2 | Lançar compra material escritório R$350 | 200 | `context-gatherer` | `data-entry` | none | ❌ FAIL |
| TC3 | Despesa R$1.200 aluguel galpão 28/05 | 200 | `context-gatherer` | `data-entry` | none | ❌ FAIL |
| TC4 | Recebi pagamento R$9.500 João Silva | 200 | `context-gatherer` | `data-entry` | none | ❌ FAIL |
| TC5 | Saída R$780 combustível frota | 200 | `context-gatherer` | `data-entry` | none | ❌ FAIL |

**Pass rate: 0/5**

---

## 4. Root Cause Breakdown

| Root Cause | Count | TCs | Description |
|---|---|---|---|
| `ROUTING_CONFIG` (P0) | 5 | TC1–TC5 | `_SLUG_ALIASES` in `common_module.py` maps `register_transaction`, `data_entry`, `transacao`, `transaction`, `registro` → `"context-gatherer"` instead of `"data-entry"` |

### Root Cause Detail

**File:** `services/tool_pool_api/src/tool_pool_api/server/tool_modules/common_module.py`

Lines 48–50:
```python
"data_entry": "context-gatherer",
"data_entry_nl": "context-gatherer",
"register_transaction": "context-gatherer",
"transacao": "context-gatherer",
"transaction": "context-gatherer",
"registro": "context-gatherer",
```

These aliases were presumably set when `context-gatherer` was the write agent. After the `data-entry` agent was introduced as the dedicated write gateway (registry.py line 233+), the aliases were never updated.

Additionally, the frontdesk agent prompt (`agents/frontdesk`) has `_SLUG_ALIASES` embedded in `common_module.py` line 232:
```
"context-gatherer (data entry, register transactions, map data, set up routines)"
```
This text in the frontdesk routing hint further reinforces routing to `context-gatherer` for transaction registration.

**This is NOT a prompt issue** — `agents/data-entry` prompt exists and is well-formed. The LLM never receives the intent to route to `data-entry` because the keyword router intercepts it first.

---

## 5. Prompt Improvements Applied

**None applied.** Root cause is `ROUTING_CONFIG` P0 code bug — prompt fixes would be wasted effort.

**Draft written:** NO — skipped intentionally per skill rules ("Do NOT touch prompt — fix code first").

---

## 6. Manual Fixes Needed (Code Changes Required)

### Fix 1 (P0) — Update `_SLUG_ALIASES` in `common_module.py`

**File:** `services/tool_pool_api/src/tool_pool_api/server/tool_modules/common_module.py`

**Change:** Replace `context-gatherer` with `data-entry` for write/transaction aliases:

```python
# BEFORE (wrong):
"data_entry": "context-gatherer",
"data_entry_nl": "context-gatherer",
"register_transaction": "context-gatherer",
"transacao": "context-gatherer",
"transaction": "context-gatherer",
"registro": "context-gatherer",

# AFTER (correct):
"data_entry": "data-entry",
"data_entry_nl": "data-entry",
"register_transaction": "data-entry",
"transacao": "data-entry",
"transaction": "data-entry",
"registro": "data-entry",
"lançamento": "data-entry",
"lancamento": "data-entry",
"venda": "data-entry",
"compra": "data-entry",
"despesa": "data-entry",
```

### Fix 2 (P1) — Update frontdesk routing_hint for data-entry in `registry.py`

Line 232 should NOT mention `context-gatherer` for data entry tasks:
```python
# BEFORE:
"context-gatherer (data entry, register transactions, map data, set up routines), "
# AFTER:
"data-entry (registrar vendas, compras, despesas, lançamentos financeiros), "
```

### Fix 3 (P1) — Fix `LoadedPrompt` is not subscriptable for `agents/frontdesk`

The frontdesk prompt was created as `type=chat` in Langfuse. Loader returns list instead of str. Per skill pitfalls: recreate as `type=text` in Langfuse UI or apply the loader normalization fix.

### Fix 4 (MANDATORY before retry) — Rebuild Docker container

After any changes to `common_module.py` or `registry.py`:
```bash
docker compose build --no-cache blu_agent_api && docker compose up -d blu_agent_api
```

---

## 7. Re-Run Results

| TC | First Run Agent | Re-Run Agent | Consistent? |
|---|---|---|---|
| TC1 | `context-gatherer` | `context-gatherer` | ✅ Deterministic |
| TC4 | `context-gatherer` | `context-gatherer` | ✅ Deterministic |

**Conclusion:** Failure is deterministic (not flaky). The `_SLUG_ALIASES` code bug consistently intercepts all write intent messages before they reach the LLM routing layer.

---

## 8. Next Recommended Actions

1. **[P0 — Fix code]** Update `_SLUG_ALIASES` in `common_module.py` to map write-intent aliases to `"data-entry"` instead of `"context-gatherer"`. No rebuild needed at `tool_pool_api` level — check if aliases are hot-reloaded or require container restart.

2. **[P1 — Fix code]** Update `routing_hint` for `data-entry` in `registry.py` to remove `context-gatherer` from the data entry description.

3. **[P1 — Fix Langfuse]** Recreate `agents/frontdesk` as `type=text` in Langfuse UI (currently `type=chat`, causing loader errors). This may explain broader frontdesk routing issues across other skills.

4. **[Post-fix]** Rebuild + retry 2.1 `ledger` with fresh JWTs to validate `data-entry` routing and `register_transaction` HITL confirmation flow.

5. **[Next]** Proceed to 2.2 `fornecedores` (expected tool: `add_supplier`, agent: `compras`) — likely same `_SLUG_ALIASES` issue for supplier-related aliases.
