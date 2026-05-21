# Handoff — BL-002 → BL-005, BL-007
**Branch:** `fix/BL-001-llm-json-extractor`
**Commit:** `20b2b449`
**Data:** 2026-05-20
**Status push:** ⚠️ pendente — remote `CidLucas/repo_platform` não acessível; ajustar URL e repetir `git push origin fix/BL-001-llm-json-extractor`

---

## Resultado de testes
| Marco | Passed | Failed |
|-------|--------|--------|
| Início da sessão | 120 | 15 |
| Após BL-002 | 127 | 13 |
| Após BL-003 | 142 | 13 |
| Após BL-004 | 162 | 13 |
| Após BL-005 | 186 | 13 |
| Após BL-007 | 186 | 13 |

13 falhas são **backlog pré-existente** (TestSimpleSqlQuerySkill ×5, TestFrontdeskPromptTemplates ×1, TestUseSpecialistGraph ×1, classify_intent/intent_fields/specialist_graph ×6). Não houve regressão.

---

## O que foi implementado

### BL-002 — `fail_on_placeholders` no runtime dos nós
**Arquivo:** `libs/blu_agent_framework/src/blu_agent_framework/nodes.py`

- `_fail_on_placeholders(config=None)`: precedência `config.fail_on_placeholders` > env var `BLU_AGENT_FAIL_ON_PLACEHOLDERS` > default `True`
- Antes: comportamento controlado apenas por env var, sem integração com `AgentConfig`
- Dois testes de integração ajustados (`test_execute_tool_node_clears_fields`, `test_execute_single_tool_node_placeholder`) com `monkeypatch.setenv("BLU_AGENT_FAIL_ON_PLACEHOLDERS", "0")`

**Novos testes:** `libs/blu_agent_framework/tests/unit/test_node_placeholders.py` (+5 testes de precedência)

---

### BL-003 — `_CheckpointerAdapter` lifecycle determinístico
**Arquivo:** `libs/blu_agent_framework/src/blu_agent_framework/checkpointer.py`

- Adicionados: `close()`, `aclose()` (idempotentes — zerando `_cm` após uso), `__enter__`/`__exit__`, `__aenter__`/`__aexit__`
- `create_checkpointer` preserva o CM original em `_cm` e passa como kwarg ao construtor
- Antes: `__enter__` era chamado mas `__exit__` nunca era delegado → resource leak

**Novos testes:** `libs/blu_agent_framework/tests/unit/test_checkpointer_lifecycle.py` (15 testes: sync/async ctx-manager, idempotência, fallback, delegação, AttributeError)

---

### BL-004 — `TierLevel.get_order` normalização robusta
**Arquivo:** `libs/blu_tool_registry/src/blu_tool_registry/tool_metadata.py`

- `TierLevel.get_order(tier)`: normaliza com `.strip().upper()` antes do lookup; lança `ValueError` explícito para tiers desconhecidos (era fallback silencioso → 0/FREE)
- `AgentTypeRegistry.for_tier` (em `registry.py`): normaliza tier, captura `ValueError`, loga `WARNING`, cai em `BASIC` (não `FREE`)

**Novos testes:** `libs/blu_agent_framework/tests/unit/test_tier_normalization.py` (20 testes: case-insensitive, whitespace, unknown, fallback BASIC)

---

### BL-005 — `test_state_reducers` movido para pacote correto
**Arquivo novo:** `libs/blu_agent_framework/tests/unit/test_state_reducers.py`

- Copiado e expandido de `/tests/unit/test_state_reducers.py` (4 → 24 testes)
- Cobre edge cases: listas vazias, boundary caps, most-recent-kept
- ⚠️ **Ação manual pendente:** `git rm tests/unit/test_state_reducers.py` (arquivo original no root do repo — remoção bloqueada por ferramenta)

---

### BL-007 — `generate_agent_docs.py` e workflow CI corrigidos
**Arquivos:**
- `scripts/generate_agent_docs.py` — reescrito
- `.github/workflows/docs_check.yml` — corrigido para monorepo

**Bugs corrigidos no script:**
- `AgentTypeRegistry.list_types()` → `AgentTypeRegistry.all()` (método correto)
- `SkillDefinition` tratado como dict → acesso por atributos (`.name`, `.tags`, etc.)
- `sys.path.insert` por lib para funcionar sem venv completo
- `mkdir(parents=True, exist_ok=True)` antes de escrever docs
- `--check` agora compara conteúdo e imprime diff unificado

**Bugs corrigidos no workflow:**
- `macos-latest` → `ubuntu-latest`
- `pip install -e .` no root → `pip install -e libs/blu_tool_registry -e libs/blu_agent_framework` separados
- Upload de artifact em caso de falha do check

**Docs gerados:**
- `docs/auto-skills.md`
- `docs/auto-agent-types.md`

---

## Pendências para próxima sessão

| Item | Status | Ação |
|------|--------|------|
| Push branch | ⚠️ Bloqueado | Corrigir remote URL e rodar `git push origin fix/BL-001-llm-json-extractor` |
| `git rm tests/unit/test_state_reducers.py` | ⚠️ Manual | Rodar no terminal: `cd repo_platform && git rm tests/unit/test_state_reducers.py && git commit -m "chore: remove state reducer test from root (movido para pacote)"` |
| BL-006 (não implementado) | 🔲 Pendente | Verificar definição original no backlog |
| 13 falhas de backlog | 🔲 Pendente | TestSimpleSqlQuerySkill, TestFrontdeskPromptTemplates, TestUseSpecialistGraph, classify_intent/intent_fields |
| PR para main | 🔲 Pendente | Após push — abrir PR cobrindo BL-001 → BL-007 |

---

## Comandos rápidos de verificação

```bash
cd libs/blu_agent_framework

# Rodar suite completa
poetry run pytest -q

# Apenas targets BL-002
poetry run pytest -q tests/unit/test_node_placeholders.py

# Apenas targets BL-003
poetry run pytest -q tests/unit/test_checkpointer_lifecycle.py

# Apenas targets BL-004
poetry run pytest -q tests/unit/test_tier_normalization.py

# Apenas targets BL-005
poetry run pytest -q tests/unit/test_state_reducers.py

# Verificar docs atualizados
cd .. && python scripts/generate_agent_docs.py --check
```
