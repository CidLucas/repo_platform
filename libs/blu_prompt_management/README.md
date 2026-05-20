# blu_prompt_management

Prompt management for Blu services — Langfuse as source of truth with builtin fallback.

## How It Works

```
build_prompt(name, variables)
  ├─ 1. Try Langfuse SDK get_prompt(name) + compile(variables)
  └─ 2. Fallback → BUILTIN_TEMPLATES in templates.py (Jinja2)
```

All prompts go through **one entry point**: `build_prompt(name, variables)`.
Never use `compose_prompt` — it has been removed.

## Installation

```bash
poetry add blu_prompt_management
```

## Usage

```python
from blu_prompt_management import build_prompt

content = await build_prompt(
    name="agents/frontdesk",
    variables={"nome_empresa": "Acme", "tier": "SME"},
)
```

```python
# With full metadata (for Langfuse trace linking)
from blu_prompt_management import build_prompt_full

loaded = await build_prompt_full(
    name="orchestrator/synthesize",
    variables={"step_results": "..."},
)
print(loaded.langfuse_prompt)        # Langfuse prompt object
print(loaded.get_trace_metadata())   # {prompt_name, prompt_version, …}
```

## Prompt Naming Conventions

All prompt names follow a structured namespace:

| Prefix          | Used By                                    | Examples                                                                                              |
| --------------- | ------------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| `agents/`       | L3 specialist system prompts               | `agents/frontdesk`                                                                                    |
| `orchestrator/` | L4 orchestrator nodes                      | `orchestrator/parse-intent`, `orchestrator/decompose`, `orchestrator/plan`, `orchestrator/synthesize` |
| `skill:`        | L2 skill system prompts                    | `skill:analyze_csv:system`, `skill:rag_search:system`                                                 |
| `fragment/`     | Modular prompt blocks composed into agents | `fragment/sql-schema`, `fragment/rag-rules`, `fragment/context-gatherer-base`                         |
| `specialists/`  | Internal routing classifiers               | `specialists/classify-skill-intent`                                                                   |
| `tool/`         | Tool-level prompt helpers                  | `tool/rag-query-rewrite`, `tool/elicitation-clarify`, `tool/sql-safety-system`                        |

## All Registered Prompts

### Orchestrator

- `orchestrator/parse-intent` — classifies request as simple / complex / uncertain
- `orchestrator/decompose` — breaks request into domain sub-tasks
- `orchestrator/plan` — maps sub-tasks to L3 skill slugs with dependency ordering
- `orchestrator/synthesize` — combines step results into a final cohesive response

### Agent System Prompts

- `agents/frontdesk` — entry-point agent with inline RAG/SQL and routing instructions

### Skill System Prompts

- `skill:analyze_csv:system`
- `skill:rag_search:system`
- `skill:extract_document:system`
- `skill:write_to_kb:system`

### Fragment Prompts (Context Gatherer)

- `fragment/context-gatherer-base`
- `fragment/transaction-extraction-rules`
- `fragment/schema-mapping-workflow`
- `fragment/routine-definition-workflow`
- `fragment/knowledge-curation-workflow`
- `fragment/confirmation-patterns`

### General Fragments

- `fragment/standalone-base` — base identity for standalone agents
- `fragment/sql-schema` — DB schema injection
- `fragment/sql-rules` — SQL generation rules
- `fragment/sql-examples` — query patterns
- `fragment/rag-rules` — RAG query rewriting

### Tool Helpers

- `tool/rag-query-rewrite`
- `tool/rag-context`
- `tool/elicitation-clarify`
- `tool/sql-safety-system`

### Internal Classifiers

- `specialists/classify-skill-intent`

## Template Variables

Builtin templates use flat Jinja2 syntax. Common variables:

| Variable                   | Source                        |
| -------------------------- | ----------------------------- |
| `{{ nome_empresa }}`       | `client_context.nome_empresa` |
| `{{ tier }}`               | `client_context.tier`         |
| `{{ schema_description }}` | DB schema for SQL agents      |
| `{{ tools_description }}`  | Formatted tool list           |
| `{{ step_results }}`       | Orchestrator step outputs     |

## Adding a New Prompt

1. Create the prompt in Langfuse under the appropriate namespace (e.g., `agents/my-agent`).
2. Add a builtin fallback in `templates.py`:

```python
BUILTIN_TEMPLATES["agents/my-agent"] = """
You are {{ nome_empresa }}'s assistant for domain X.
…
"""
```

3. Reference the prompt name in the agent's `AgentTypeConfig.prompt_name` field in
   `libs/blu_agent_framework/src/blu_agent_framework/registry.py`.

## Dependencies

- `blu_observability_bootstrap` — Langfuse client
- `blu_context_service` — Redis caching (optional)
- `jinja2` — Template rendering for builtins
