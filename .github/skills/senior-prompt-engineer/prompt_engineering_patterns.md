# Prompt Engineering Patterns

## How Prompts Work in This Repo

There is a single prompt entry point: `build_prompt(name, variables, context_service=None)` from `blu_prompt_management`. `compose_prompt` is removed — do not use it anywhere.

### Loading resolution by prefix

| Prefix          | Langfuse?        | Builtin fallback                      | Used for                                                |
| --------------- | ---------------- | ------------------------------------- | ------------------------------------------------------- |
| `orchestrator/` | ✅ first         | `BUILTIN_TEMPLATES` in `templates.py` | L4 orchestrator nodes                                   |
| `agents/`       | ✅ first         | `BUILTIN_TEMPLATES` in `templates.py` | L3 domain specialists                                   |
| `skill:`        | ✅ first         | `BUILTIN_TEMPLATES` in `templates.py` | L2 skill system prompts                                 |
| `fragment/*`    | ❌ builtins only | `BUILTIN_TEMPLATES` in `templates.py` | Shared fragments (legacy stacks)                        |
| `tool/*`        | ❌ builtins only | `BUILTIN_TEMPLATES` in `templates.py` | Internal tool LLM calls                                 |
| `atendente/*`   | ❌ builtins only | `BUILTIN_TEMPLATES` in `templates.py` | Atendente-specific prompts                              |
| `classify/*`    | ❌ builtins only | `BUILTIN_TEMPLATES` in `templates.py` | Intent/skill classifiers (e.g. `classify/skill-intent`) |

Langfuse is tried with `label=production`, 300s cache, and a circuit breaker that ignores 404s (missing prompt → builtin fallback, never a 5-minute cooldown).

---

## Prompt Syntax — Two Systems

### 1. Langfuse source files (Mustache)

Files in `prompts/orchestrator/`, `prompts/specialists/`, `prompts/skills/`, `prompts/fragment/` use Mustache — no spaces inside double braces:

```mustache
{{variable}}                           ← substitute
{{#variable}}...{{/variable}}          ← render block if truthy
{{^variable}}...{{/variable}}          ← render block if falsy (inverse/else)
```

Example — conditional schema injection in a specialist prompt:

```mustache
{{#sql_schema_context}}
{{sql_schema_context}}
{{/sql_schema_context}}
{{^sql_schema_context}}
# DATABASE SCHEMA (Analytics V2 — Star Schema)
...static fallback...
{{/sql_schema_context}}
```

### 2. Builtin templates in `templates.py` (Jinja2)

`PromptTemplateConfig.content` strings use Jinja2 — spaces inside double braces:

```jinja2
{{ variable }}                         ← substitute
{% if variable %}...{% endif %}        ← conditional block
```

**Never mix the two syntaxes.** Langfuse `.md` files → Mustache. `templates.py` content → Jinja2.

---

## Builtin Fallback Format

Every Langfuse-managed prompt needs a `PromptTemplateConfig` in `BUILTIN_TEMPLATES`. Without it the service degrades silently.

```python
# libs/blu_prompt_management/src/blu_prompt_management/templates.py

PromptTemplateConfig(
    name="agents/<slug>",              # must match AgentTypeConfig.prompt_name
    category=PromptCategory.SYSTEM,
    description="<Human description for logs>",
    required_variables=["nome_empresa"],
    optional_variables={
        "sql_schema_context": "",
        "kb_context": "",
        "context_sections": "",
        "tools_description": "",
    },
    content="""Você é o <nome do agente> da **{{ nome_empresa }}**.

{% if sql_schema_context %}
{{ sql_schema_context }}
{% endif %}

{% if kb_context %}
{{ kb_context }}
{% endif %}

## Instruções
<instruções específicas do agente>

Responda sempre no idioma do usuário.
""",
),
```

Variables are **flat** — no dot notation. Use `{{ nome_empresa }}`, not `{{ client.nome_empresa }}`.
Declare all expected variables as `required_variables` or `optional_variables` (with defaults).

---

## Variable Assembly

Variables flow from `BluClientContext` into prompts via `_WorkerInvoker._get_prompt()` (for supervisor/orchestrator workers) or `UnifiedAgentFactory.get_standalone_agent()` (for standalone agents).

### Current variable inventory

| Variable               | Type | Source                                                            | Where injected                                                |
| ---------------------- | ---- | ----------------------------------------------------------------- | ------------------------------------------------------------- |
| `nome_empresa`         | str  | `BluClientContext.nome_empresa`                                   | all specialist prompts                                        |
| `agent_name`           | str  | `AgentTypeConfig.name`                                            | specialist prompts                                            |
| `agent_description`    | str  | `AgentTypeConfig.description`                                     | specialist prompts                                            |
| `sql_schema_context`   | str  | `VariableExtractor.render_sql_schema(client_context.data_schema)` | SQL specialists                                               |
| `kb_context`           | str  | `VariableExtractor.render_kb_context(client_context)`             | RAG specialists                                               |
| `context_sections`     | str  | compiled `BluClientContext` summary                               | supervisor-role                                               |
| `workers_description`  | str  | `AgentTypeRegistry.build_supervisor_description(tier)`            | orchestrator/plan, orchestrator/parse-intent                  |
| `max_turns`            | int  | `SkillDefinition.max_turns` / Langfuse `config.max_turns`         | skill prompts                                                 |
| `query`                | str  | tool call argument                                                | `tool/sql-generation`, `tool/rag-query-rewrite`               |
| `table_info`           | str  | schema from ContextService                                        | `tool/sql-generation`                                         |
| `csv_datasets`         | list | `collected_context.csv_datasets`                                  | specialist/standalone prompts                                 |
| `document_names`       | list | `collected_context.document_names`                                | specialist/standalone prompts                                 |
| `csv_datasets_details` | str  | rendered detail string                                            | specialist/standalone prompts                                 |
| `collected_context`    | dict | `agent_sessions.collected_context`                                | standalone-base (legacy fragment stack)                       |
| `filled_fields`        | int  | `len(collected_context)`                                          | standalone agents                                             |
| `total_fields`         | int  | context config                                                    | standalone agents                                             |
| `uploaded_file_count`  | int  | context                                                           | standalone agents                                             |
| `google_connected`     | bool | `bool(collected_context.get("google_email"))`                     | standalone agents                                             |
| `knowledge_updated_at` | str  | context                                                           | standalone agents                                             |
| `document_count`       | int  | context                                                           | standalone agents                                             |
| `schema_description`   | str  | `_render_schema_description(data_schema)`                         | `build_frontdesk_prompt()` and legacy standalone factory only |

> **Deprecated for new prompts**: `schema_description` — replaced by `sql_schema_context` in specialist prompts. It still appears in `build_frontdesk_prompt()` and the standalone factory for legacy fragment agents; do not introduce it in new `agents/` or `skill:` prompts.

> **Frontdesk-specific variables** (via `build_frontdesk_prompt()`): `nome_empresa`, `tools_description`, `company_profile`, `schema_description`. These differ from the standard specialist variable set — do not mix.

### Dynamic context injection (`sql_schema_context` and `kb_context`)

These are rendered in `supervisor.py` and `orchestrator.py` before each worker invocation:

```python
# libs/blu_agent_framework/src/blu_agent_framework/supervisor.py
# _WorkerInvoker._get_prompt()

from blu_prompt_management.variables import VariableExtractor

sql_schema_context = VariableExtractor.render_sql_schema(
    getattr(client_context, "data_schema", None)
)
kb_context = VariableExtractor.render_kb_context(client_context)
```

`VariableExtractor` lives in `libs/blu_prompt_management/src/blu_prompt_management/variables.py`:

- `render_sql_schema(data_schema)` — reads `data_schema.table_schemas` (from `sql_table_config` Supabase rows); returns markdown with table/column/join/example-query blocks; returns `""` when no custom rows exist
- `render_kb_context(client_context)` — reads `data_freshness`, `data_sources`, `policies`, `company_profile.sector`; returns `""` when nothing available

Currently all clients use the analytics_v2 star schema (no `sql_table_config` rows), so `sql_schema_context` is always `""` and `fragment/sql-schema` renders its static fallback.

### Adding a new variable

1. Add rendering logic to `VariableExtractor` in `variables.py` (or derive from existing `BluClientContext` fields)
2. Add the variable to the `variables` dict in `_WorkerInvoker._get_prompt()` (`supervisor.py`) and `make_execute_step_node` (`orchestrator.py`)
3. For standalone agents: also wire in `UnifiedAgentFactory.get_standalone_agent()` in `factory.py`
4. Add `{{#variable}}...{{/variable}}` guard in the Langfuse `.md` source file
5. Add to `optional_variables` in the `PromptTemplateConfig` fallback in `templates.py`

---

## New Agent Checklist (L3 Specialist)

New specialists always use `prompt_name`. The `fragments` list is legacy — never use for new agents.

```python
# 1. registry.py — AgentTypeConfig
AgentTypeConfig(
    slug="my-agent",
    name="My Agent",
    description="Does X. Use for Y. Not for Z.",
    prompt_name="agents/my-agent",         # Langfuse key — "agents/" prefix is managed
    enabled_tools=["tool_a", "tool_b"],
    tier_required=TierLevel.BASIC,
    routing_hint="keywords for delegation matching",
    max_turns=4,
    on_max_turns="return_partial",
    max_retries=2,
    tags=["domain"],
)

# 2. templates.py — BUILTIN_TEMPLATES (safety net)
PromptTemplateConfig(name="agents/my-agent", ...)

# 3. prompts/specialists/my-agent.md — Langfuse source of truth
# 4. supabase/migrations/<ts>_add_my_agent.sql — agent_catalog insert
```

---

## New Skill Checklist (L2)

```python
# 1. skills.py — SKILL_REGISTRY
SkillDefinition(
    name="my_skill",
    description="One sentence for classify_skill_intent.",
    prompt_name="skill:my_skill:system",   # "skill:" prefix is managed
    required_tool_names=["tool_a"],        # subset of parent agent's enabled_tools
    max_turns=3,
    on_max_turns="return_partial",
    tags=["domain"],                       # must intersect parent agent's tags
)

# 2. templates.py — BUILTIN_TEMPLATES
PromptTemplateConfig(name="skill:my_skill:system", ...)

# 3. prompts/skills/my_skill/system.md — Langfuse source
# 4. Push to Langfuse with label="production" via mcp__langfuse__createTextPrompt
```

---

## Current Prompt Inventory

### L4 Orchestrator (`orchestrator/` — Langfuse-managed)

| Prompt                      | Purpose                                                     |
| --------------------------- | ----------------------------------------------------------- |
| `orchestrator/parse-intent` | Classifies complexity, outputs JSON with plan/clarification |
| `orchestrator/decompose`    | Decomposes task into sub_tasks by domain                    |
| `orchestrator/plan`         | Maps sub_tasks to L3 specialist slugs                       |
| `orchestrator/synthesize`   | Synthesizes multi-specialist results into coherent response |

### Supervisor fragments (Langfuse-stored, runtime as builtins)

| Prompt                     | Purpose                                                            |
| -------------------------- | ------------------------------------------------------------------ |
| `fragment/supervisor-role` | Supervisor identity, `{{nome_empresa}}`, optional context sections |

### Context-gatherer fragments (Langfuse-stored)

| Prompt                                  | Purpose                                                                         |
| --------------------------------------- | ------------------------------------------------------------------------------- |
| `fragment/context-gatherer-base`        | 4 jobs: schema mapping, transaction extraction, routine definition, KB curation |
| `fragment/transaction-extraction-rules` | Field extraction rules + confirmation gate                                      |
| `fragment/schema-mapping-workflow`      | 4-step schema mapping workflow                                                  |
| `fragment/routine-definition-workflow`  | Routine creation using L3 skill slugs                                           |
| `fragment/knowledge-curation-workflow`  | KB curation with RAG conflict detection                                         |
| `fragment/confirmation-patterns`        | Two-turn confirmation gate for write tools                                      |

### Schema fragment

| Prompt                | Purpose                                                          |
| --------------------- | ---------------------------------------------------------------- |
| `fragment/sql-schema` | Static analytics_v2 star schema (tables, joins, rules, examples) |

### Skills (`skill:` — Langfuse-managed)

| Prompt                          | Purpose                            | Context variables                        |
| ------------------------------- | ---------------------------------- | ---------------------------------------- |
| `skill:simple_sql_query:system` | Single-turn SQL lookup (Frontdesk) | —                                        |
| `skill:analyze_csv:system`      | DuckDB CSV analysis                | `{{#sql_schema_context}}` optional block |
| `skill:rag_search:system`       | RAG retrieval + synthesis          | `{{#kb_context}}` optional block         |
| `skill:extract_document:system` | Document OCR extraction            | —                                        |
| `skill:generate_rfq:system`     | RFQ generation (transactional)     | —                                        |
| `skill:write_to_kb:system`      | KB write operations                | —                                        |
| `skill:generate_report:system`  | Report generation                  | —                                        |

### Skill classification (`classify/` — builtins only)

| Prompt                  | Purpose                                                                                                                              |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `classify/skill-intent` | LLM selects a SKILL_REGISTRY entry given task + filtered skills list; used by `_create_classify_skill_intent_node()` in `builder.py` |

### Tool prompts (`tool/` — builtins only)

| Prompt                   | Purpose                                                           |
| ------------------------ | ----------------------------------------------------------------- |
| `tool/sql-generation`    | NL→SQL inside `executar_sql_agent`; accepts `query`, `table_info` |
| `tool/rag-query-rewrite` | Pre-retrieval query rewriting inside `executar_rag_cliente`       |
| `tool/rag-query`         | RAG synthesis with cited passages                                 |
| `tool/sql-safety-system` | SQL safety constraints for `TextToSqlLLMCall`                     |

### Standalone / legacy fragments (builtins only)

| Fragment                       | Purpose                                                            |
| ------------------------------ | ------------------------------------------------------------------ |
| `fragment/standalone-base`     | Persona, session metadata (CSV, docs, Google OAuth), language rule |
| `fragment/standalone-response` | Output format, quality standards                                   |
| `fragment/sql-rules`           | SQL generation constraints, column/join rules, defaults            |
| `fragment/sql-examples`        | Few-shot SQL patterns                                              |
| `fragment/rag-search`          | RAG tool description, citation rules                               |
| `fragment/fallback-strategy`   | What to do when queries fail                                       |
| `fragment/*-workflow`          | Per-agent step-by-step tool orchestration                          |

---

## Fragment Ordering (Legacy Fragment-Stack Agents)

Order is meaningful — fragments concatenate top to bottom:

```
1. standalone-base          ← ALWAYS FIRST (identity, language rule)
2. Domain knowledge         ← WHAT THE AGENT KNOWS (sql-schema, rag-search)
3. Domain rules             ← HOW TO USE THE KNOWLEDGE (sql-rules, fallback-strategy)
4. Workflow                 ← STEP-BY-STEP BEHAVIOUR (*-workflow)
5. standalone-response      ← ALWAYS LAST (output format)
```

Rule: Tool USAGE instructions (which tool, when to call) belong in the **workflow** fragment, not in rules or schema fragments.

---

## Anti-Patterns

| Anti-pattern                                                 | Fix                                                                                                                                                                                              |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `compose_prompt(fragments=[...])` anywhere                   | Use `build_prompt(name, variables)` — `compose_prompt` is removed                                                                                                                                |
| New `AgentTypeConfig` with `fragments=[...]`                 | Use `prompt_name="agents/<slug>"`                                                                                                                                                                |
| `{{ schema_description }}` in new specialist prompts         | Use `{{sql_schema_context}}` (Mustache) or `{{ sql_schema_context }}` (Jinja2); `schema_description` only appears in `build_frontdesk_prompt()` and legacy standalone factory — do not propagate |
| `cliente_id` in any new code                                 | Use `client_id` — consistent across DB, Python, MCP headers                                                                                                                                      |
| Variables in prompt without a source in code                 | Wire in `_WorkerInvoker._get_prompt()` or `factory.py` first                                                                                                                                     |
| Schema hardcoded in both agent prompt and tool prompt        | Agent prompt → `{{sql_schema_context}}`; tool prompt → `table_info` arg                                                                                                                          |
| Synthesis logic inside a retrieval tool                      | Return raw results; agent synthesises                                                                                                                                                            |
| Two SQL tools in same agent                                  | `execute_sql` for agents with schema; `executar_sql_agent` for those without                                                                                                                     |
| Missing `PromptTemplateConfig` for a Langfuse-managed prompt | Add to `BUILTIN_TEMPLATES` in `templates.py`                                                                                                                                                     |
| `"connection" in str(e)` for circuit breaker logic           | 404 responses include `'connection': 'keep-alive'` in headers — use `_is_connection_error()` which excludes 404/not-found patterns                                                               |
| Fragment source `.md` file missing in `prompts/`             | Create it — Langfuse sync needs it at deploy time                                                                                                                                                |
| New `classify/*` prompt pushed to Langfuse                   | `classify/*` is builtins-only — add to `BUILTIN_TEMPLATES`, do not push to Langfuse                                                                                                              |

---

## Auditing and Validation

```bash
# Audit Langfuse production labels
python scripts/audit_langfuse_prompts.py

# Verify all BUILTIN_TEMPLATES compile without missing variables
python scripts/verify_standalone_prompts.py
```

To push a new prompt to Langfuse:

- Use `mcp__langfuse__createTextPrompt` or `mcp__langfuse__createChatPrompt` with `labels=["production"]`
- Langfuse labels are unique per version: setting `production` on v2 removes it from v1 automatically

---

## Further Reading

- `libs/blu_prompt_management/src/blu_prompt_management/templates.py` — all builtin fallbacks
- `libs/blu_prompt_management/src/blu_prompt_management/variables.py` — `VariableExtractor` and `PromptVariables`
- `libs/blu_prompt_management/src/blu_prompt_management/loader.py` — Langfuse circuit breaker logic
- `libs/blu_agent_framework/src/blu_agent_framework/supervisor.py` — `_WorkerInvoker._get_prompt()`
- `libs/blu_agent_framework/src/blu_agent_framework/registry.py` — `AgentTypeConfig` fragment lists
- `libs/blu_agent_framework/src/blu_agent_framework/skills.py` — `SkillDefinition` prompt keys
- `services/agent_api/src/agent_api/core/factory.py` — standalone agent variable assembly
