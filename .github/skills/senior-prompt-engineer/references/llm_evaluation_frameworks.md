# LLM Evaluation Frameworks

## Core Principle

A prompt change is only validated when the real service path behaves correctly. Reading the prompt text or eyeballing one output is not enough. Many failures in this repo are variable-assembly issues, not wording issues — verify that the compiled prompt contains the right variables before assuming the text is the problem.

---

## Isolating Failures

When a run fails, determine which layer is responsible before changing prompts:

| Layer             | Failure signal                                 | Where to look                                                                |
| ----------------- | ---------------------------------------------- | ---------------------------------------------------------------------------- |
| Prompt text       | Agent reasons incorrectly given correct inputs | Langfuse trace → compiled system prompt                                      |
| Variable assembly | Prompt compiles with empty or wrong values     | `factory.py` variables dict; `compose_prompt` call                           |
| Tool availability | Agent calls wrong tool or no tool              | `AgentTypeConfig.enabled_tools`; `SkillDefinition.required_tool_names`       |
| Context injection | Schema / session data missing                  | `ContextService.get_sql_table_configs()`; `agent_sessions.collected_context` |
| Graph routing     | Wrong agent receives the request               | `supervisor-rules`; `AgentTypeRegistry.build_supervisor_description()`       |
| Tool contract     | Tool returns unexpected format                 | `tool_pool_api` implementation; tool prompt in `prompts/tool/`               |
| RLS / data        | Query returns wrong rows                       | `client_id` filter in SQL execution; `get_sql_table_configs` scope           |

---

## Evaluation Surfaces

### 1. Script-based prompt verification

```bash
# Audit all prompts for production labels and missing entries
python scripts/audit_langfuse_prompts.py

# Verify that fragment composition compiles with real variables
python scripts/verify_standalone_prompts.py
```

Use when: validating a batch of prompt changes, checking production labels before rollout, verifying that no prompt key is missing from Langfuse.

### 2. Prompt seeding scripts

```bash
# Seed or update specific prompt families in Langfuse
python scripts/create_standalone_prompts.py
python scripts/create_analytics_prompts.py
python scripts/create_rfq_prompts.py
python scripts/create_supervisor_prompts.py
python scripts/update_atendente_fragments.py
```

Use when: creating a new prompt family, refreshing content after a bulk rewrite, or syncing builtin fallback files to Langfuse.

### 3. Langfuse trace inspection

Every agent run produces a Langfuse trace. Check:

- Which prompt version ran (label, version number)
- What variables were compiled into the system prompt
- Which tools were called and in what order
- Where the turn budget was consumed

Use when: debugging a live session, verifying that `schema_description` is populated correctly, or confirming that a new fragment appears in the compiled prompt.

### 4. Focused integration tests

```
libs/*/tests/          — unit and integration tests per library
services/*/tests/      — service-level tests
```

When a prompt change affects SQL output or RAG retrieval, prefer the closest existing test slice. For SQL: run against a test schema that matches the analytics_v2 structure. For RAG: verify that `executar_rag_cliente` returns passages and that synthesis happens in the agent, not the tool.

### 5. Manual verification checklist for fragment changes

Before marking a fragment change complete:

- [ ] Does the builtin `.md` fallback file exist and render without error?
- [ ] Are all `{{ variables }}` in the fragment listed in `optional_variables` or `required_variables` in the frontmatter?
- [ ] Are all variables assembled in `factory.py` before `compose_prompt` is called?
- [ ] Does the compiled prompt contain the correct content when `schema_description` is empty (static fallback renders)?
- [ ] Does the compiled prompt contain the correct content when `schema_description` is populated (dynamic schema renders)?
- [ ] Is the Langfuse entry updated and labeled `production`?

---

## Task-Specific Success Criteria

### SQL agent (data-analyst)

- Generated SQL uses `SUM(f.valor)` for revenue, not `valor_total`
- Date filtering JOINs `dim_datas` via `ON f.data_competencia_id = d.data_id`, not a direct column
- Tables are prefixed with `analytics_v2.`
- `client_id` filter is never present in generated SQL (injected post-execution)
- For "top N per group" queries, a CTE with `ROW_NUMBER()` is used

### RAG agent (knowledge-assistant)

- Agent calls `executar_rag_cliente` before answering any policy/process question
- Response cites source documents by name
- When passages don't contain the answer, agent says so rather than guessing
- No synthesis happens inside the tool — raw passages are returned, agent synthesises

### Supervisor

- Multi-topic requests produce parallel tool calls in a single response (not sequential)
- `workers_description` includes all agents accessible at the user's tier
- Greetings and clarifications are handled directly without delegation

### Skill (SkillFactory)

- Skill's `required_tool_names` intersects correctly with parent agent's `enabled_tools`
- `on_max_turns="raise"` skills (generate_rfq) surface `SkillTurnLimitError` on budget exceeded
- `on_max_turns="return_partial"` skills return whatever state exists without raising

---

## Anti-Patterns

| Anti-pattern                                                            | Fix                                                                           |
| ----------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Declaring success by reading the prompt text                            | Run the actual consuming path and inspect the compiled output                 |
| Changing prompt wording when the issue is a missing variable            | Check `factory.py` variables dict first                                       |
| Treating a graph routing failure as a prompt failure                    | Check `enabled_tools`, `AgentTypeConfig.routing_hint`, and `supervisor-rules` |
| Skipping the Langfuse trace when debugging a live session               | Traces show exact prompt version, compiled variables, and tool calls          |
| Broadening evaluation scope before re-running the original narrow check | Rerun the same focused check after each repair                                |

---

## Further Reading

- `scripts/audit_langfuse_prompts.py`
- `scripts/verify_standalone_prompts.py`
- `scripts/create_standalone_prompts.py`
- `services/agent_api/src/agent_api/core/factory.py`
- `libs/blu_context_service/src/blu_context_service/context_service.py`
