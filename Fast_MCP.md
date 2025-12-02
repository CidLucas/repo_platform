# Copilot Guidance: Leveraging FastMCP for Advanced Context Engineering & Agentic Workflows

## **Project Goals**
- Unify and scale context management, tool/resource orchestration, and prompt-driven workflows using FastMCP.
- Facilitate modular, dynamic, and reproducible agent flows for LLM/RAG-based assistants.
- Integrate human-in-the-loop, personalized workflows, and experiment-driven improvement using MCP and Langfuse.
- Achieve agility in onboarding new tools, resources, and context schemas, with robust versioning and traceability.

---

## **🔍 Repository Analysis (December 2025)**

> **Note:** This section documents the current state of the vizu-mono repository in relation to the roadmap below.

### Current Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        atendente_core                            │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │ AtendenteService│───▶│  LangGraph      │                     │
│  └────────┬────────┘    │  (StateGraph)   │                     │
│           │             │ ┌──────────────┐ │                     │
│           │             │ │supervisor_node│─── LLM + Tools       │
│           │             │ └──────┬───────┘ │                     │
│           │             │        ▼         │                     │
│           │             │ │execute_tools │─── MCP Client         │
│           │             └─────────────────┘                     │
│           ▼                       ▼                              │
│   ┌───────────────┐       ┌───────────────┐                     │
│   │ Langfuse SDK  │       │ MCPConnection │                     │
│   │ CallbackHandler│       │   Manager    │                     │
│   └───────────────┘       └───────┬───────┘                     │
└───────────────────────────────────┼──────────────────────────────┘
                                    │ SSE (/mcp/sse)
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                        tool_pool_api                             │
│   ┌────────────┐   ┌─────────────┐   ┌──────────────┐          │
│   │  FastAPI   │──▶│   FastMCP   │──▶│    Tools     │          │
│   │ :8006      │   │  v2.11.0    │   │ • RAG        │          │
│   └────────────┘   └─────────────┘   │ • SQL Agent │          │
│                                       │ • Test      │          │
│                                       └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### Feature Matrix: Current vs Roadmap

| Feature | Roadmap Phase | Status | Location |
|---------|---------------|--------|----------|
| MCP Tools (`@mcp.tool`) | Phase 1 | ✅ **Implemented** | `services/tool_pool_api/src/server/tools.py` |
| MCP Resources (`@mcp.resource`) | Phase 1-2 | ✅ **Implemented** | `services/tool_pool_api/src/server/resources.py` |
| MCP Prompts (`@mcp.prompt`) | Phase 5 | ✅ **Implemented** | `services/tool_pool_api/src/server/prompts.py` |
| Server Composition | Phase 4 | ✅ **Implemented** | `tool_modules/` package |
| Context Passing | Phase 2 | ✅ **Implemented** | `SafeClientContext` + `InternalClientContext` |
| Dynamic Tool Filtering | Phase 2 | ✅ **Implemented** | `nodes.py:filter_tools_for_client()` |
| Dynamic System Prompt | Phase 2 | ✅ **Implemented** | `nodes.py:build_dynamic_system_prompt()` |
| Client Context Endpoint | Phase 2 | ✅ **Implemented** | `GET /context` |
| Elicitation Types | Phase 3 | ✅ **Implemented** | `vizu_models.agent_types` |
| Elicitation Flow | Phase 3 | ✅ **Implemented** | `atendente_core/core/elicitation.py`, `graph.py` |
| Shared Agent Types | — | ✅ **Implemented** | `libs/vizu_models/src/vizu_models/agent_types.py` |
| Langfuse Tracing | Phase 6 | ✅ **Implemented** | `atendente_core/core/observability.py` |
| Prompt Versioning | Phase 5 | ✅ **Implemented** | Database + MCP Prompts |
| DB Prompt Templates | Phase 5 | ✅ **Implemented** | `vizu_models.PromptTemplate` |
| DB Knowledge Base Config | Phase 2 | ✅ **Implemented** | `vizu_models.KnowledgeBaseConfig` |
| HITL System | Phase 6 | ✅ **Implemented** | `vizu_hitl_service`, `apps/hitl_dashboard` |
| HITL Streamlit Dashboard | Phase 6 | ✅ **Implemented** | `apps/hitl_dashboard/` |
| Langfuse Dataset Integration | Phase 6 | ✅ **Implemented** | `LangfuseDatasetManager` |
| Experiment Manifests | Phase 7 | ✅ **Implemented** | `vizu_models.ExperimentManifest` |
| ExperimentRunner | Phase 7 | ✅ **Implemented** | `vizu_experiment_service` |
| ResponseClassifier | Phase 7 | ✅ **Implemented** | `vizu_experiment_service` |
| TrainingDatasetGenerator | Phase 7 | ✅ **Implemented** | `vizu_experiment_service` |
| Ollama Cloud Support | — | ✅ **Implemented** | `vizu_llm_service` |
| Model Selection per Request | — | ✅ **Implemented** | `GET /models`, `POST /chat` with `model` field |

### Implemented Tools (3 total)

| Tool | Description | Auth | Module |
|------|-------------|------|--------|
| `executar_rag_cliente` | RAG search in client knowledge base | JWT + cliente_id | `rag_module` |
| `executar_sql_agent` | SQL queries for structured data | JWT + cliente_id | `sql_module` |
| `ferramenta_publica_de_teste` | Internal diagnostic | None | `common_module` |

> **💡 Nota:** Endpoints de diagnóstico (`/health`, `/info`) são HTTP puro, não MCP tools.
> Isso evita confundir a LLM com ferramentas que não são para atendimento ao cliente.

### Implemented Resources (6 total)

| Resource URI | Description | Files |
|--------------|-------------|-------|
| `knowledge://summary` | KB summary for authenticated client | `resources.py` |
| `knowledge://{cliente_id}/summary` | KB summary by client ID | `resources.py` |
| `knowledge://{cliente_id}/search/{query}` | Raw document search (no LLM) | `resources.py` |
| `config://client` | Config for authenticated client | `resources.py` |
| `config://{cliente_id}/settings` | Full client settings | `resources.py` |
| `config://{cliente_id}/prompt` | Custom prompt for client | `resources.py` |

### Implemented Prompts (5 total)

| Prompt Name | Description | Parameters |
|-------------|-------------|------------|
| `atendente/system/v1` | Basic system prompt | `nome_empresa` |
| `atendente/system/v2` | Full system prompt with context | `cliente_id` |
| `atendente/confirmacao-agendamento` | Scheduling confirmation | `data`, `horario`, `servico` |
| `atendente/esclarecimento` | Disambiguation prompt | `pergunta`, `opcoes` |
| `rag/query` | RAG response template | `context`, `question` |

### Security Pattern (Well-Implemented ✅)

```python
# AgentState separates safe vs internal context
class AgentState(TypedDict):
    safe_context: SafeClientContext      # ✅ Exposed to LLM (nome_empresa, horarios, etc.)
    _internal_context: InternalClientContext  # ✅ Never in prompts (cliente_id, api_key)
```

### Key Files for Reference

| Purpose | File Path |
|---------|-----------|
| MCP Server Setup | `services/tool_pool_api/src/server/mcp_server.py` |
| Tool Registration | `services/tool_pool_api/src/server/tools.py` |
| LangGraph Definition | `services/atendente_core/src/atendente_core/core/graph.py` |
| State Definition | `services/atendente_core/src/atendente_core/core/state.py` |
| Langfuse Integration | `services/atendente_core/src/atendente_core/core/observability.py` |
| Langfuse Core (Shared) | `libs/vizu_llm_service/src/vizu_llm_service/client.py` |
| HITL Service | `libs/vizu_hitl_service/` |
| HITL Dashboard | `apps/hitl_dashboard/` |
| MCP Client | `services/atendente_core/src/atendente_core/services/mcp_client.py` |
| Context Service | `libs/vizu_context_service/src/vizu_context_service/context_service.py` |
| Dynamic Tool Filter | `services/atendente_core/src/atendente_core/core/nodes.py` |

### Architecture: Separation of Concerns

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           REQUEST FLOW                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. Request arrives at atendente_core                                        │
│                    ↓                                                         │
│  2. ContextService.get_client_context_by_id()                               │
│     ├── Check Redis cache (TTL 5min)                                        │
│     └── If miss → Query DB → Cache in Redis                                 │
│                    ↓                                                         │
│  3. VizuClientContext → InternalClientContext + SafeClientContext           │
│     └── SafeClientContext contains: ferramenta_rag_habilitada, etc.         │
│                    ↓                                                         │
│  4. supervisor_node (LangGraph)                                              │
│     ├── filter_tools_for_client(all_tools, safe_context)                    │
│     │   └── Matches MCP tools with client permissions                       │
│     ├── build_dynamic_system_prompt(safe_context, available_tools)          │
│     └── LLM.invoke(messages, tools=available_tools)                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

Key Principle:
- ContextService: Owns data loading + caching (DB → Redis)
- nodes.py: Owns tool filtering (cross-references MCP tools with client flags)
- SafeClientContext: Contains permission flags, never exposed to LLM prompts
```

### Shared Types Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      TYPE SHARING PATTERN                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  libs/vizu_models/src/vizu_models/agent_types.py                            │
│  ├── ElicitationType, ElicitationOption, ElicitationRequest                 │
│  ├── ElicitationResponse                                                    │
│  ├── ToolInfo, ToolExecutionResult                                          │
│  ├── ModelInfo                                                              │
│  ├── AgentChatRequest, AgentChatResponse                                    │
│  └── ClientContextResponse                                                  │
│                                                                              │
│  services/atendente_core/src/atendente_core/api/schemas.py                  │
│  ├── ChatRequest(AgentChatRequest)    # Extends base                        │
│  ├── ChatResponse(AgentChatResponse)  # Extends base                        │
│  └── ModelsResponse                   # Atendente-specific                  │
│                                                                              │
│  services/vendas_agent/src/.../schemas.py   (Future)                        │
│  ├── VendasChatRequest(AgentChatRequest)                                    │
│  └── VendasChatResponse(AgentChatResponse)                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

Key Principle:
- vizu_models.agent_types: Base types shared across all agents
- Each agent's schemas.py: Extends base types with agent-specific fields
- Ensures consistency and code reuse across multiple LangGraph flows
```

---

## **💡 Observations & Recommendations**

### ✅ Strengths
1. **Clean tool/registration separation** — Logic in factories, registration in `tools.py`
2. **Multi-tenant security** — Context split pattern is solid
3. **Redis checkpointing** — Conversation memory persists across sessions
4. **Langfuse SDK v3** — Correctly using metadata-based trace attributes
5. **Context caching** — ContextService caches client data in Redis (5 min TTL)
6. **Dynamic tool filtering** — Tools filtered per-client based on DB flags
7. **Shared agent types** — `vizu_models.agent_types` enables code reuse
8. **Consolidated observability** — Langfuse code centralized in `vizu_llm_service`, thin wrapper in `atendente_core`
9. **HITL System** — Full human-in-the-loop pipeline with Streamlit dashboard
10. **Modular tool architecture** — Domain-specific modules in `tool_modules/` package

### ⚠️ Gaps to Address

1. ~~**No MCP Resources**~~ ✅ Implemented in `resources.py`

2. ~~**No MCP Prompts**~~ ✅ Implemented in `prompts.py`

3. ~~**No Elicitation**~~ ✅ Implemented (Phase 3)

4. ~~**No Server Composition**~~ ✅ Implemented as modular tool architecture

5. ~~**No HITL System**~~ ✅ Implemented (Phase 6)

6. **Experiment Manifests** — Structured experiment definitions (YAML/JSON) not yet implemented
   - Consider using `ferramentas/evaluation_suite/` patterns

### 🎯 Quick Wins (Low effort, high impact)

1. ~~**Add `@mcp.resource` for knowledge bases**~~ ✅ Done
2. ~~**Move system prompt to `@mcp.prompt`**~~ ✅ Done
3. ~~**Add HITL dashboard**~~ ✅ Done
4. **Add Langfuse prompt management** — 4-8 hours (Langfuse has native prompt versioning)
5. **Create experiment manifest schema** — Enable reproducible experiments

---

## **Phased Roadmap**

### **Phase 1: Modular MCP Service Registry**
**Objective:** Refactor core services (RAG, SQL, etc.) into MCP servers exposing resources, tools, and prompts.
- **Actions:**
  - Register all major resources, tools, and prompts via FastMCP decorators.
  - Construct a service registry using FastMCP server composition—allow live-linking and dynamic endpoint mounting.
  - Document interfaces and usage contracts for all MCP endpoints.

> **📋 Current Status:** Tools registered ✅. Resources and prompts not yet implemented.
>
> **🔧 Suggested Implementation:**
> ```python
> # In tools.py, add resources:
> @mcp.resource("knowledge://{cliente_id}/base")
> async def get_knowledge_base(cliente_id: str) -> str:
>     """Returns the full knowledge base content for a client."""
>     # Use vizu_rag_factory to fetch all documents
>     ...
>
> @mcp.resource("config://{cliente_id}/prompt")
> async def get_client_prompt(cliente_id: str) -> str:
>     """Returns the custom prompt for a client."""
>     ctx = await get_client_context(cliente_id)
>     return ctx.prompt_base
> ```

**Checkpoint:** Agents discover and orchestrate all services/tools/resources via MCP, with registry transparency.

### **Phase 2: Dynamic Personalized Context**
**Objective:** Enable workflow, data, and tool selection to adapt in real time to session/user/context.
- **Actions:**
  - Pass and mutate context variables through agent/tool flows (user, business logic, permissions, history).
  - Mount external dynamic sources as FastMCP resources—with context-dependent loading and ACL.
  - Integrate context mutability into experiment manifests.

> **📋 Status:** ✅ **IMPLEMENTED**
>
> **✅ Implementations:**
> - `ContextService` with Redis caching (5 min TTL) for client data
> - `filter_tools_for_client()` in `nodes.py` — filters MCP tools based on client permissions
> - `build_dynamic_system_prompt()` in `nodes.py` — generates context-aware prompts
> - `GET /context` endpoint — returns client context and available tools
> - `TOOL_PERMISSIONS` mapping in `nodes.py`
>
> **📁 Key Files:**
> ```
> services/atendente_core/src/atendente_core/core/nodes.py
>   - filter_tools_for_client(all_tools, safe_context) -> List[Tool]
>   - build_dynamic_system_prompt(safe_context, available_tools) -> str
>   - TOOL_PERMISSIONS dict
>
> services/atendente_core/src/atendente_core/api/router.py
>   - GET /context endpoint
>
> libs/vizu_context_service/src/vizu_context_service/context_service.py
>   - ContextService class (DB load + Redis cache)
> ```
>
> **Example Tool Filtering:**
> ```python
> TOOL_PERMISSIONS = {
>     "executar_rag_cliente": "ferramenta_rag_habilitada",
>     "executar_sql_agent": "ferramenta_sql_habilitada",
>     "ferramenta_publica_de_teste": None,  # Always available
> }
>
> def filter_tools_for_client(all_tools, safe_context):
>     available = []
>     for tool in all_tools:
>         flag = TOOL_PERMISSIONS.get(tool.name)
>         if flag is None or getattr(safe_context, flag, False):
>             available.append(tool)
>     return available
> ```

**Checkpoint:** ✅ Personalized workflows verified — tools filtered per client, dynamic prompts include context.

### **Phase 3: Human-in-the-Loop/Elicitation**
**Objective:** Incorporate structured elicitation into agent flows for approvals, disambiguation, annotation, or escalation.
- **Actions:**
  - Implement elicitation server endpoints, enable agents to pause for user/API input, then resume.
  - Register elicitation events in Langfuse/experiment spans and results.
  - Design prompt flows to anticipate/handle elicitation, document run logic.

> **📋 Status:** 🔄 **IN PROGRESS**
>
> **🔧 Implementation Strategy:**
>
> Since MCP's native `ctx.elicit()` requires client-side protocol support, we implement
> elicitation as a **state-based pattern** in LangGraph:
>
> ```
> ┌─────────────────────────────────────────────────────────────────┐
> │                    ELICITATION FLOW                             │
> ├─────────────────────────────────────────────────────────────────┤
> │                                                                  │
> │  1. Tool determines elicitation is needed                       │
> │     └── Returns ElicitationRequest instead of result           │
> │                                                                  │
> │  2. LangGraph detects pending elicitation                       │
> │     └── Saves state with elicitation_pending = True            │
> │     └── Returns response asking for user input                  │
> │                                                                  │
> │  3. User responds (via same /chat endpoint)                     │
> │     └── Request includes elicitation_response field            │
> │                                                                  │
> │  4. LangGraph resumes from saved state                          │
> │     └── Passes response to waiting tool                        │
> │     └── Tool completes execution                                │
> │                                                                  │
> └─────────────────────────────────────────────────────────────────┘
> ```
>
> **📌 Note:** This approach leverages existing Redis checkpointing for state persistence.

**Checkpoint:** Elicitation events function within experiments and agent flows; all human-in-the-loop cases logged and measured.

### **Phase 4: Dynamic Tool/Resource Orchestration**
**Objective:** Scale agent intelligence and flexibility by compositional tool/resource chaining, proxying, and aggregation.
- **Actions:**
  - Ensure all tools/resources are MCP-registered and versioned, with dynamic endpoint adaptation per context.
  - Use server composition to aggregate microservice capabilities under unified agent endpoints.
  - Validate aggregate workflows in registry and experiment manifests.

> **📋 Status:** ✅ **IMPLEMENTED** (Modular Tool Architecture)
>
> **🔧 Implementation: Modular Tool Organization**
>
> Instead of server composition with multiple MCP servers, we implemented a **modular tool
> architecture** within `tool_pool_api` that provides similar benefits with less complexity:
>
> ```
> tool_pool_api/
> └── server/
>     ├── tools.py                 # Entry point, delegates to modules
>     └── tool_modules/            # Domain-specific modules
>         ├── __init__.py          # Registry + register_all_tools()
>         ├── rag_module.py        # RAG tools (executar_rag_cliente)
>         ├── sql_module.py        # SQL tools (executar_sql_agent)
>         └── common_module.py     # Public utilities (ping, test)
> ```
>
> **📌 Architecture Benefits:**
> - **Separation of Concerns:** Each domain has its own module with logic + registration
> - **Lazy Loading:** Heavy dependencies only loaded when module is registered
> - **Testability:** Logic functions (`_*_logic`) are pure and easily testable
> - **Extensibility:** New modules added by creating file + using `@register_module`
> - **Metadata:** `AVAILABLE_MODULES` provides introspection for discovery
> - **HTTP Transport:** Migrated from SSE to modern Streamable HTTP
> - **Deterministic Endpoints:** `/health` and `/info` are HTTP-only, not MCP tools
>
> **📌 Adding a New Tool Module:**
> ```python
> # tool_modules/scheduling_module.py
> from . import register_module
>
> @register_module
> def register_tools(mcp: FastMCP) -> List[str]:
>     @mcp.tool(name="agendar_servico", description="...")
>     async def agendar_servico(data: str, servico: str): ...
>
>     return ["agendar_servico"]
> ```
>
> **📌 Available Modules (3 total):**
> | Module | Tools | Auth Required |
> |--------|-------|---------------|
> | `rag` | `executar_rag_cliente` | ✅ Yes |
> | `sql` | `executar_sql_agent` | ✅ Yes |
> | `common` | `ferramenta_publica_de_teste` | ❌ No |
>
> **📌 HTTP Endpoints (não MCP):**
> | Endpoint | Descrição |
> |----------|-----------|
> | `GET /health` | Health check para k8s/load balancers |
> | `GET /info` | Metadata do servidor para admin |

**Checkpoint:** ✅ Tools organized by domain, easy to extend, metadata available for introspection.

### **Phase 5: Structured Prompt Design/Management**
**Objective:** Tightly couple prompt templates and output schemas with MCP context, workflow phases, and evaluation needs.
- **Actions:**
  - Build prompt registry with versioning, output typing, context variable embedding.
  - Compose prompts for multi-step workflow (retrieval → summarization → action → elicitation).
  - Validate and record prompt schema matches during all experiments and agent sessions.

> **📋 Status:** ✅ **IMPLEMENTED**
>
> **🔧 Implementation: Versioned Prompt System**
>
> Prompts são gerenciados em duas camadas:
>
> 1. **MCP Prompts (`tool_pool_api/server/prompts.py`):**
>    - Templates expostos via protocolo MCP
>    - Podem ser chamados por clientes MCP
>    - Versionados por nome (ex: `atendente/system/v1`, `atendente/system/v2`)
>
> 2. **Database Prompts (`PromptTemplate`):**
>    - Armazenados na tabela `prompt_template`
>    - Suportam override por cliente (`cliente_vizu_id`)
>    - Versionamento numérico (`version`)
>    - Variáveis dinâmicas: `{{nome_empresa}}`, `{{horario_formatado}}`, etc.
>
> ```
> ┌─────────────────────────────────────────────────────────────────┐
> │                    PROMPT RESOLUTION                            │
> ├─────────────────────────────────────────────────────────────────┤
> │                                                                  │
> │  1. nodes.py: build_dynamic_system_prompt()                     │
> │     └── Tenta buscar prompt do DB (get_prompt_from_db)         │
> │                                                                  │
> │  2. Prioridade de busca no DB:                                  │
> │     └── 1º: Prompt específico do cliente (cliente_vizu_id)     │
> │     └── 2º: Prompt global (cliente_vizu_id = NULL)             │
> │                                                                  │
> │  3. Se não encontrar no DB:                                     │
> │     └── Usa fallback hardcoded (prompt_parts)                  │
> │                                                                  │
> │  4. Substitui variáveis dinâmicas:                              │
> │     └── {{nome_empresa}}, {{prompt_personalizado}}, etc.       │
> │                                                                  │
> └─────────────────────────────────────────────────────────────────┘
> ```
>
> **📌 Prompts MCP Disponíveis:**
> | Nome | Descrição | Parâmetros |
> |------|-----------|------------|
> | `atendente/system/v1` | System prompt básico | `nome_empresa` |
> | `atendente/system/v2` | System prompt completo | `cliente_id` |
> | `atendente/confirmacao-agendamento` | Confirmação de agenda | `data`, `horario`, `servico` |
> | `atendente/esclarecimento` | Desambiguação | `pergunta`, `opcoes` |
> | `rag/query` | Template RAG | `context`, `question` |
> | `db/render` | Renderiza prompt do DB | `name`, `variables`, `version`, `cliente_id` |

**Checkpoint:** ✅ All prompts are versioned, structured, and linked to context, workflow step, experiment result.

### **Phase 6: Evaluation & Experimentation**
**Objective:** Run reproducible, protocol-driven experiments using MCP registry endpoints, context variants, and Langfuse traces.
- **Actions:**
  - Draft/maintain experiment manifests keyed to MCP endpoints, context settings, and registry versions.
  - Instrument all workflow steps and elicitation events for Langfuse traceability.
  - Measure agent performance/metrics on protocol-aligned experimental tasks.
  - Develop simple streamlit interface for human in the loop interactions, it should have a a mechanism that determine which messages go for human in the loop.

> **📋 Status:** ✅ **IMPLEMENTED** (HITL + Langfuse Integration)
>
> **🔧 Implementation: Human-in-the-Loop System**
>
> Sistema completo de HITL para criação de datasets e controle de qualidade:
>
> ```
> ┌─────────────────────────────────────────────────────────────────────────────┐
> │                    HUMAN-IN-THE-LOOP WORKFLOW                               │
> ├─────────────────────────────────────────────────────────────────────────────┤
> │                                                                              │
> │  1. LLM responde normalmente                                                │
> │     ├── Confiança alta (>threshold): envia direto                          │
> │     └── Confiança baixa/critério ativado: marca para revisão               │
> │                                                                              │
> │  2. HitlService.evaluate() verifica critérios configurados                 │
> │     └── Múltiplos critérios ordenados por prioridade                       │
> │                                                                              │
> │  3. Se should_review=True:                                                  │
> │     └── HitlQueue.enqueue() → Redis sorted set                             │
> │                                                                              │
> │  4. Streamlit Dashboard (apps/hitl_dashboard)                               │
> │     ├── Lista mensagens pendentes por cliente                              │
> │     ├── Revisor pode: aprovar / corrigir / rejeitar / escalar             │
> │     └── Feedback salvo + exportado para Langfuse dataset                   │
> │                                                                              │
> │  5. Dataset cresce organicamente                                            │
> │     ├── Bons exemplos: LLM acertou (aprovados)                             │
> │     ├── Correções: humano corrigiu (golden samples)                        │
> │     └── Rejeitados: casos problemáticos para análise                       │
> │                                                                              │
> └─────────────────────────────────────────────────────────────────────────────┘
> ```
>
> **📌 Critérios de Roteamento HITL (Configuráveis):**
> | Critério | Descrição | Params |
> |----------|-----------|--------|
> | `low_confidence` | Confiança < threshold | `threshold: 0.7` |
> | `elicitation_pending` | Elicitation em andamento | — |
> | `tool_call_failed` | Ferramenta retornou erro | — |
> | `keyword_trigger` | Palavras-chave detectadas | `keywords: [...]` |
> | `first_n_messages` | Primeiras N mensagens | `n: 3` |
> | `random_sample` | Amostragem aleatória | `rate: 0.05` |
> | `manual_flag` | Marcação manual | — |
> | `sentiment_negative` | Sentimento negativo | `patterns: [...]` |
> | `long_response_time` | Resposta demorada | `threshold_seconds: 30` |
>
> **📁 Arquivos Implementados:**
> ```
> libs/vizu_models/src/vizu_models/hitl.py
>   - HitlReview, HitlConfig, HitlCriterion, HitlDecision
>   - HitlCriteriaType, HitlReviewStatus, HitlFeedbackType
>
> libs/vizu_hitl_service/
>   - HitlService: avaliação de critérios
>   - HitlQueue: fila Redis com priorização
>   - LangfuseDatasetManager: integração com datasets
>
> apps/hitl_dashboard/
>   - Streamlit app para revisão humana
>   - Páginas: Pendentes, Estatísticas, Datasets, Config
>
> services/atendente_core/src/atendente_core/core/
>   - hitl_integration.py: integração no fluxo do agente
>   - service.py: chamada evaluate_and_submit após cada resposta
> ```
>
> **📌 Configuração via Ambiente:**
> ```bash
> HITL_ENABLED=true                    # Ativa o sistema HITL
> HITL_CONFIDENCE_THRESHOLD=0.7        # Threshold de confiança
> HITL_SAMPLE_RATE=0.05                # Taxa de amostragem aleatória
> HITL_TTL_HOURS=24                    # TTL na fila
> ```
>
> **📌 Uso do Dashboard:**
> ```bash
> cd apps/hitl_dashboard
> poetry install
> poetry run streamlit run src/hitl_dashboard/app.py
> ```
>
> **🔧 Suggested Next Steps:**
> ```yaml
> # experiments/atendente_v1.yaml
> name: atendente_baseline
> version: 1.0.0
>
> registry:
>   mcp_endpoint: http://tool_pool_api:9000/mcp/
>   tools_version: v2.11.0
>
> context_variants:
>   - name: studio_j_rag_only
>     cliente_id: 83c94590-ca01-4991-8cbd-18e016c64222
>     enabled_tools: [executar_rag_cliente]
>   - name: studio_j_full
>     cliente_id: 83c94590-ca01-4991-8cbd-18e016c64222
>     enabled_tools: [executar_rag_cliente, executar_sql_agent]
>
> test_cases:
>   - input: "Quais serviços vocês oferecem?"
>     expected_tool: executar_rag_cliente
>     expected_contains: ["corte", "coloração"]
>
> langfuse:
>   tags: [experiment, baseline]
>   session_prefix: exp-baseline-
> ```
>
> **📌 See:** `ferramentas/evaluation_suite/` for existing eval patterns.

**Checkpoint:** Every experiment is reproducible, registry-linked, fully context-traceable, and outputs clear metrics.

---

## **Measurement & Validation Objectives**
- **Coverage:** 100% of agentic endpoints (tools/resources/prompts) are MCP-registered and discoverable.
- **Traceability:** All agent flows, context mutations, and elicitation events are captured in Langfuse traces and experiment logs.
- **Reproducibility:** Experiments rerun with identical registry/context yield consistent traces and outcome metrics.
- **Personalization:** Variable context demonstrates measurable improvement in agent accuracy, relevance, or user success rates.
- **Human-in-the-Loop:** Elicitation events are sampled, logged, and show reduction in ambiguous/error cases or annotated by SME review.
- **Extensibility:** Onboarding a new MCP resource/tool/prompt takes < N hours and is validated by registry and experiment run.

> **📊 Current Metrics (December 2025):**
> - Tools registered: 3/3 ✅
> - Resources registered: 6/6 ✅ (knowledge + config)
> - Prompts registered: 5/5 ✅ (system, RAG, elicitation, etc.)
> - HITL system: ✅ Implemented (vizu_hitl_service + Streamlit dashboard)
> - Langfuse coverage: ~95% (LangGraph + LLM + HITL events traced)
> - Experiment manifests: 0 (see `ferramentas/evaluation_suite/` for patterns)
> - Code cleanup: ✅ Removed duplicate Langfuse code, unused imports cleaned

---

## **General Principles**
- Prioritize modular MCP registration and context composition for every new tool, resource, or prompt.
- Keep registry and manifests up to date and versioned.
- Instrument all flows for metrics and trace context transitions, human-in-the-loop events, and tool orchestration.
- All experiment/eval logic lives outside of prod; rapid iteration in dev environments only.

---

## **🚀 Suggested Priority Order**

Based on the repository analysis, here's a recommended implementation order:

### ✅ Completed Sprints

#### Sprint 1: Foundation (Completed)
1. ✅ **Add MCP Resources for knowledge bases** — Exposes RAG content as readable resources
2. ✅ **Move system prompt to DB + MCP** — Enable versioning and per-client customization
3. ✅ **Document current MCP interface** — Tools, resources, prompts documented

#### Sprint 2: Context Engineering (Completed)
4. ✅ **Implement dynamic tool filtering** — Based on client tier/permissions
5. ✅ **Add MCP Prompts** — Versioned prompt templates via FastMCP
6. ✅ **Enhance Langfuse traces** — Custom spans for RAG retrieval, tool execution

#### Sprint 3: Human-in-the-Loop (Completed)
7. ✅ **Design elicitation protocol** — State-based pattern in LangGraph
8. ✅ **Implement HITL system** — Full pipeline with criteria-based routing
9. ✅ **Add Streamlit dashboard** — Review interface with dataset export

### 🔄 Next Sprint: Experimentation

#### Sprint 4: Experiment Suite (Completed ✅)
10. ✅ **Create experiment manifest schema** — YAML format with clients, cases, HITL config
11. ✅ **Build ExperimentRunner** — Concurrent execution against atendente API
12. ✅ **Add ResponseClassifier** — Routes cases to auto-approve or HITL queue
13. ✅ **Create TrainingDatasetGenerator** — Exports approved cases to Langfuse datasets
14. ✅ **Add DB migrations** — `experiment_run` and `experiment_case` tables
15. ✅ **Langfuse-First Refactoring** — Native SDK integration

---

## **🔄 Langfuse-First Architecture (December 2025)**

### Design Principles

1. **Langfuse is the Source of Truth** for prompts, datasets, and experiments
2. **Local cache for high availability** — Production prompts cached in DB
3. **YAML manifests for orchestration** — Define experiments locally, sync to Langfuse
4. **HITL stays local** — Custom workflow via Streamlit, sync results to Langfuse

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      LANGFUSE-FIRST ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         LANGFUSE CLOUD                               │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────┐   │    │
│  │  │   Prompts   │  │  Datasets   │  │ Experiments │  │  Scores  │   │    │
│  │  │  (versioned)│  │(training/eval)│ │ (SDK runs) │  │ (traces) │   │    │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └────┬─────┘   │    │
│  └─────────┼────────────────┼────────────────┼───────────────┼────────┘    │
│            │                │                │               │              │
│            ▼                ▼                ▼               ▼              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    vizu_llm_service.PromptService                    │    │
│  │  ┌───────────────────────────────────────────────────────────────┐  │    │
│  │  │ 1. Fetch from Langfuse (primary)                              │  │    │
│  │  │ 2. Cache in memory (5 min TTL)                                │  │    │
│  │  │ 3. Sync "production" label to local DB (fallback)            │  │    │
│  │  │ 4. If Langfuse down → Use DB cache                           │  │    │
│  │  └───────────────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │               vizu_experiment_service.LangfuseExperimentRunner       │    │
│  │  ┌───────────────────────────────────────────────────────────────┐  │    │
│  │  │ 1. Load YAML manifest (local)                                 │  │    │
│  │  │ 2. Sync test cases → Langfuse Dataset                         │  │    │
│  │  │ 3. Run via langfuse.run_experiment() with evaluators          │  │    │
│  │  │ 4. Store results in local DB (tracking)                       │  │    │
│  │  │ 5. Route low-confidence → HITL queue                          │  │    │
│  │  └───────────────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                  vizu_hitl_service.LangfuseDatasetManager            │    │
│  │  ┌───────────────────────────────────────────────────────────────┐  │    │
│  │  │ On review approved:                                           │  │    │
│  │  │   1. Add score to original trace (hitl_approved, hitl_quality)│  │    │
│  │  │   2. Create dataset item in "hitl-training"                   │  │    │
│  │  │   3. Link to source trace for traceability                    │  │    │
│  │  └───────────────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Source of Truth | Local Role |
|-----------|-----------------|------------|
| **Prompts** | Langfuse Prompt Management | DB cache for fallback |
| **Datasets** | Langfuse Datasets | YAML manifests for definition |
| **Experiments** | Langfuse Experiments | CLI for orchestration |
| **Traces** | Langfuse Tracing | Already integrated |
| **Scores** | Langfuse Scores | Created from HITL reviews |
| **HITL Reviews** | Local DB + Streamlit | Synced to Langfuse on approval |

### New Files Added

```
libs/vizu_llm_service/src/vizu_llm_service/
├── prompt_service.py          # PromptService (Langfuse-First)
│   ├── LangfusePromptClient   # Wrapper for Langfuse prompt API
│   ├── PromptCacheDB          # Local DB cache
│   ├── PromptService          # Main API with fallback logic
│   └── get_prompt()           # Convenience function

libs/vizu_experiment_service/src/vizu_experiment_service/
├── langfuse_runner.py         # LangfuseExperimentRunner
│   ├── sync_manifest_to_dataset()    # YAML → Langfuse Dataset
│   ├── run_from_manifest()           # Uses langfuse.run_experiment()
│   ├── create_training_dataset_from_approved()
│   └── evaluators                    # tool, contains, confidence

libs/vizu_hitl_service/src/vizu_hitl_service/
├── langfuse_integration.py    # LangfuseDatasetManager (enhanced)
│   ├── score_trace()                 # Add HITL scores to traces
│   ├── add_review_to_dataset()       # Create training items
│   ├── sync_pending_to_langfuse()    # Batch sync
│   └── create_evaluation_dataset()   # Sample for eval
```

### CLI Commands

```bash
# Run experiment using Langfuse SDK (recommended)
poetry run python -m vizu_experiment_service.cli run manifest.yaml

# Run with legacy runner (httpx only)
poetry run python -m vizu_experiment_service.cli run manifest.yaml --legacy

# Sync manifest to Langfuse Dataset without running
poetry run python -m vizu_experiment_service.cli sync manifest.yaml

# Classify results and route to HITL
poetry run python -m vizu_experiment_service.cli classify <run_id>

# Export to JSONL for fine-tuning
poetry run python -m vizu_experiment_service.cli export <run_id> --output data.jsonl
```

### Prompt Usage Example

```python
from vizu_llm_service import PromptService, get_prompt

# Option 1: Using service
service = PromptService(db_session=session)
prompt = await service.get_prompt(
    name="atendente/system",
    label="production",  # Langfuse label
)

# Compile with variables
text = prompt.compile(
    client_name="Studio J",
    tools_available=["RAG", "SQL"],
)

# Option 2: Using convenience function
prompt = await get_prompt("atendente/system", db_session=session)
messages = prompt.to_messages(client_name="Studio J")
```

### Experiment Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LANGFUSE-FIRST EXPERIMENT PIPELINE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. YAML Manifest (local)                                                    │
│     └── Defines: clients, test cases, HITL thresholds                       │
│                                                                              │
│  2. Sync to Langfuse                                                         │
│     └── Creates dataset: "experiment/{manifest_name}"                       │
│     └── Each case → dataset_item with input/expected_output                 │
│                                                                              │
│  3. Run Experiment via SDK                                                   │
│     └── langfuse.run_experiment(dataset, task=atendente_api)                │
│     └── Evaluators: tool_assertion, contains_assertion, confidence          │
│     └── All traces auto-linked to dataset run                               │
│                                                                              │
│  4. Process Results                                                          │
│     └── HIGH_CONFIDENCE → auto-approved                                      │
│     └── LOW_CONFIDENCE → route to HITL queue                                │
│     └── Store in local DB for tracking                                      │
│                                                                              │
│  5. HITL Review (Streamlit)                                                  │
│     └── Reviewer approves/corrects/rejects                                  │
│     └── On approval:                                                        │
│         ├── Score added to original trace                                   │
│         └── Item added to "hitl-training" dataset                           │
│                                                                              │
│  6. Training Dataset                                                         │
│     └── Langfuse dataset with approved interactions                         │
│     └── Can be used for fine-tuning or evaluation                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## **❓ Questions Resolved**

1. **Elicitation Transport:** ✅ Handover tool for human feedback (future enhancement, not priority)
   - Current: Inline with agent response
   - Future: Can add explicit pause/resume or Twilio interactive messages

2. **Prompt Storage:** ✅ Langfuse-First with DB fallback
   - Primary: Langfuse Prompt Management (version control, A/B testing)
   - Fallback: Local DB cache of "production" labeled prompts
   - See: `vizu_llm_service.PromptService`

3. **Server Composition vs Modules:** ✅ Modular tool architecture
   - Current: Single server with `tool_modules/` package
   - Pattern: Domain-specific modules (rag_module, sql_module, common_module)

4. **Experiment Cadence:** ✅ Manual trigger via Make commands
   - CLI: `poetry run python -m vizu_experiment_service.cli run <manifest>`
   - Future: CI integration possible via GitHub Actions

---

## **References for Implementation**
- [FastMCP Context](https://fastmcp.mintlify.app/servers/context)
- [FastMCP Elicitation](https://fastmcp.mintlify.app/servers/elicitation)
- [FastMCP Tools](https://fastmcp.mintlify.app/clients/tools)
- [FastMCP Resources](https://fastmcp.mintlify.app/clients/resources)
- [FastMCP Prompts](https://fastmcp.mintlify.app/clients/prompts)
- [Langfuse Prompt Management](https://langfuse.com/docs/prompts/get-started)
- [Langfuse Datasets](https://langfuse.com/docs/datasets)

---

## **📁 Related Files in Repository**

| Purpose | Path |
|---------|------|
| MCP Server | `services/tool_pool_api/src/server/` |
| LangGraph Agent | `services/atendente_core/src/atendente_core/core/` |
| Langfuse Integration | `services/atendente_core/src/atendente_core/core/observability.py` |
| Langfuse Core (Shared) | `libs/vizu_llm_service/src/vizu_llm_service/client.py` |
| RAG Factory | `libs/vizu_rag_factory/` |
| SQL Factory | `libs/vizu_sql_factory/` |
| HITL Service | `libs/vizu_hitl_service/` |
| HITL Dashboard | `apps/hitl_dashboard/` |
| Experiment Service | `libs/vizu_experiment_service/` |
| Experiment Models | `libs/vizu_models/src/vizu_models/experiment.py` |
| Example Manifest | `ferramentas/evaluation_suite/workflows/atendente/example_manifest.yaml` |
| Evaluation Suite | `ferramentas/evaluation_suite/` |
| Shared Models | `libs/vizu_shared_models/` |

---