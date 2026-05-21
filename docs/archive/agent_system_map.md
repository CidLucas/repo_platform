# Blu Platform — Agent System Map

> Reference document: graphs, tools, skills, prompts, and data flow.

---

## 1. Architecture Overview

The system is organized in **4 progressive layers**. Each layer delegates down; no layer skips another.

```
┌─────────────────────────────────────────────────────────────────┐
│  L4  Orchestrator                                               │
│       decomposes multi-step requests → plans → routes to L3    │
├─────────────────────────────────────────────────────────────────┤
│  L3  Domain Specialists (Agent Types)                           │
│       frontdesk · context-gatherer · …                         │
├─────────────────────────────────────────────────────────────────┤
│  L2  Skills (ephemeral tool bundles)                            │
│       analyze_csv · rag_search · extract_document · write_to_kb │
├─────────────────────────────────────────────────────────────────┤
│  L1  Primitive Tools (stateless MCP)                            │
│       execute_sql · executar_rag_cliente · parse_buying_list …  │
└─────────────────────────────────────────────────────────────────┘
```

Entry point is always the **Frontdesk** specialist. Simple requests are handled inline; complex ones are handed to the Orchestrator.

---

## 2. Graphs

### 2.1 Frontdesk Graph (L3 — default path)

**File:** `libs/blu_agent_framework/src/blu_agent_framework/builder.py`
**Factory:** `UnifiedAgentFactory.get_frontdesk_graph(tier)` — compiled and **cached per tier**.

```
init_node
  └→ classify_intent_node
       └→ context_enrichment_node
            └→ respond_node  ←──────────────────┐
                 ├── [tool call] execute_single_tool_node ──┤
                 ├── [skill] run_skill_node                 │
                 └── [done] end_node                        │
                                       (loops until ended) ─┘
```

| Node                       | Input                          | Output                                            |
| -------------------------- | ------------------------------ | ------------------------------------------------- |
| `init_node`                | `AgentState`                   | increments `turn_count`, validates limits         |
| `classify_intent_node`     | messages                       | domain tags, complexity hint                      |
| `context_enrichment_node`  | `client_id`                    | enriches `client_context`, `nome_empresa`, `tier` |
| `respond_node`             | messages + tools               | AI response or tool call                          |
| `execute_single_tool_node` | `tool_to_execute`, `tool_args` | `last_tool_result`                                |
| `run_skill_node`           | `current_skill`, parent state  | `skill_results`                                   |
| `end_node`                 | —                              | sets `ended=True`                                 |

---

### 2.2 Orchestrator Graph (L4 — complex requests)

**File:** `libs/blu_agent_framework/src/blu_agent_framework/orchestrator.py`

```
parse_intent
  ├─ [simple]  ─────────────────────────────────────────→ execute_step
  ├─ [uncertain] ─→ confirm ──────────────────────────→ execute_step
  └─ [complex] ─→ decompose ─→ plan ─┬─→ execute_step ──┐
                                      │   (loop per step)│
                                      │←─────────────────┘
                                      └─→ synthesize ─→ end
                                     escalate (on failure)
```

| Node           | Input                         | Output                                        |
| -------------- | ----------------------------- | --------------------------------------------- |
| `parse_intent` | messages                      | `complexity` ("simple"/"complex"/"uncertain") |
| `decompose`    | messages, available L3 skills | `plan` list of sub-tasks                      |
| `plan`         | `plan`, `AgentTypeRegistry`   | step–skill assignments, `is_mutation` flags   |
| `confirm`      | `pending_confirmation`        | waits for `confirmed=True` from user          |
| `execute_step` | one step from `plan`          | invokes L3 subgraph, writes to `step_results` |
| `synthesize`   | `step_results`                | final AI response combining all step outputs  |
| `escalate`     | failed step                   | error response, sets `ended=True`             |

**Routing functions** (`routing.py`):

| Function                | Decision                                      |
| ----------------------- | --------------------------------------------- |
| `route_after_context()` | → decompose / execute_step / confirm / end    |
| `route_after_plan()`    | → confirm / execute_step / escalate           |
| `route_after_step()`    | → execute_step (next) / synthesize / escalate |

---

### 2.3 Standalone Agent Graph

**Factory:** `UnifiedAgentFactory.get_standalone_agent(session_id, client_id, agent_catalog_id)`
Reads configuration from Supabase `agent_catalog` table, compiles and caches a graph **per session**.

```
init_node → [same default graph topology as Frontdesk]
```

Returns a `BuiltAgent` dataclass:

```python
@dataclass
class BuiltAgent:
    graph: CompiledGraph
    system_prompt: str
    agent_name: str
    agent_role: str
    enabled_tools: list[str]
    client_context: dict
    metadata: dict          # {tier, nome_empresa}
```

---

## 3. Agent Types (L3 — Domain Specialists)

**File:** `libs/blu_agent_framework/src/blu_agent_framework/registry.py`

### 3.1 Frontdesk

| Property     | Value                                                                |
| ------------ | -------------------------------------------------------------------- |
| Slug         | `frontdesk`                                                          |
| Prompt       | `agents/frontdesk`                                                   |
| Max Turns    | 10                                                                   |
| Min Tier     | BASIC                                                                |
| Routing Hint | Entry point — simple RAG/SQL, routes complex to Orchestrator         |
| Tools        | `executar_rag_cliente`, `execute_sql`, `ferramenta_publica_de_teste` |
| Tags         | `frontdesk`, `routing`, `rag`, `sql`                                 |

### 3.2 Context Gatherer

| Property  | Value                                                         |
| --------- | ------------------------------------------------------------- |
| Slug      | `context-gatherer`                                            |
| Prompt    | assembled from **fragments** (see §5.3)                       |
| Max Turns | 6                                                             |
| Min Tier  | BASIC                                                         |
| Tags      | `context`, `mapping`, `transactions`, `routines`, `knowledge` |

**Tools (grouped by capability):**

| Group        | Tools                                                                                                                                                                   |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Routines     | `listar_rotinas_catalogo`, `listar_rotinas_personalizadas`, `criar_rotina_personalizada`, `enviar_rotina_para_aprovacao`                                                |
| Knowledge    | `write_summary_to_kb`, `executar_rag_cliente`                                                                                                                           |
| Data Catalog | `register_transaction`, `list_data_sources`, `query_data_catalog`, `suggest_column_mapping`, `update_schema_mapping`, `get_knowledge_status`, `update_context_document` |

---

## 4. Skills (L2 — Ephemeral Tool Bundles)

**File:** `libs/blu_agent_framework/src/blu_agent_framework/skills.py`
**Executor:** `SkillFactory` in `skill_factory.py`

Each skill is a **self-contained subgraph** compiled on demand, with its own filtered tool set and prompt. It runs inside an L3 agent when `run_skill_node` is triggered.

| Skill                 | Slug               | Tools                                                                                 | Prompt                          | Max Turns | On Limit       |
| --------------------- | ------------------ | ------------------------------------------------------------------------------------- | ------------------------------- | --------- | -------------- |
| CSV / Analytics       | `analyze_csv`      | `list_csv_datasets`, `peek_csv_columns`, `execute_csv_query`                          | `skill:analyze_csv:system`      | 5         | return_partial |
| RAG / Knowledge       | `rag_search`       | `executar_rag_cliente`                                                                | `skill:rag_search:system`       | 3         | return_partial |
| Document Intelligence | `extract_document` | `extract_document_with_ocr`, `summarize_document_sections`, `extract_structured_data` | `skill:extract_document:system` | 4         | return_partial |
| Knowledge Persistence | `write_to_kb`      | `write_summary_to_kb`                                                                 | `skill:write_to_kb:system`      | 2         | return_partial |

**SkillFactory execution flow:**

```
run_skill_node
  └→ SkillFactory.run(skill_name, parent_state)
       ├── load skill prompt via build_prompt(skill.prompt_name)
       ├── filter tools to skill.required_tools
       ├── compile isolated subgraph (respond → end)
       ├── invoke with isolated state snapshot
       └── return SkillResult → appended to skill_results
```

**SkillResult shape:**

```python
{
  "skill": "analyze_csv",
  "output": "<final AI message text>",
  "tool_calls": [...],
  "truncated": False
}
```

---

## 5. Prompts

**Single entry point:** `build_prompt(name, variables)` from `blu_prompt_management`.
Strategy: try **Langfuse** first (by name), fall back to **builtin templates** (`templates.py`).
Template syntax: Jinja2 flat variables — `{{ nome_empresa }}`, `{{ schema_description }}`.

### 5.1 Orchestrator Prompts

| Name                        | Purpose                                   |
| --------------------------- | ----------------------------------------- |
| `orchestrator/parse-intent` | Classifies request complexity             |
| `orchestrator/decompose`    | Breaks request into domain sub-tasks      |
| `orchestrator/plan`         | Maps sub-tasks to L3 skills with ordering |
| `orchestrator/synthesize`   | Combines step results into final response |

### 5.2 Agent Prompts

| Name               | Agent                                            |
| ------------------ | ------------------------------------------------ |
| `agents/frontdesk` | Frontdesk inline response + routing instructions |

### 5.3 Fragment Prompts (Context Gatherer)

Fragments are modular prompt blocks composed together for the Context Gatherer agent.

| Fragment                                | Covers                               |
| --------------------------------------- | ------------------------------------ |
| `fragment/context-gatherer-base`        | Agent identity & goals               |
| `fragment/transaction-extraction-rules` | How to register transactions         |
| `fragment/schema-mapping-workflow`      | Schema mapping process               |
| `fragment/routine-definition-workflow`  | Creating automation routines         |
| `fragment/knowledge-curation-workflow`  | Managing the knowledge base          |
| `fragment/confirmation-patterns`        | When and how to ask for confirmation |

### 5.4 Skill Prompts

| Name                            | Skill                   |
| ------------------------------- | ----------------------- |
| `skill:analyze_csv:system`      | CSV analytics           |
| `skill:rag_search:system`       | RAG search              |
| `skill:extract_document:system` | Document extraction     |
| `skill:write_to_kb:system`      | Write to knowledge base |

### 5.5 Tool & Fragment Helpers

| Name                                | Purpose                                |
| ----------------------------------- | -------------------------------------- |
| `fragment/standalone-base`          | Base identity for any standalone agent |
| `fragment/sql-schema`               | DB schema injected into SQL agents     |
| `fragment/sql-rules`                | SQL generation rules                   |
| `fragment/sql-examples`             | Query patterns & examples              |
| `fragment/rag-rules`                | RAG query rewriting instructions       |
| `tool/rag-query-rewrite`            | Optimizes user query before RAG call   |
| `tool/rag-context`                  | RAG context block injection            |
| `tool/elicitation-clarify`          | Prompts for clarification from user    |
| `tool/sql-safety-system`            | SQL safety constraints                 |
| `specialists/classify-skill-intent` | Maps task to a Layer-2 skill           |

---

## 6. Tools (L1 — Primitive MCP Tools)

**File:** `libs/blu_tool_registry/src/blu_tool_registry/registry.py`
**Executor:** `MCPToolExecutor` → calls `tool_pool_api` via MCP protocol.

### 6.1 Access Control

**TierLevel** (ordered):

```
FREE(0) → BASIC(1) → SME(2) → PREMIUM(3) → ENTERPRISE(4) → ADMIN(99)
```

**ToolCategory:**

```
RAG · SQL · SCHEDULING · DOCKER_MCP · PUBLIC · GOOGLE · CUSTOM
```

### 6.2 Tool Catalog

**RAG & Knowledge:**

| Tool                          | Min Tier | Category |
| ----------------------------- | -------- | -------- |
| `executar_rag_cliente`        | BASIC    | RAG      |
| `extract_document_with_ocr`   | SME      | RAG      |
| `summarize_document_sections` | SME      | RAG      |
| `extract_structured_data`     | SME      | RAG      |
| `write_summary_to_kb`         | SME      | RAG      |

**SQL & Analytics:**

| Tool                 | Min Tier | Category |
| -------------------- | -------- | -------- |
| `executar_sql_agent` | SME      | SQL      |
| `execute_sql`        | SME      | SQL      |
| `execute_csv_query`  | SME      | SQL      |
| `list_csv_datasets`  | SME      | SQL      |
| `peek_csv_columns`   | BASIC    | SQL      |

**Setup & Config:**

| Tool                        | Min Tier |
| --------------------------- | -------- |
| `check_config_completeness` | BASIC    |
| `save_config_field`         | BASIC    |
| `get_agent_requirements`    | BASIC    |
| `finalize_config`           | BASIC    |

**Data Catalog & Context:**

| Tool                      | Min Tier |
| ------------------------- | -------- |
| `register_transaction`    | BASIC    |
| `list_data_sources`       | BASIC    |
| `query_data_catalog`      | BASIC    |
| `suggest_column_mapping`  | BASIC    |
| `update_schema_mapping`   | BASIC    |
| `get_knowledge_status`    | BASIC    |
| `update_context_document` | BASIC    |

**Routines:**

| Tool                            | Min Tier |
| ------------------------------- | -------- |
| `listar_rotinas_catalogo`       | BASIC    |
| `listar_rotinas_personalizadas` | BASIC    |
| `criar_rotina_personalizada`    | BASIC    |
| `enviar_rotina_para_aprovacao`  | BASIC    |

**Procurement / RFQ:**

| Tool                             | Min Tier | Notes                     |
| -------------------------------- | -------- | ------------------------- |
| `parse_buying_list`              | BASIC    |                           |
| `validate_buying_list`           | BASIC    |                           |
| `list_suppliers`                 | BASIC    |                           |
| `dispatch_rfq`                   | BASIC    |                           |
| `check_rfq_responses`            | BASIC    |                           |
| `submit_mock_response`           | BASIC    |                           |
| `optimize_allocation`            | BASIC    |                           |
| `generate_po_report`             | BASIC    |                           |
| `create_purchase_order`          | BASIC    | **requires_confirmation** |
| `approve_purchase_order`         | BASIC    | **requires_confirmation** |
| `suggest_counter_offer`          | BASIC    |                           |
| `dispatch_rfq_whatsapp`          | SME      |                           |
| `parse_supplier_reply`           | SME      |                           |
| `import_buying_list_from_sheets` | BASIC    |                           |
| `export_po_to_sheets`            | BASIC    |                           |
| `add_supplier`                   | BASIC    |                           |

**Monitoring:**

| Tool               | Min Tier |
| ------------------ | -------- |
| `monitor_feature`  | BASIC    |
| `monitor_keywords` | BASIC    |
| `monitor_company`  | BASIC    |

**Diagnostic:**

| Tool                          | Min Tier |
| ----------------------------- | -------- |
| `ferramenta_publica_de_teste` | FREE     |

---

## 7. State Schema

**File:** `libs/blu_agent_framework/src/blu_agent_framework/state.py` — `AgentState` TypedDict

```
┌─────────────────── AgentState ────────────────────────────────┐
│                                                               │
│  Identifiers                                                  │
│    session_id · client_id · thread_id · channel              │
│                                                               │
│  Messages                                                     │
│    messages: list[BaseMessage]  [reducer: append]            │
│                                                               │
│  Execution Control                                            │
│    turn_count · max_turns · ended · end_reason               │
│                                                               │
│  Tool Execution                                               │
│    tool_to_execute · tool_args                               │
│    tool_results [reducer: accumulate]                        │
│    last_tool_result · pending_tool_calls                     │
│                                                               │
│  Skill Routing                                                │
│    complexity · current_skill                                 │
│    skill_results [reducer: accumulate]                       │
│                                                               │
│  Elicitation                                                  │
│    pending_elicitation · elicitation_response                │
│    elicitation_history                                       │
│                                                               │
│  Agent Context                                                │
│    system_prompt · agent_name · agent_role                   │
│                                                               │
│  Client Context                                               │
│    client_context · nome_empresa · tier                      │
│                                                               │
│  Orchestrator Planning                                        │
│    plan: list[{id, skill_slug, task, depends_on,             │
│                status, result, is_mutation,                  │
│                requires_confirmation}]                       │
│    step_results: dict[step_id → result_text]                 │
│    involved_domains · pending_confirmation · confirmed       │
│                                                               │
│  Error Handling                                               │
│    error · errors [capped at 20]                             │
│                                                               │
│  Metadata                                                     │
│    metadata [reducer: merge_dict]                            │
│    available_tools_metadata                                  │
│    model_override · user_jwt · structured_data               │
└───────────────────────────────────────────────────────────────┘
```

State is persisted across turns via **Redis checkpointer** (`langgraph.checkpoint.redis`).
`session_id` maps 1:1 to LangGraph `thread_id`.

---

## 8. End-to-End Data Flows

### 8.1 Simple Request

```
User message (HTTP POST /agents/chat)
  └─ agents_router.py → ChatService.invoke()
       └─ UnifiedAgentFactory.get_frontdesk_graph(tier)
            └─ CompiledGraph.astream(initial_state)
                 init_node → classify_intent_node → context_enrichment_node
                   → respond_node
                        [no tool needed] → end_node → stream response
```

### 8.2 Request Requiring a Tool

```
respond_node detects tool call
  └─ execute_single_tool_node
       └─ MCPToolExecutor.call(tool_name, tool_args, client_id)
            └─ MCP protocol → tool_pool_api service
                 ← tool result
       → last_tool_result injected into messages
  └─ respond_node (again with tool result)
       → end_node → stream response
```

### 8.3 Request Routed to a Skill

```
classify_skill_intent_node → selects skill from SKILL_REGISTRY
  └─ run_skill_node → SkillFactory.run(skill_name, parent_state)
       ├─ build_prompt(skill.prompt_name)        [Langfuse → builtin]
       ├─ filter tools to skill.required_tools
       ├─ compile isolated subgraph (respond_node → end_node)
       ├─ astream with isolated state
       └─ SkillResult → appended to skill_results
  └─ respond_node synthesizes skill result → end_node
```

### 8.4 Complex Multi-Step Request (Orchestrator)

```
parse_intent → complexity="complex"
  → decompose_node
       prompt: orchestrator/decompose
       output: list of domain sub-tasks
  → plan_node
       prompt: orchestrator/plan
       output: plan[] with {skill_slug, depends_on, is_mutation}
  → [confirm_node if any step is_mutation or requires_confirmation]
       waits for user confirmed=True
  → execute_step_node (loop)
       for each pending step with dependencies satisfied:
         ├─ compile L3 specialist subgraph for step.skill_slug
         ├─ invoke(task=step.task, parent_state)
         ├─ extract final AI message as result
         └─ mark step status="done", store in step_results
  → synthesize_node
       prompt: orchestrator/synthesize
       input: step_results dict
       output: final cohesive response
```

---

## 9. Elicitation Flow

Elicitation allows an agent to **pause and collect structured input** from the user before proceeding.

```
respond_node detects tool requires input
  → elicit_node
       type: "confirmation" | "selection" | "text_input" | "date_time"
       sets pending_elicitation
       → streams elicitation request to frontend
  ← user responds
       elicitation_response populated
       appended to elicitation_history
  → respond_node resumes with answer
```

---

## 10. Context Loading

**Service:** `ContextService` → `BluClientContext` (Redis-cached, Supabase-backed)

```
context_enrichment_node
  └─ ContextService.get_context(client_id)
       ├─ Redis cache hit? → return BluClientContext
       └─ miss → Supabase query → cache → return
            populates:
              client_context · nome_empresa · tier
              schema_description · available_integrations
```

The resolved `client_context` is injected into every prompt that references `{{ nome_empresa }}`, `{{ tier }}`, or schema variables.

---

## 11. Key Files Reference

| Concern             | File                                                                |
| ------------------- | ------------------------------------------------------------------- |
| Agent type registry | `libs/blu_agent_framework/src/blu_agent_framework/registry.py`      |
| Skill registry      | `libs/blu_agent_framework/src/blu_agent_framework/skills.py`        |
| Graph nodes         | `libs/blu_agent_framework/src/blu_agent_framework/nodes.py`         |
| Routing functions   | `libs/blu_agent_framework/src/blu_agent_framework/routing.py`       |
| State schema        | `libs/blu_agent_framework/src/blu_agent_framework/state.py`         |
| Graph builder       | `libs/blu_agent_framework/src/blu_agent_framework/builder.py`       |
| Orchestrator        | `libs/blu_agent_framework/src/blu_agent_framework/orchestrator.py`  |
| Skill execution     | `libs/blu_agent_framework/src/blu_agent_framework/skill_factory.py` |
| MCP tool executor   | `libs/blu_agent_framework/src/blu_agent_framework/mcp_executor.py`  |
| Tool catalog        | `libs/blu_tool_registry/src/blu_tool_registry/registry.py`          |
| Tool metadata/enums | `libs/blu_tool_registry/src/blu_tool_registry/tool_metadata.py`     |
| Prompt templates    | `libs/blu_prompt_management/src/blu_prompt_management/templates.py` |
| Graph factory       | `services/agent_api/src/agent_api/core/factory.py`                  |
| HTTP router         | `services/agent_api/src/agent_api/api/agents_router.py`             |

---

## 12. Enumerations Quick Reference

```
TierLevel:     FREE · BASIC · SME · PREMIUM · ENTERPRISE · ADMIN
ToolCategory:  RAG · SQL · SCHEDULING · DOCKER_MCP · PUBLIC · GOOGLE · CUSTOM
Complexity:    simple · complex · uncertain
ElicitType:    confirmation · selection · text_input · date_time
StepStatus:    pending · done · failed
OnMaxTurns:    return_partial · raise
Channel:       whatsapp · web · api
```
