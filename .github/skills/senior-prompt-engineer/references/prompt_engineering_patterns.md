# Prompt Engineering Patterns

## How Prompts Work in This Repo

There are four prompt surfaces, each with its own loading path:

| Surface              | Loader call                                                         | Builtin fallback location                                                    |
| -------------------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Fragment-based agent | `compose_prompt(fragments=[...], variables={})`                     | `libs/blu_prompt_management/src/blu_prompt_management/prompts/fragment/*.md` |
| Named-prompt agent   | `build_prompt(name=prompt_name, variables={}, context_service=...)` | varies by prompt_name                                                        |
| Skill system prompt  | `PromptLoader.load("skill:<name>:system")`                          | `libs/blu_prompt_management/src/blu_prompt_management/prompts/skill/*.md`    |
| Tool prompt          | `PromptLoader.load("tool/<name>", variables={})`                    | `libs/blu_prompt_management/src/blu_prompt_management/prompts/tool/*.md`     |

Langfuse is the canonical source for all prompts in production (label `production`). The `.md` files are offline fallbacks — they must exist for every prompt that has a Langfuse entry.

---

## Fragment Ordering Rules

Fragment lists are ordered and concatenated. The order is not arbitrary:

```
1. standalone-base          ← ALWAYS FIRST
   • Agent persona, company name (nome_empresa)
   • Collected session context (CSV datasets, documents, Google OAuth)
   • Language instruction ("respond in the user's language")

2. Domain knowledge         ← WHAT THE AGENT KNOWS
   • sql-schema             — database tables and columns (dynamic via schema_description)
   • rag-search             — RAG tool description and retrieval rules
   • document-intelligence-tools — OCR tool descriptions
   • csv-tools              — DuckDB CSV tool descriptions

3. Domain rules             ← HOW TO USE THE KNOWLEDGE
   • sql-rules              — SQL generation constraints and defaults
   • fallback-strategy      — what to do when queries fail

4. Workflow                 ← STEP-BY-STEP AGENT BEHAVIOUR
   • data-analyst-workflow
   • knowledge-assistant-workflow
   • report-generator-workflow
   • document-intelligence-workflow
   • config-helper-workflow
   • rfq-orchestrator, rfq-supplier-liaison, rfq-optimizer, rfq-report-composer

5. standalone-response      ← ALWAYS LAST
   • Output format (tables, bold numbers, bullet lists)
   • Response quality standards
```

**Rule:** Tool USAGE instructions (which tool to call and when) belong in the workflow fragment, not in rules or schema fragments. Rules fragments contain constraints; workflow fragments contain steps.

---

## Variable Assembly

Variables are assembled in `UnifiedAgentFactory.get_standalone_agent()` before `compose_prompt` is called. Every variable must have a concrete source — never invent a variable without wiring it in the factory.

### Current variable inventory

| Variable               | Type | Source                                                       | Used by                                         |
| ---------------------- | ---- | ------------------------------------------------------------ | ----------------------------------------------- |
| `nome_empresa`         | str  | `BluClientContext.nome_empresa`                              | all agents                                      |
| `agent_name`           | str  | `agent_catalog.name`                                         | `standalone-base`                               |
| `agent_description`    | str  | `agent_catalog.slug`                                         | `standalone-base`                               |
| `collected_context`    | dict | `agent_sessions.collected_context`                           | `standalone-base`                               |
| `csv_datasets`         | list | `collected_context["csv_datasets"]`                          | `standalone-base`                               |
| `csv_datasets_details` | str  | from collected_context                                       | `standalone-base`                               |
| `document_names`       | list | `collected_context["document_names"]`                        | `standalone-base`                               |
| `document_count`       | int  | derived                                                      | `standalone-base`                               |
| `google_connected`     | bool | `bool(collected_context.get("google_email"))`                | `standalone-base`, `config-helper-workflow`     |
| `uploaded_file_count`  | int  | from collected_context                                       | `standalone-base`                               |
| `schema_description`   | str  | `_render_schema_description(client_context_obj.data_schema)` | `sql-schema`                                    |
| `workers_description`  | str  | `AgentTypeRegistry.build_supervisor_description(tier)`       | `supervisor-workers`                            |
| `context_sections`     | str  | `BluClientContext` summary                                   | `supervisor-role`                               |
| `query`                | str  | tool call argument                                           | `tool/sql-generation`, `tool/rag-query-rewrite` |
| `table_info`           | str  | schema mapping from ContextService                           | `tool/sql-generation`                           |

### Adding a new variable

1. Add the variable to the `variables` dict in `factory.py`
2. Identify the source (ContextService, agent_sessions, agent_catalog, derived)
3. Add it to the relevant fragment's `optional_variables` frontmatter
4. Use `{% if variable %}` guards for variables that may be empty

### Dynamic schema injection

`schema_description` is populated from `sql_table_config` rows in Supabase:

```python
# context_service.py
configs = await self.get_sql_table_configs(cliente_id)
# merges global rows (client_id IS NULL) with client-specific overrides

# factory.py
if "fragment/sql-schema" in registry_cfg.fragments:
    schema_description = _render_schema_description(client_context_obj.data_schema)
```

When `schema_description` is non-empty, `fragment/sql-schema` renders the client's actual schema. When empty (no `sql_table_config` rows for the client), it falls back to the static analytics_v2 schema defined in the fragment.

---

## Builtin Fallback File Format

Every prompt that is loaded by `PromptLoader` needs a `.md` fallback file. Format:

```markdown
---
name: fragment/<name>
category: system
version: 1
required_variables: []
optional_variables: { "var_name": "default_value" }
---

<!--
Description: one-line description of what this fragment does
-->

[prompt content with {{ variable }} substitution]
```

Fragment files use Jinja2-style `{{ variable }}` and `{% if variable %}...{% endif %}` blocks. Optional variables listed in the frontmatter default to empty string when not supplied.

---

## Current Prompt Inventory

### Fragments (builtin fallbacks in `prompts/fragment/`)

**Identity (all standalone agents)**

- `standalone-base` — persona, session metadata, language rule
- `standalone-response` — response quality standards

**Supervisor**

- `supervisor-role` — identity, company name, context sections
- `supervisor-workers` — `{{ workers_description }}` (dynamic from AgentTypeRegistry)
- `supervisor-rules` — parallel tool call rule, handle-directly cases

**SQL domain** (data-analyst only)

- `sql-schema` — database schema; uses `{{ schema_description }}` with static fallback
- `sql-rules` — SQL generation constraints, column/join rules, defaults
- `sql-examples` — few-shot SQL query patterns
- `fallback-strategy` — what to do when queries fail

**RAG domain**

- `rag-search` — RAG tool description, citation rules, multi-search guidance

**Workflows (one per agent)**

- `data-analyst-workflow` — Path A (SQL primary), Path B (CSV secondary)
- `knowledge-assistant-workflow`
- `report-generator-workflow`
- `document-intelligence-workflow`
- `config-helper-workflow`
- `rfq-orchestrator`, `rfq-supplier-liaison`, `rfq-optimizer`, `rfq-report-composer`

**Tool-use context**

- `csv-tools`, `google-export`, `document-intelligence-tools`

**Other**

- `anomaly-detection` — used by the `daily_insights` routine (not an agent)

### Tool prompts (`prompts/tool/`)

- `sql-generation` — NL→SQL inside `executar_sql_agent`; accepts `{query, table_info, context_guidance}`
- `sql-safety-system` — SQL safety constraints for `TextToSqlLLMCall`
- `rag-query-rewrite` — pre-retrieval query rewriting inside `executar_rag_cliente`
- `elicitation-clarify` — clarifying question generation

### Skill prompts (Langfuse only — `skill:<name>:system`)

All 6 skills need builtin fallbacks at `prompts/skill/<name>.md`:

- `skill:analyze_csv:system`
- `skill:rag_search:system`
- `skill:extract_document:system`
- `skill:generate_rfq:system`
- `skill:write_to_kb:system`
- `skill:generate_report:system`

---

## Anti-Patterns

| Anti-pattern                                                                       | Fix                                                                                                    |
| ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Tool USAGE instructions in a rules or schema fragment                              | Move to the agent's workflow fragment                                                                  |
| Language instruction only in `standalone-response`                                 | Move to `standalone-base` so it can't be dropped                                                       |
| Static routing table in `supervisor-rules` alongside dynamic `workers_description` | Remove static table; `workers_description` is already dynamic                                          |
| Schema hardcoded in both agent fragment and tool prompt                            | Agent fragment uses `{{ schema_description }}`; tool prompt gets `table_info` as argument — one source |
| Skill `required_tool_names` includes a tool not in any agent's `enabled_tools`     | Add to the agent's `enabled_tools` or remove from the skill                                            |
| Builtin fallback `.md` file missing for a Langfuse prompt                          | Create it; without it the service degrades to a blank or hardcoded fallback                            |
| Variables fabricated in the prompt without a factory source                        | Wire the variable in `factory.py` before adding it to the fragment                                     |
| Synthesis logic inside a retrieval tool                                            | Return raw results; let the agent synthesise                                                           |
| Two competing SQL tools in the same agent (`execute_sql` + `executar_sql_agent`)   | Use only one: `execute_sql` for agents with schema context, `executar_sql_agent` for those without     |

---

## Further Reading

- `libs/blu_prompt_management/src/blu_prompt_management/prompts/` — all builtin fallback files
- `services/agent_api/src/agent_api/core/factory.py` — variable assembly and compose_prompt call
- `libs/blu_agent_framework/src/blu_agent_framework/registry.py` — AgentTypeConfig fragment lists
- `libs/blu_agent_framework/src/blu_agent_framework/skills.py` — SkillDefinition prompt keys
- `scripts/audit_langfuse_prompts.py` — audit production labels
- `scripts/verify_standalone_prompts.py` — verify fragment composition
