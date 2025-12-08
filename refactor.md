🚀 COPILOT PROMPT: Multi-Agent Architecture with Dynamic Tool Allocation & Docker MCP Integration

---
## 📊 IMPLEMENTATION PROGRESS

**Last Updated:** December 5, 2025

### ✅ COMPLETED

#### Phase 1.1: Update vizu_models ✓
- [x] Added `enabled_tools: List[str]` field to `ClienteVizu` model
- [x] Added `tier_required` and `docker_mcp_integration` to `ToolInfo`
- [x] Added `ToolCategory` enum (RAG, SQL, SCHEDULING, DOCKER_MCP, PUBLIC)
- [x] Updated `TierCliente` with comparison operators (`__lt__`, `__le__`, etc.)
- [x] Updated `ClientContextResponse` with `enabled_tools`, `tier`, `docker_mcp_enabled`
- [x] Updated `VizuClientContext` with `enabled_tools` and `get_enabled_tools_list()` helper
- [x] Updated `SafeClientContext` and `InternalClientContext` with new fields
- [x] Added backward compatibility via `get_enabled_tools_list()` fallback to legacy booleans

**Files Modified:**
- `libs/vizu_models/src/vizu_models/enums.py`
- `libs/vizu_models/src/vizu_models/agent_types.py`
- `libs/vizu_models/src/vizu_models/cliente_vizu.py`
- `libs/vizu_models/src/vizu_models/vizu_client_context.py`
- `libs/vizu_models/src/vizu_models/safe_client_context.py`
- `libs/vizu_models/src/vizu_models/__init__.py`

#### Phase 1.2: Create DB Migration ✓
- [x] Created migration `20251205_add_enabled_tools_column.py`
- [x] Added `enabled_tools` JSONB column with backfill from legacy booleans
- [x] Created GIN index for efficient `enabled_tools @> '["tool"]'` queries
- [x] Added helper functions: `add_tool_to_client()`, `remove_tool_from_client()`, `client_has_tool()`
- [x] Marked legacy columns as DEPRECATED via SQL comments

**Files Created:**
- `libs/vizu_db_connector/alembic/versions/20251205_add_enabled_tools_column.py`

#### Phase 2.1: Create vizu_tool_registry lib ✓
- [x] Created `ToolMetadata` dataclass with tier comparison
- [x] Created `ToolRegistry` with builtin, Google, and Docker MCP tools
- [x] Created `TierValidator` with tier definitions and upgrade/downgrade logic
- [x] Created `DockerMCPBridge` for Docker MCP integration discovery
- [x] Created exception classes: `ToolNotFoundError`, `TierAccessDeniedError`, etc.
- [x] Created comprehensive test suite (50+ tests)

**Files Created:**
- `libs/vizu_tool_registry/pyproject.toml`
- `libs/vizu_tool_registry/README.md`
- `libs/vizu_tool_registry/src/vizu_tool_registry/__init__.py`
- `libs/vizu_tool_registry/src/vizu_tool_registry/tool_metadata.py`
- `libs/vizu_tool_registry/src/vizu_tool_registry/registry.py`
- `libs/vizu_tool_registry/src/vizu_tool_registry/tier_validator.py`
- `libs/vizu_tool_registry/src/vizu_tool_registry/docker_mcp_bridge.py`
- `libs/vizu_tool_registry/src/vizu_tool_registry/exceptions.py`
- `libs/vizu_tool_registry/tests/test_registry.py`

#### Phase 2.2: Create vizu_mcp_commons lib ✓
- [x] Created exception classes: `MCPError`, `MCPAuthError`, `MCPAuthorizationError`, `MCPToolError`, etc.
- [x] Created `TokenValidator` class with JWT validation and claims parsing
- [x] Created `TokenClaims` dataclass with expiration checks
- [x] Created `MCPTokenExtractor` for FastMCP context extraction
- [x] Created dependency utilities: `get_context_service`, `get_redis_client`, `DependencyContainer`
- [x] Created `inject_cliente_context` middleware decorator
- [x] Created `require_tool` and `require_tier` decorators
- [x] Created `ToolExecutor` with parallel execution support
- [x] Created `ToolCall`, `ToolResult`, `ToolCallBuilder` classes
- [x] Created `ResourceLoader` and `MCPResourceBuilder` for dynamic resources
- [x] Created comprehensive test suite (50+ tests)

**Files Created:**
- `libs/vizu_mcp_commons/pyproject.toml`
- `libs/vizu_mcp_commons/README.md`
- `libs/vizu_mcp_commons/src/vizu_mcp_commons/__init__.py`
- `libs/vizu_mcp_commons/src/vizu_mcp_commons/exceptions.py`
- `libs/vizu_mcp_commons/src/vizu_mcp_commons/auth.py`
- `libs/vizu_mcp_commons/src/vizu_mcp_commons/dependencies.py`
- `libs/vizu_mcp_commons/src/vizu_mcp_commons/middleware.py`
- `libs/vizu_mcp_commons/src/vizu_mcp_commons/tool_executor.py`
- `libs/vizu_mcp_commons/src/vizu_mcp_commons/resource_loader.py`
- `libs/vizu_mcp_commons/tests/test_mcp_commons.py`

### ✅ PHASE 2 COMPLETED

#### Phase 2.5: Create vizu_agent_framework lib ✓
- [x] Created `AgentConfig` dataclass with validation and fluent API
- [x] Created `AgentState` TypedDict with annotated reducers for LangGraph
- [x] Created `create_initial_state()` helper function
- [x] Created `NodeRegistry` for registering custom nodes
- [x] Created built-in nodes: `init_node`, `elicit_node`, `execute_tool_node`, `respond_node`, `end_node`
- [x] Created routing functions: `route_from_elicit`, `route_from_tool`, `should_continue`
- [x] Created `MCPToolExecutor` with HTTP client, retries, and parallel execution
- [x] Created `MockMCPToolExecutor` for testing
- [x] Created `RedisCheckpointer` for LangGraph state persistence
- [x] Created `AgentBuilder` factory with fluent API and default graph structure
- [x] Created predefined configs: `ATENDENTE_CONFIG`, `VENDAS_CONFIG`, `SUPPORT_CONFIG`
- [x] Created comprehensive test suite (50+ tests)

**Files Created:**
- `libs/vizu_agent_framework/pyproject.toml`
- `libs/vizu_agent_framework/README.md`
- `libs/vizu_agent_framework/src/vizu_agent_framework/__init__.py`
- `libs/vizu_agent_framework/src/vizu_agent_framework/config.py`
- `libs/vizu_agent_framework/src/vizu_agent_framework/state.py`
- `libs/vizu_agent_framework/src/vizu_agent_framework/nodes.py`
- `libs/vizu_agent_framework/src/vizu_agent_framework/routing.py`
- `libs/vizu_agent_framework/src/vizu_agent_framework/mcp_executor.py`
- `libs/vizu_agent_framework/src/vizu_agent_framework/checkpointer.py`
- `libs/vizu_agent_framework/src/vizu_agent_framework/builder.py`
- `libs/vizu_agent_framework/tests/__init__.py`
- `libs/vizu_agent_framework/tests/test_agent_framework.py`

#### Phase 2.3: Create vizu_prompt_management lib ✓
- [x] Created `PromptTemplateConfig` dataclass with category, required/optional variables
- [x] Created 12 built-in templates (system, action, RAG, elicitation, error)
- [x] Created `TemplateRenderer` with Jinja2 and simple placeholder support
- [x] Created `SafeRenderer` with size limits and output truncation
- [x] Created `PromptVariables` dataclass with `to_dict()` method
- [x] Created `VariableExtractor` for context/dict extraction
- [x] Created `ContextVariableBuilder` with fluent interface
- [x] Created `PromptLoader` with database and builtin fallback
- [x] Created `PromptManager` for versioning and rollback
- [x] Created `MCPPromptBuilder` for FastMCP integration
- [x] Created comprehensive test suite (30+ tests)

**Files Created:**
- `libs/vizu_prompt_management/pyproject.toml`
- `libs/vizu_prompt_management/README.md`
- `libs/vizu_prompt_management/src/vizu_prompt_management/__init__.py`
- `libs/vizu_prompt_management/src/vizu_prompt_management/templates.py`
- `libs/vizu_prompt_management/src/vizu_prompt_management/renderer.py`
- `libs/vizu_prompt_management/src/vizu_prompt_management/variables.py`
- `libs/vizu_prompt_management/src/vizu_prompt_management/loader.py`
- `libs/vizu_prompt_management/src/vizu_prompt_management/manager.py`
- `libs/vizu_prompt_management/src/vizu_prompt_management/mcp_builder.py`
- `libs/vizu_prompt_management/tests/test_prompt_management.py`

#### Phase 2.4: Create vizu_elicitation_service lib ✓
- [x] Created `PendingElicitation` TypedDict and `ElicitationResult` dataclass
- [x] Created `ElicitationContext` and local `ElicitationOption` models
- [x] Created exception hierarchy: `ElicitationError`, `ElicitationRequired`, `ElicitationNotFoundError`, etc.
- [x] Created `PendingElicitationStore` with Redis-backed storage and TTL management
- [x] Created `ElicitationResponseHandler` with validation and normalization
- [x] Created `ElicitationManager` as central coordinator
- [x] Created helper functions: `create_confirmation_elicitation`, `create_selection_elicitation`, etc.
- [x] Created `format_elicitation_for_llm` and `validate_elicitation_response` utilities
- [x] Created comprehensive test suite (50+ tests)

**Files Created:**
- `libs/vizu_elicitation_service/pyproject.toml`
- `libs/vizu_elicitation_service/README.md`
- `libs/vizu_elicitation_service/src/vizu_elicitation_service/__init__.py`
- `libs/vizu_elicitation_service/src/vizu_elicitation_service/models.py`
- `libs/vizu_elicitation_service/src/vizu_elicitation_service/exceptions.py`
- `libs/vizu_elicitation_service/src/vizu_elicitation_service/store.py`
- `libs/vizu_elicitation_service/src/vizu_elicitation_service/response_handler.py`
- `libs/vizu_elicitation_service/src/vizu_elicitation_service/manager.py`
- `libs/vizu_elicitation_service/src/vizu_elicitation_service/helpers.py`
- `libs/vizu_elicitation_service/tests/__init__.py`
- `libs/vizu_elicitation_service/tests/test_elicitation_service.py`

### ✅ PHASE 3 COMPLETED

#### Phase 3.1: Simplify tool_pool_api ✓ (Dec 5, 2025)
- [x] Updated `resources.py` to use `ToolRegistry` for dynamic tool filtering
- [x] Updated `prompts.py` to use `vizu_prompt_management.mcp_builder.register_prompts_with_mcp()` with fallback
- [x] Updated `rag_module.py` with `_is_tool_enabled_for_client()` helper using `ToolRegistry`
- [x] Updated `sql_module.py` with same pattern
- [x] Added new resources: `tools://registry`, `tools://{cliente_id}/available`, `tools://tier/{tier}`
- [x] Updated `pyproject.toml` with new library dependencies

**Files Modified:**
- `services/tool_pool_api/src/tool_pool_api/server/resources.py`
- `services/tool_pool_api/src/tool_pool_api/server/prompts.py`
- `services/tool_pool_api/src/tool_pool_api/server/tool_modules/rag_module.py`
- `services/tool_pool_api/src/tool_pool_api/server/tool_modules/sql_module.py`
- `services/tool_pool_api/pyproject.toml`

#### Phase 3.2: Refactor atendente_core ✓ (Dec 5, 2025)
- [x] Added `USE_NEW_FRAMEWORK: bool = False` feature flag to `config.py`
- [x] Updated `service.py` to optionally use `AgentBuilder` from `vizu_agent_framework`
- [x] Updated `nodes.py` to use `ToolRegistry.get_available_tools()` for tool filtering
- [x] Updated `nodes.py` to use `vizu_prompt_management` with graceful fallback (`HAS_PROMPT_MANAGEMENT`)
- [x] Updated `nodes.py` to use `vizu_elicitation_service` with graceful fallback (`HAS_ELICITATION_SERVICE`)
- [x] Updated `pyproject.toml` with new library dependencies and pythonpath

**Files Modified:**
- `services/atendente_core/src/atendente_core/core/config.py`
- `services/atendente_core/src/atendente_core/core/service.py`
- `services/atendente_core/src/atendente_core/core/nodes.py`
- `services/atendente_core/pyproject.toml`

**Key Design Decisions:**
- Feature flag `USE_NEW_FRAMEWORK` allows gradual rollout (default: `False`)
- Graceful fallbacks for all library imports (`HAS_*` constants)
- Legacy boolean tool flags still supported via `get_enabled_tools_list()` fallback
- Services maintain backward compatibility with existing DB data

### ✅ PHASE 4 COMPLETED

#### Phase 4.1: Create vendas_agent ✓ (Dec 5, 2025)
- [x] Created complete service structure following atendente_core patterns
- [x] Implemented `VendasAgent` class using `AgentBuilder` (~60 lines of core logic)
- [x] Sales-specific configuration: `elicitation_strategy="sales_pipeline"`, `max_turns=15`
- [x] Added sales-specific response fields: `suggested_products`, `discount_available`
- [x] Created Dockerfile and pyproject.toml
- [x] Created tests with mocked dependencies

**Files Created (16 files, ~400 lines total):**
- `services/vendas_agent/pyproject.toml`
- `services/vendas_agent/Dockerfile`
- `services/vendas_agent/README.md`
- `services/vendas_agent/.env.example`
- `services/vendas_agent/src/vendas_agent/__init__.py`
- `services/vendas_agent/src/vendas_agent/main.py`
- `services/vendas_agent/src/vendas_agent/core/__init__.py`
- `services/vendas_agent/src/vendas_agent/core/config.py`
- `services/vendas_agent/src/vendas_agent/core/agent.py`
- `services/vendas_agent/src/vendas_agent/core/service.py`
- `services/vendas_agent/src/vendas_agent/api/__init__.py`
- `services/vendas_agent/src/vendas_agent/api/schemas.py`
- `services/vendas_agent/src/vendas_agent/api/auth.py`
- `services/vendas_agent/src/vendas_agent/api/router.py`
- `services/vendas_agent/tests/__init__.py`
- `services/vendas_agent/tests/test_agent.py`

#### Phase 4.2: Create support_agent ✓ (Dec 5, 2025)
- [x] Created complete service structure following vendas_agent patterns
- [x] Implemented `SupportAgent` class using `AgentBuilder` (~70 lines of core logic)
- [x] Support-specific configuration: `elicitation_strategy="issue_classification"`, `max_turns=25`
- [x] Added support-specific features: `issue_category`, `severity`, `escalation_needed`
- [x] Added `/ticket` endpoint for ticket creation
- [x] Created Dockerfile and pyproject.toml
- [x] Created tests with mocked dependencies

**Files Created (16 files, ~450 lines total):**
- `services/support_agent/pyproject.toml`
- `services/support_agent/Dockerfile`
- `services/support_agent/README.md`
- `services/support_agent/.env.example`
- `services/support_agent/src/support_agent/__init__.py`
- `services/support_agent/src/support_agent/main.py`
- `services/support_agent/src/support_agent/core/__init__.py`
- `services/support_agent/src/support_agent/core/config.py`
- `services/support_agent/src/support_agent/core/agent.py`
- `services/support_agent/src/support_agent/core/service.py`
- `services/support_agent/src/support_agent/api/__init__.py`
- `services/support_agent/src/support_agent/api/schemas.py`
- `services/support_agent/src/support_agent/api/auth.py`
- `services/support_agent/src/support_agent/api/router.py`
- `services/support_agent/tests/__init__.py`
- `services/support_agent/tests/test_agent.py`

**Code Reuse Achievement:**
| Agent | Core Agent Lines | Total Service Lines | Framework Reuse |
|-------|-----------------|---------------------|-----------------|
| atendente_core (old) | 1200+ | 2000+ | 0% |
| vendas_agent (new) | ~60 | ~400 | 95% |
| support_agent (new) | ~70 | ~450 | 95% |

### 📋 REMAINING TODO

#### Phase 6: E2E Testing & Validation ✓ (Dec 5, 2025)
- [x] Database migration for `enabled_tools` column
  - Created merge migration: `c9591c3d133a_merge_enabled_tools.py`
  - Successfully merged alembic heads and applied migration
  - Verified column exists with proper data backfill
- [x] Fixed version conflicts in pyproject.toml files (langchain-core ^0.3 vs ^1.0.0)
- [x] Fixed missing exports in vizu_agent_framework/__init__.py
- [x] Fixed auth.py in vendas_agent and support_agent (proper vizu_auth pattern)
- [x] Cleaned up pyproject.toml files to only include direct dependencies
- [x] Updated Dockerfiles with correct PYTHONPATH for all lib source directories
- [x] Added `vizu_llm_service` dependency to vendas_agent and support_agent
- [x] Fixed `get_model()` import (was `get_llm_client()`)
- [x] Fixed RedisCheckpointer serialization bug (HumanMessage not JSON serializable)
- [x] Fixed graph routing infinite loop (`route_from_respond` now ends after response)
- [x] Fixed `respond_node` fallback behavior when no LLM client
- [x] Updated Makefile with new test targets (test-vendas, test-support, test-agents, smoke-test)
- [x] Ran comprehensive smoke tests - ALL PASSING

**Smoke Test Results:**
```
🔥 Running comprehensive smoke test...

1️⃣ Checking services status...
vizu_atendente_core           Up
vizu_support_agent            Up
vizu_tool_pool_api            Up
vizu_vendas_agent             Up

2️⃣ Testing tool_pool_api MCP...
✅ tool_pool_api healthy

3️⃣ Testing atendente_core with RAG tool...
✅ RAG query works

4️⃣ Testing vendas_agent...
✅ Sales agent responding

5️⃣ Testing support_agent...
✅ Support agent responding

✅ Smoke test complete!
```

**Files Modified in Phase 6:**
- `libs/vizu_agent_framework/src/vizu_agent_framework/routing.py` - Fixed route_from_respond
- `libs/vizu_agent_framework/src/vizu_agent_framework/builder.py` - Fixed respond_node fallback
- `libs/vizu_agent_framework/src/vizu_agent_framework/checkpointer.py` - Fixed JSON serialization
- `services/vendas_agent/pyproject.toml` - Added vizu-llm-service dependency
- `services/support_agent/pyproject.toml` - Added vizu-llm-service dependency
- `services/vendas_agent/src/vendas_agent/core/service.py` - Fixed get_model() import
- `services/support_agent/src/support_agent/core/service.py` - Fixed get_model() import
- `services/vendas_agent/Dockerfile` - Added vizu_llm_service to PYTHONPATH
- `services/support_agent/Dockerfile` - Added vizu_llm_service to PYTHONPATH
- `Makefile` - Added test targets for new agents

### 🎯 NEXT STEPS

#### Phase 7: Production Rollout
- [ ] Enable `USE_NEW_FRAMEWORK=true` in staging environment
- [ ] Monitor Langfuse traces for regressions
- [ ] Run full E2E test suite on staging
- [ ] Canary deployment to production (10%)
- [ ] Full production rollout
- [ ] Remove legacy boolean tool flags (after 2 weeks)

#### Future Enhancements
- [ ] Create appointment_agent using same pattern
- [ ] Add more Docker MCP integrations (Jira, Notion, etc.)
- [ ] Implement tool usage analytics dashboard
- [ ] Add A/B testing for elicitation strategies

---

Markdown
# INSTRUCTIONS FOR IMPLEMENTING MULTI-AGENT ARCHITECTURE WITH DYNAMIC TOOL ALLOCATION

## PROJECT OBJECTIVE
Refactor vizu-mono from single-agent to scalable multi-agent architecture with:
1. Dynamic tool allocation (replace boolean flags with tool lists)
2.  Reusable agent framework reducing code by 95%
3. Docker MCP toolkit integration for composable tools
4. Support for unlimited agents (atendente, vendas, support, etc.)

## ARCHITECTURE OVERVIEW

### Current State
- Single atendente_core agent (1200+ lines)
- 3 hardcoded boolean tool flags (not scalable)
- Tools embedded in tool_pool_api (not composable)
- Monolithic code duplication for new agents

### Target State
- Multi-agent framework (shared library)
- Dynamic tool lists per client (JSON array in DB)
- Composable MCP servers (FastMCP + Docker MCP toolkit)
- New agents in 300 lines (95% code reuse)
- Tier-based tool access (BASIC/SME/ENTERPRISE)

---

## PHASE 1: DATABASE & DATA MODEL REFACTOR (4 days)

### 1. 1 Update vizu_models with Tool List Configuration

**Files to Modify:**
- `libs/vizu_models/src/vizu_models/cliente_vizu. py`
- `libs/vizu_models/src/vizu_models/agent_types.py`
- `libs/vizu_models/src/vizu_models/vizu_client_context.py`
- `libs/vizu_models/src/vizu_models/safe_client_context.py`

**Changes:**

```python
# libs/vizu_models/src/vizu_models/cliente_vizu.py

from typing import List
from enum import Enum

class TierCliente(str, Enum):
    BASIC = "BASIC"          # 1-2 tools
    SME = "SME"              # 3-5 tools
    ENTERPRISE = "ENTERPRISE" # All tools

class ClienteVizu(ClienteVizuBase, table=True):
    """Main client configuration model"""

    # REPLACE 3 BOOLEANS with 1 LIST
    enabled_tools: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="List of enabled tool names (e.g., ['executar_rag_cliente', 'executar_sql_agent'])"
    )

    # NEW: Tier-based tool access
    tier: TierCliente = Field(
        default=TierCliente. BASIC,
        sa_column=Column(String, server_default="BASIC"),
        description="Service tier determining baseline tool access"
    )

    # LEGACY (marked for deprecation in v1.1)
    # Keep for backward compatibility through migration period
    ferramenta_rag_habilitada: Optional[bool] = Field(
        default=None,
        sa_column=Column(Boolean, nullable=True),
        description="DEPRECATED: Use enabled_tools instead"
    )
    ferramenta_sql_habilitada: Optional[bool] = Field(
        default=None,
        sa_column=Column(Boolean, nullable=True),
        description="DEPRECATED: Use enabled_tools instead"
    )
    ferramenta_agendamento_habilitada: Optional[bool] = Field(
        default=None,
        sa_column=Column(Boolean, nullable=True),
        description="DEPRECATED: Use enabled_tools instead"
    )
Python
# libs/vizu_models/src/vizu_models/agent_types.py

class ToolInfo(BaseModel):
    """Information about an available tool"""
    name: str = Field(..., description="Technical tool name")
    description: Optional[str] = Field(None, description="User-friendly description")
    enabled: bool = Field(True, description="Whether enabled for this client")
    category: Optional[str] = Field(None, description="Category: rag, sql, scheduling, docker_mcp")
    requires_confirmation: bool = Field(False, description="Needs user confirmation before execution")
    tier_required: str = Field("BASIC", description="Minimum tier required (BASIC, SME, ENTERPRISE)")
    docker_mcp_integration: Optional[str] = Field(None, description="Docker MCP server name if applicable")

class ClientContextResponse(BaseModel):
    """Client context returned by /context endpoints"""
    nome_empresa: str
    tier: str = Field(... , description="Client tier: BASIC, SME, ENTERPRISE")
    enabled_tools: List[str] = Field(... , description="List of enabled tool names")
    available_tools: List[ToolInfo] = Field(..., description="Full tool metadata with status")
    horario_funcionamento: Optional[Dict[str, Any]] = None
    has_custom_prompt: bool = False
    collection_rag: Optional[str] = None

    # NEW: Docker MCP status
    docker_mcp_enabled: bool = Field(False, description="Whether Docker MCP containers are available")

class VizuClientContext(ClienteVizuBase):
    """Full client context with all configuration"""
    id: uuid.UUID
    api_key: str
    nome_empresa: str
    tier: TierCliente
    enabled_tools: List[str]  # REPLACE 3 BOOLEANS
    prompt_base: Optional[str]
    horario_funcionamento: Optional[Dict[str, Any]]
    collection_rag: Optional[str]
    credenciais: List[CredencialServicoExternoBase] = []
Checklist:

 Add enabled_tools: List[str] field to ClienteVizu model
 Add tier: TierCliente field with enum
 Keep deprecated boolean fields for backward compatibility (wrapped in deprecation warnings)
 Update ClientContextResponse to use enabled_tools list
 Update VizuClientContext to replace 3 booleans with 1 list
 Add ToolInfo. tier_required and docker_mcp_integration fields
 Add migration helper: migrate_boolean_tools_to_list(cliente_id)
 Add validation: validate_tool_access(enabled_tools, tier)
 Write unit tests for new ToolInfo validation
 Write tests for legacy boolean → list conversion
1.2 Create Database Migration
File: libs/vizu_db_connector/alembic/versions/20251205_migrate_tools_to_list.py

Python
"""Migration: Replace tool boolean flags with dynamic tool list."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy. dialects import postgresql

def upgrade():
    # Add new columns
    op.add_column(
        'cliente_vizu',
        sa.Column('enabled_tools', postgresql.JSON, nullable=False, server_default='[]')
    )
    op.add_column(
        'cliente_vizu',
        sa.Column('tier', sa.String(50), nullable=False, server_default='BASIC')
    )

    # Backfill: Convert existing boolean flags to tool lists
    op.execute("""
        UPDATE cliente_vizu SET enabled_tools =
        CASE
            WHEN ferramenta_rag_habilitada = true OR ferramenta_sql_habilitada = true
                 OR ferramenta_agendamento_habilitada = true
            THEN jsonb_agg(tool_name)
            ELSE '[]'::jsonb
        END
        FROM (
            SELECT 'executar_rag_cliente' as tool_name WHERE ferramenta_rag_habilitada = true
            UNION ALL
            SELECT 'executar_sql_agent' as tool_name WHERE ferramenta_sql_habilitada = true
            UNION ALL
            SELECT 'agendar_consulta' as tool_name WHERE ferramenta_agendamento_habilitada = true
        ) tools
    """)

    # Keep old columns for backward compatibility (deprecate in v1.1)
    # Do NOT drop columns yet

def downgrade():
    op.drop_column('cliente_vizu', 'enabled_tools')
    op.drop_column('cliente_vizu', 'tier')
Checklist:

 Create migration file with version stamp
 Test forward migration on staging DB
 Test backward migration (downgrade)
 Verify data integrity after migration (no tools lost)
 Document rollback procedure
 Add seed data for new tiers (BASIC, SME, ENTERPRISE)
 Update seed_clients.py to use enabled_tools list
Migration Verification:

SQL
-- Verify migration
SELECT id, tier, enabled_tools,
       ferramenta_rag_habilitada, ferramenta_sql_habilitada, ferramenta_agendamento_habilitada
FROM cliente_vizu LIMIT 5;

-- Expected: enabled_tools populated, old columns still present
PHASE 2: CREATE SHARED LIBRARIES (8 days)
2.1 Create vizu_tool_registry Library
Purpose: Centralized tool discovery and dynamic allocation

Files:

Code
libs/vizu_tool_registry/
├── src/vizu_tool_registry/
│   ├── __init__.py
│   ├── registry. py              # Tool registry + lookup
│   ├── tool_metadata.py         # Tool definition/metadata
│   ├── tier_validator.py        # Tier-based access control
│   ├── docker_mcp_bridge.py     # Docker MCP integration
│   └── exceptions.py
├── tests/
│   ├── test_registry.py
│   ├── test_tier_validator. py
│   └── test_docker_mcp_bridge.py
└── pyproject.toml
2.1.1 Tool Registry

Python
# libs/vizu_tool_registry/src/vizu_tool_registry/registry.py

from typing import Dict, List, Optional
from . tool_metadata import ToolMetadata

class ToolRegistry:
    """Central registry of all available tools"""

    # Built-in tools (always available to FastMCP)
    BUILTIN_TOOLS: Dict[str, ToolMetadata] = {
        "executar_rag_cliente": ToolMetadata(
            name="executar_rag_cliente",
            category="rag",
            description="Search knowledge base",
            tier_required="BASIC",
            requires_confirmation=False
        ),
        "executar_sql_agent": ToolMetadata(
            name="executar_sql_agent",
            category="sql",
            description="Query structured data",
            tier_required="SME",
            requires_confirmation=False
        ),
        "agendar_consulta": ToolMetadata(
            name="agendar_consulta",
            category="scheduling",
            description="Schedule an appointment",
            tier_required="SME",
            requires_confirmation=True
        ),
    }

    # Docker MCP tools (optional, lazy-loaded)
    DOCKER_MCP_TOOLS: Dict[str, ToolMetadata] = {
        "github_read": ToolMetadata(
            name="github_read",
            category="docker_mcp",
            description="Read GitHub repositories",
            tier_required="ENTERPRISE",
            docker_mcp_integration="github",
            requires_confirmation=False
        ),
        "slack_send": ToolMetadata(
            name="slack_send",
            category="docker_mcp",
            description="Send Slack messages",
            tier_required="ENTERPRISE",
            docker_mcp_integration="slack",
            requires_confirmation=False
        ),
        "stripe_charge": ToolMetadata(
            name="stripe_charge",
            category="docker_mcp",
            description="Process Stripe payment",
            tier_required="ENTERPRISE",
            docker_mcp_integration="stripe",
            requires_confirmation=True
        ),
    }

    @staticmethod
    def get_tool(tool_name: str) -> Optional[ToolMetadata]:
        """Get tool metadata by name"""
        return (
            ToolRegistry.BUILTIN_TOOLS.get(tool_name) or
            ToolRegistry.DOCKER_MCP_TOOLS.get(tool_name)
        )

    @staticmethod
    def get_available_tools(
        enabled_tools: List[str],
        tier: str,
        include_docker_mcp: bool = False
    ) -> List[ToolMetadata]:
        """
        Get tools available for a client based on enabled list and tier.

        Args:
            enabled_tools: List of tool names from client config
            tier: Client tier (BASIC, SME, ENTERPRISE)
            include_docker_mcp: Whether to check Docker MCP tools

        Returns:
            List of accessible ToolMetadata objects
        """
        available = []

        # Check builtin tools
        for tool_name in enabled_tools:
            tool = ToolRegistry. BUILTIN_TOOLS.get(tool_name)
            if tool and tool.tier_required <= tier:
                available.append(tool)

        # Optionally check Docker MCP tools
        if include_docker_mcp:
            for tool_name in enabled_tools:
                tool = ToolRegistry.DOCKER_MCP_TOOLS.get(tool_name)
                if tool and tool.tier_required <= tier:
                    available.append(tool)

        return available

    @staticmethod
    def validate_client_tools(
        enabled_tools: List[str],
        tier: str
    ) -> tuple[bool, List[str]]:
        """
        Validate that client's enabled_tools are compatible with tier.

        Returns: (is_valid, list_of_invalid_tools)
        """
        invalid = []
        for tool_name in enabled_tools:
            tool = ToolRegistry.get_tool(tool_name)
            if not tool:
                invalid.append(f"{tool_name} (not found)")
            elif tool. tier_required > tier:
                invalid.append(f"{tool_name} (requires {tool.tier_required}, client has {tier})")

        return (len(invalid) == 0, invalid)
2. 1.2 Tool Metadata Model

Python
# libs/vizu_tool_registry/src/vizu_tool_registry/tool_metadata.py

from dataclasses import dataclass
from typing import Optional
from enum import Enum

class TierLevel(str, Enum):
    BASIC = "BASIC"
    SME = "SME"
    ENTERPRISE = "ENTERPRISE"

@dataclass
class ToolMetadata:
    """Metadata for a tool"""
    name: str
    category: str  # rag, sql, scheduling, docker_mcp
    description: str
    tier_required: TierLevel = TierLevel.BASIC
    requires_confirmation: bool = False
    docker_mcp_integration: Optional[str] = None

    def __lt__(self, other):
        """For tier comparison"""
        tier_order = {"BASIC": 0, "SME": 1, "ENTERPRISE": 2}
        return tier_order[self.tier_required] < tier_order[other.tier_required]

    def __le__(self, tier: str):
        """Check if tool tier <= given tier"""
        tier_order = {"BASIC": 0, "SME": 1, "ENTERPRISE": 2}
        return tier_order[self.tier_required] <= tier_order[tier]
2.1.3 Tier Validator

Python
# libs/vizu_tool_registry/src/vizu_tool_registry/tier_validator.py

from typing import List
from .tool_metadata import ToolMetadata, TierLevel

class TierValidator:
    """Validates tool access based on client tier"""

    # Define what tools are available at each tier
    TIER_DEFINITIONS = {
        TierLevel. BASIC: {
            "included_tools": ["executar_rag_cliente"],
            "max_queries_per_day": 100,
            "description": "Basic RAG search only"
        },
        TierLevel.SME: {
            "included_tools": ["executar_rag_cliente", "executar_sql_agent", "agendar_consulta"],
            "max_queries_per_day": 1000,
            "description": "RAG, SQL, and scheduling"
        },
        TierLevel.ENTERPRISE: {
            "included_tools": ["executar_rag_cliente", "executar_sql_agent", "agendar_consulta"],
            "max_queries_per_day": None,  # Unlimited
            "description": "All tools + Docker MCP integrations"
        }
    }

    @staticmethod
    def get_default_tools_for_tier(tier: str) -> List[str]:
        """Get default tool list for a tier"""
        return TierValidator.TIER_DEFINITIONS[tier]["included_tools"]

    @staticmethod
    def can_access_tool(tool_name: str, tier: str) -> bool:
        """Check if tier has access to tool"""
        tier_def = TierValidator.TIER_DEFINITIONS. get(tier)
        if not tier_def:
            return False
        return tool_name in tier_def["included_tools"]

    @staticmethod
    def upgrade_tier_tools(enabled_tools: List[str], new_tier: str) -> List[str]:
        """
        When client tier is upgraded, automatically enable new tools.
        Preserves existing enabled tools.
        """
        default_for_tier = TierValidator.get_default_tools_for_tier(new_tier)
        return list(set(enabled_tools) | set(default_for_tier))
2.1.4 Docker MCP Bridge

Python
# libs/vizu_tool_registry/src/vizu_tool_registry/docker_mcp_bridge.py

import logging
from typing import Optional, List, Dict, Any
from . tool_metadata import ToolMetadata

logger = logging.getLogger(__name__)

class DockerMCPBridge:
    """
    Bridge between FastMCP and Docker MCP toolkit integrations.

    Enables composition of:
    - Built-in Vizu tools (RAG, SQL)
    - Docker MCP verified servers (GitHub, Slack, Stripe, etc.)
    """

    def __init__(self, docker_host: str = "localhost"):
        self.docker_host = docker_host
        self.connected_integrations: Dict[str, bool] = {}

    async def discover_docker_mcp_servers(self) -> Dict[str, ToolMetadata]:
        """
        Discover available Docker MCP servers and map to tools.

        Requires: Docker Desktop with MCP toolkit enabled

        Returns:
            Dict mapping tool_name -> ToolMetadata for Docker MCP tools
        """
        try:
            # Query Docker API for running MCP containers
            docker_mcp_tools = {}

            # Example: If GitHub MCP is running, expose github_read tool
            if await self._is_docker_mcp_running("github"):
                docker_mcp_tools["github_read"] = ToolMetadata(
                    name="github_read",
                    category="docker_mcp",
                    description="Read GitHub repositories via MCP",
                    docker_mcp_integration="github"
                )

            # Similar for Slack, Stripe, etc.
            integrations = ["github", "slack", "stripe", "postgres", "jira"]
            for integration in integrations:
                if await self._is_docker_mcp_running(integration):
                    docker_mcp_tools[f"{integration}_tool"] = await self._create_docker_mcp_tool(integration)

            logger.info(f"Discovered {len(docker_mcp_tools)} Docker MCP integrations")
            return docker_mcp_tools

        except Exception as e:
            logger. warning(f"Docker MCP discovery failed: {e}")
            return {}

    async def _is_docker_mcp_running(self, integration_name: str) -> bool:
        """Check if a Docker MCP integration container is running"""
        # Implementation: Query Docker daemon for running container
        # docker ps | grep mcp-{integration_name}
        pass

    async def _create_docker_mcp_tool(self, integration: str) -> ToolMetadata:
        """Create ToolMetadata for a Docker MCP integration"""
        # Map integration name to tool metadata
        pass

    @staticmethod
    def build_docker_mcp_connection_url(integration: str) -> str:
        """Build connection URL for Docker MCP integration"""
        return f"docker://mcp-{integration}:latest"
Checklist:

 Create vizu_tool_registry/src/vizu_tool_registry/registry.py with ToolRegistry class
 Create tool_metadata.py with ToolMetadata dataclass
 Implement TierValidator with tier definitions
 Implement DockerMCPBridge for Docker MCP discovery
 Add unit tests for ToolRegistry. get_available_tools()
 Add unit tests for TierValidator.can_access_tool()
 Add integration tests with Docker daemon (optional)
 Write docstrings for all public methods
 Add type hints throughout
 Create pyproject.toml with dependencies
 Add README with usage examples
2.2 Create vizu_mcp_commons Library (Extract & Share)
Purpose: Common MCP utilities used by all services

Files:

Code
libs/vizu_mcp_commons/
├── src/vizu_mcp_commons/
│   ├── __init__. py
│   ├── auth.py              # JWT/token validation
│   ├── dependencies.py      # Shared dependency injection
│   ├── exceptions.py        # Common MCP exceptions
│   ├── middleware.py        # Auth middleware
│   ├── tool_executor.py     # Execute tools with context injection
│   └── resource_loader.py   # Load resources dynamically
├── tests/
└── pyproject.toml
Key Classes:

Python
# libs/vizu_mcp_commons/src/vizu_mcp_commons/auth.py

import jwt
from typing import Optional
from uuid import UUID

class TokenValidator:
    """Validate and extract context from JWT tokens"""

    @staticmethod
    def validate_token(token: str, secret: str) -> dict:
        """Validate JWT and extract claims"""
        try:
            payload = jwt.decode(token, secret, algorithms=["HS256"])
            return payload
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Token validation failed: {e}")

    @staticmethod
    def extract_cliente_id(token: str, secret: str) -> UUID:
        """Extract cliente_id from token"""
        payload = TokenValidator. validate_token(token, secret)
        return UUID(payload. get("sub"))
Python
# libs/vizu_mcp_commons/src/vizu_mcp_commons/dependencies.py

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from vizu_db_connector.database import SessionLocal
from vizu_context_service import ContextService

@asynccontextmanager
async def get_context_service() -> AsyncGenerator[ContextService, None]:
    """Dependency: Get ContextService with DB session"""
    db_session = SessionLocal()
    try:
        context_service = ContextService(db_session=db_session)
        yield context_service
    finally:
        db_session.close()
Checklist:

 Extract auth logic from tool_pool_api/dependencies.py
 Create TokenValidator class
 Create shared exception classes
 Create auth middleware for FastAPI
 Add tool executor with context injection
 Add resource loader for dynamic loading
 Write unit tests for TokenValidator
 Write integration tests with DB
2.3 Create vizu_prompt_management Library
Purpose: Centralized prompt management (extract from tool_pool_api)

Files:

Code
libs/vizu_prompt_management/
├── src/vizu_prompt_management/
│   ├── __init__.py
│   ├── loader.py            # Load prompts from DB
│   ├── manager. py           # Prompt versioning
│   ├── templates. py         # Common prompt templates
│   ├── mcp_builder.py       # Build MCP resources
│   └── variables.py         # Variable substitution
├── tests/
└── pyproject.toml
Key Classes:

Python
# libs/vizu_prompt_management/src/vizu_prompt_management/loader.py

from typing import Optional
from uuid import UUID
from vizu_db_connector.database import SessionLocal
from vizu_models import PromptTemplate

class PromptLoader:
    """Load prompts from database"""

    @staticmethod
    async def load_prompt(
        name: str,
        version: Optional[int] = None,
        cliente_id: Optional[UUID] = None
    ) -> Optional[PromptTemplate]:
        """
        Load prompt template by name and version.
        Prioritizes client-specific prompts over global.
        """
        db = SessionLocal()
        try:
            query = db.query(PromptTemplate). filter(PromptTemplate.name == name)

            # Search for client-specific first, then global
            if cliente_id:
                template = query.filter(PromptTemplate. cliente_vizu_id == cliente_id)
                if not template.first():
                    query = db.query(PromptTemplate). filter(
                        PromptTemplate.name == name,
                        PromptTemplate.cliente_vizu_id == None
                    )

            if version:
                template = query.filter(PromptTemplate.version == version)
            else:
                # Get latest version
                template = query. order_by(PromptTemplate. version.desc())

            return template.first()
        finally:
            db.close()

    @staticmethod
    async def render_prompt(
        template: PromptTemplate,
        context: dict
    ) -> str:
        """Render prompt with variable substitution"""
        content = template.content
        for key, value in context.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))
        return content
Checklist:

 Create PromptLoader class
 Implement version management
 Add variable substitution
 Create MCP resource builder
 Migrate prompts from tool_pool_api/prompts. py
 Add caching layer (Redis)
 Write unit tests for rendering
 Write integration tests with DB
2. 4 Create vizu_elicitation_service Library
Purpose: Reusable elicitation strategies (extract from tool_pool_api)

Files:

Code
libs/vizu_elicitation_service/
├── src/vizu_elicitation_service/
│   ├── __init__.py
│   ├── core/
│   │   ├── types.py          # Elicitation types
│   │   ├── executor.py       # Execute elicitation steps
│   │   ├── validator.py      # Validate responses
│   │   └── context. py        # Build context from DB
│   ├── strategies/
│   │   ├── __init__.py
│   │   ├── ask_name.py
│   │   ├── ask_service.py
│   │   ├── ask_time.py
│   │   └── ask_product.py
│   └── tests/
├── pyproject.toml
Key Implementation:

Python
# libs/vizu_elicitation_service/src/vizu_elicitation_service/strategies/ask_name.py

from typing import Optional
from vizu_models import ElicitationType, ElicitationResponse
from vizu_llm_service. client import LLMClient

class AskNameStrategy:
    """Reusable strategy for eliciting customer name"""

    @staticmethod
    async def execute(
        client_context,
        llm_client: LLMClient,
        confidence_threshold: float = 0. 8
    ) -> ElicitationResponse:
        """Execute name elicitation"""

        # Get prompt template
        prompt = PromptLoader.load("elicitation/ask_name", version=1)

        # Generate question
        question = await llm_client.generate(
            prompt.content,
            max_tokens=200
        )

        # Validate response quality
        is_valid = ElicitationValidator.validate_name_question(question)

        return ElicitationResponse(
            type=ElicitationType.NAME,
            question=question,
            is_valid=is_valid,
            confidence=0.95
        )
Checklist:

 Create ElicitationType enum with all strategies
 Implement AskNameStrategy
 Implement AskServiceStrategy
 Implement AskTimeStrategy
 Create validator pipeline
 Add confidence scoring
 Write integration tests with LLM
 Add documentation
2.5 Create vizu_agent_framework Library
Purpose: Reusable LangGraph agent patterns for all agents

Files:

Code
libs/vizu_agent_framework/
├── src/vizu_agent_framework/
│   ├── __init__.py
│   ├── core/
│   │   ├── agent_builder.py   # AgentBuilder factory
│   │   ├── state. py           # AgentState baseclass
│   │   ├── nodes.py           # Reusable graph nodes
│   │   ├── edges.py           # Routing logic
│   │   └── config.py          # AgentConfig
│   ├── mcp/
│   │   ├── client.py          # MCP client wrapper
│   │   └── tool_executor.py   # Execute MCP tools
│   ├── observability/
│   │   └── langfuse_integration.py
│   └── tests/
├── pyproject.toml
Key Classes:

Python
# libs/vizu_agent_framework/src/vizu_agent_framework/core/agent_builder.py

from typing import Optional
from langgraph.graph import StateGraph
from dataclasses import dataclass

@dataclass
class AgentConfig:
    """Configuration for agent creation"""
    name: str
    role: str
    elicitation_strategy: str = "support_triage"
    enabled_tools: List[str] = field(default_factory=list)
    max_turns: int = 20
    use_langfuse: bool = True
    model: str = "ollama:llama2"

class AgentBuilder:
    """Factory for creating agents with shared patterns"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.graph = StateGraph(AgentState)

    def build(self) -> Runnable:
        """Build and compile the agent graph"""

        # 1. Add reusable nodes
        self.graph.add_node("init", self._node_init)
        self.graph.add_node("elicit", self._node_elicit)
        self.graph.add_node("execute_tool", self._node_execute_tool)
        self.graph.add_node("respond", self._node_respond)
        self.graph.add_node("end", self._node_end)

        # 2. Add edges/routing
        self.graph.add_edge("init", "elicit")
        self.graph.add_conditional_edges(
            "elicit",
            self._route_from_elicit,
            {"needs_tool": "execute_tool", "ready_to_respond": "respond"}
        )
        self.graph.add_edge("execute_tool", "respond")
        self.graph.add_edge("respond", "end")

        # 3.  Compile and return
        return self. graph.compile()

    async def _node_init(self, state: AgentState):
        """Initialize agent state"""
        return {"initialized": True}

    async def _node_elicit(self, state: AgentState):
        """Elicit information from user"""
        # Use configured strategy
        strategy_class = self._get_elicitation_strategy()
        result = await strategy_class.execute(state["context"], state["llm_client"])
        return {"elicitation": result}

    async def _node_execute_tool(self, state: AgentState):
        """Execute an MCP tool"""
        tool_name = state. get("tool_to_execute")
        result = await self. mcp_client.call_tool(
            tool_name,
            state. get("tool_args", {})
        )
        return {"tool_result": result}

    async def _node_respond(self, state: AgentState):
        """Generate response"""
        # Use LLM to generate response
        response = await state["llm_client"].generate(
            messages=state["messages"],
            system_prompt=state["system_prompt"]
        )
        return {"response": response}

    async def _node_end(self, state: AgentState):
        """End conversation"""
        return {"ended": True}

    def _route_from_elicit(self, state: AgentState):
        """Route based on elicitation result"""
        if state. get("elicitation", {}). get("needs_tool"):
            return "needs_tool"
        return "ready_to_respond"

    def _get_elicitation_strategy(self):
        """Get elicitation strategy class by name"""
        # Map strategy name to class
        pass
Checklist:

 Create AgentState base class with common fields
 Implement AgentBuilder factory
 Create reusable nodes (init, elicit, execute_tool, respond, end)
 Implement routing logic (edges)
 Add configuration system (AgentConfig)
 Integrate MCP client wrapper
 Add Langfuse observability hooks
 Write comprehensive tests
 Document node lifecycle
PHASE 3: REFACTOR EXISTING SERVICES (5 days)
3.1 Simplify tool_pool_api
File Changes:

services/tool_pool_api/src/tool_pool_api/server/resources.py - Use vizu_tool_registry
services/tool_pool_api/src/tool_pool_api/server/prompts.py - Remove, use vizu_prompt_management
services/tool_pool_api/src/tool_pool_api/server/mcp_server.py - Keep, minimal changes
services/tool_pool_api/pyproject.toml - Remove prompt dependencies
Key Changes:

Python
# services/tool_pool_api/src/tool_pool_api/server/resources. py (UPDATED)

from vizu_tool_registry import ToolRegistry, TierValidator
from vizu_prompt_management import PromptLoader

async def _get_client_config(cliente_id: Optional[str] = None) -> str:
    """Build config resource with dynamic tools"""

    context = await _resolve_client_context(cliente_id)

    # NEW: Use ToolRegistry for dynamic tool list
    available_tools = ToolRegistry.get_available_tools(
        enabled_tools=context.enabled_tools,
        tier=context.tier,
        include_docker_mcp=True
    )

    # Build response
    result = f"# Configuration - {context.nome_empresa}\n\n"
    result += f"## Tools Enabled ({len(available_tools)})\n"
    for tool in available_tools:
        status = "✅" if tool.enabled else "❌"
        result += f"{status} {tool.name} ({tool.category})\n"

    return result
Checklist:

 Import ToolRegistry and TierValidator
 Update config resource to use dynamic tools
 Remove prompts.py entirely
 Update resources.py to use PromptLoader
 Remove prompt registration from mcp_server.py
 Update pyproject.toml (remove prompt deps, add registry deps)
 Update tests to use mock ToolRegistry
 Test dynamic tool loading
 Test tier-based access control
3.2 Refactor atendente_core
File Changes:

services/atendente_core/src/atendente_core/core/agent.py - Use AgentBuilder
services/atendente_core/src/atendente_core/core/state.py - Remove, use framework
services/atendente_core/src/atendente_core/core/workflow.py - Remove, use AgentBuilder
services/atendente_core/src/atendente_core/api/routes.py - Keep, minimal changes
Before:

Python
# services/atendente_core/src/atendente_core/core/workflow.py (OLD - REMOVE)
# ~600 lines of graph definition

class AttendenteState(BaseModel):
    messages: List[BaseMessage]
    session_id: str
    cliente_id: UUID
    # ... 30+ fields

def build_atendente_graph():
    # ~300 lines of node definitions and edge routing
    pass
After:

Python
# services/atendente_core/src/atendente_core/core/agent. py (NEW - SIMPLIFIED)

from vizu_agent_framework import AgentBuilder, AgentConfig
from vizu_tool_registry import ToolRegistry

class AtendenteCoreAgent:
    """Atendente agent using shared framework"""

    def __init__(self, cliente_context: VizuClientContext):
        # Get tools from registry based on enabled_tools
        available_tools = ToolRegistry.get_available_tools(
            enabled_tools=cliente_context.enabled_tools,
            tier=cliente_context.tier
        )

        # Build agent using framework
        config = AgentConfig(
            name="atendente_core",
            role="Customer Support Agent",
            elicitation_strategy="support_triage",
            enabled_tools=[t.name for t in available_tools],
            max_turns=20,
            use_langfuse=True
        )

        self.agent = AgentBuilder(config).build()

    async def process_message(
        self,
        message: str,
        session_id: str
    ) -> ChatResponse:
        """Process user message"""
        return await self.agent.invoke({
            "messages": [message],
            "session_id": session_id
        })
Checklist:

 Remove ~600 lines of workflow definition
 Create minimal agent. py using AgentBuilder
 Update imports to use framework
 Update /chat endpoint to use new agent
 Remove state. py and workflow.py files
 Update pyproject. toml to add framework dependency
 Run existing tests (should pass with no changes)
 Add new tests for tool registry integration
 Verify Langfuse integration still works
 Test dynamic tool loading in agent
PHASE 4: BUILD NEW AGENTS (4 days)
4. 1 Create vendas_agent
Structure:

Code
services/vendas_agent/
├── src/vendas_agent/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app + agent setup
│   ├── api/
│   │   ├── schemas.py          # vendas-specific types
│   │   └── routes.py           # /chat, /status endpoints
│   ├── core/
│   │   ├── agent.py            # Agent instantiation
│   │   ├── config.py           # Vendas-specific config
│   │   └── dependencies.py
│   └── config/
│       └── settings.py
├── tests/
├── pyproject.toml
└── Dockerfile
Implementation:

Python
# services/vendas_agent/src/vendas_agent/core/agent.py

from vizu_agent_framework import AgentBuilder, AgentConfig
from vizu_tool_registry import ToolRegistry

class VendasAgent:
    """Sales agent for B2C order processing"""

    def __init__(self, cliente_context: VizuClientContext):
        # Get enabled tools for this client
        available_tools = ToolRegistry.get_available_tools(
            enabled_tools=cliente_context.enabled_tools,
            tier=cliente_context.tier
        )

        # Sales-specific configuration
        config = AgentConfig(
            name="vendas_agent",
            role="Sales Representative",
            elicitation_strategy="sales_pipeline",  # DIFFERENT from support_triage
            enabled_tools=[t.name for t in available_tools],
            max_turns=15,  # DIFFERENT from atendente (20)
            use_langfuse=True
        )

        self.agent = AgentBuilder(config).build()

    async def process_message(self, message: str, session_id: str) -> ChatResponse:
        return await self.agent.invoke({"messages": [message], "session_id": session_id})
Python
# services/vendas_agent/src/vendas_agent/api/schemas.py

from vizu_models import AgentChatRequest, AgentChatResponse

class VendasChatRequest(AgentChatRequest):
    """Vendas-specific request"""
    customer_id: Optional[UUID] = None
    product_category: Optional[str] = None

class VendasChatResponse(AgentChatResponse):
    """Vendas-specific response"""
    suggested_products: Optional[List[str]] = None
    discount_available: bool = False
Python
# services/vendas_agent/src/vendas_agent/main.py

from fastapi import FastAPI, Depends, HTTPException
from . core.agent import VendasAgent
from .api import schemas, routes

app = FastAPI(title="Vizu Vendas Agent")

# Mount routes
app.include_router(routes.router)

@app.on_event("startup")
async def startup():
    logger.info("Vendas Agent starting")

@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "vendas"}
Checklist:

 Create vendas_agent directory structure
 Implement VendasAgent class (inherit 95% from framework)
 Create vendas-specific schemas
 Implement /chat endpoint
 Create Dockerfile (reuse pattern from atendente_core)
 Write unit tests (mock framework, test routing)
 Write integration tests (with ToolRegistry)
 Add to docker-compose.yml
 Test tier-based tool access
 Test dynamic tool allocation
4.2 Create support_agent
Same pattern as vendas_agent, with different:

elicitation_strategy="issue_classification"
enabled_tools=["executar_rag_cliente", "executar_sql_agent"]
Ticket tracking schemas
Checklist:

 Create support_agent using same pattern as vendas_agent
 Customize elicitation strategy
 Add ticket management schemas
 Test with different tier configurations
 Add to docker-compose.yml
4.3 Create appointment_agent (Optional)
Pattern: Same as other agents, focused on scheduling

Checklist:

 Create appointment_agent
 Integrate with agendar_consulta tool
 Add calendar availability checking
 Test confirmation workflow
PHASE 5: DOCKER MCP INTEGRATION (3 days)
5. 1 Docker MCP Discovery & Registration
File: services/tool_pool_api/src/tool_pool_api/server/docker_mcp_adapter.py

Python
"""
Adapter for Docker MCP toolkit integrations.

Allows tool_pool_api to discover and proxy Docker MCP containers
as additional tools/resources.

Supported integrations:
- GitHub (read repos, issues, PRs)
- Slack (send messages, read channels)
- Stripe (process payments)
- PostgreSQL (query external DBs)
- Jira (create tickets, update issues)
- And 100+ more from Docker MCP catalog
"""

import logging
from typing import Dict, Optional, List
from vizu_tool_registry import ToolRegistry, ToolMetadata, DockerMCPBridge

logger = logging.getLogger(__name__)

class DockerMCPAdapter:
    """Adapter for Docker MCP integrations"""

    def __init__(self):
        self. bridge = DockerMCPBridge()
        self.registered_integrations: Dict[str, bool] = {}

    async def discover_and_register(self, mcp_server):
        """Discover Docker MCP servers and register as tools"""

        # 1. Discover available Docker MCP containers
        docker_tools = await self.bridge.discover_docker_mcp_servers()

        logger.info(f"Discovered {len(docker_tools)} Docker MCP integrations")

        # 2. For each Docker MCP tool, register with FastMCP
        for tool_name, tool_metadata in docker_tools.items():
            try:
                await self._register_docker_mcp_tool(mcp_server, tool_metadata)
                self.registered_integrations[tool_name] = True
                logger.info(f"Registered Docker MCP tool: {tool_name}")
            except Exception as e:
                logger.error(f"Failed to register {tool_name}: {e}")
                self.registered_integrations[tool_name] = False

    async def _register_docker_mcp_tool(self, mcp_server, tool_metadata: ToolMetadata):
        """Register a single Docker MCP tool with FastMCP"""

        # Create wrapper that calls Docker MCP container
        async def docker_mcp_wrapper(**kwargs):
            # Forward request to Docker MCP container
            result = await self.bridge.call_docker_mcp_tool(
                tool_metadata.docker_mcp_integration,
                tool_metadata.name,
                kwargs
            )
            return result

        # Register with MCP server
        mcp_server.tool(
            name=tool_metadata.name,
            description=tool_metadata.description
        )(docker_mcp_wrapper)
Checklist:

 Create DockerMCPAdapter class
 Implement Docker daemon discovery
 Test with GitHub MCP (read repos)
 Test with Slack MCP (send messages)
 Test with Stripe MCP (payments)
 Add error handling and logging
 Document Docker Desktop setup requirements
 Add configuration for enabling/disabling integrations
 Write integration tests with Docker
5.2 Update docker-compose.yml
Add Docker MCP Services (Optional):

YAML
version: '3.8'
services:
  # Existing services...

  tool_pool_api:
    image: vizu/tool-pool-api:latest
    environment:
      DOCKER_MCP_ENABLED: "true"
      MCP_INTEGRATIONS: "github,slack,stripe"

  # Optional: Docker MCP containers (if not using Docker Desktop)
  mcp-github:
    image: docker.io/modelcontextprotocol/mcp-github:latest
    environment:
      GITHUB_TOKEN: ${GITHUB_TOKEN}
    ports:
      - "3001:3000"

  mcp-slack:
    image: docker.io/modelcontextprotocol/mcp-slack:latest
    environment:
      SLACK_BOT_TOKEN: ${SLACK_BOT_TOKEN}
    ports:
      - "3002:3000"

  mcp-stripe:
    image: docker.io/modelcontextprotocol/mcp-stripe:latest
    environment:
      STRIPE_API_KEY: ${STRIPE_API_KEY}
    ports:
      - "3003:3000"
Checklist:

 Add DOCKER_MCP_ENABLED env var
 Configure which integrations to enable
 Document Docker Desktop MCP setup
 Test with docker-compose up
 Add health checks for MCP containers
 Document authentication per integration
PHASE 6: MIGRATION & ROLLOUT (3 days)
6. 1 Data Migration Script
File: scripts/migrate_tools_to_list.py

Python
"""
Script to migrate existing client tool configuration from booleans to list.

Usage:
    python scripts/migrate_tools_to_list.py --dry-run
    python scripts/migrate_tools_to_list.py --commit
"""

import argparse
from uuid import UUID
from sqlmodel import Session, select
from vizu_db_connector. database import engine
from vizu_models import ClienteVizu
from vizu_tool_registry import TierValidator

def migrate_client(session: Session, client: ClienteVizu, dry_run: bool = True):
    """Migrate a single client"""

    # Determine enabled tools from old booleans
    tools = []
    if client.ferramenta_rag_habilitada:
        tools.append("executar_rag_cliente")
    if client.ferramenta_sql_habilitada:
        tools.append("executar_sql_agent")
    if client.ferramenta_agendamento_habilitada:
        tools.append("agendar_consulta")

    # Validate against tier
    # If tier is BASIC but client has SQL tools, upgrade to SME
    if client.tier == "BASIC" and "executar_sql_agent" in tools:
        print(f"  Upgrading {client.nome_empresa} from BASIC to SME")
        client.tier = "SME"

    # Set new field
    client.enabled_tools = tools

    if not dry_run:
        session. add(client)

    return tools

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()

    if args.commit:
        args.dry_run = False

    with Session(engine) as session:
        clients = session.exec(select(ClienteVizu)).all()

        for client in clients:
            print(f"Client: {client.nome_empresa}")
            tools = migrate_client(session, client, args.dry_run)
            print(f"  Tools: {tools}")
            print(f"  Tier: {client.tier}")

        if not args.dry_run:
            session.commit()
            print("\n✅ Migration completed")
        else:
            print("\n⚠️ Dry-run completed.  Use --commit to apply changes")

if __name__ == "__main__":
    main()
Checklist:

 Create migration script
 Test on staging DB (dry-run)
 Verify no data loss
 Document rollback procedure
 Test rollback on staging
 Run on production (with backup)
 Monitor for errors post-migration
6.2 Feature Flags (Gradual Rollout)
File: services/tool_pool_api/src/tool_pool_api/config/feature_flags.py

Python
"""
Feature flags for gradual rollout of new systems.

Allows running old and new systems in parallel.
"""

from enum import Enum

class FeatureFlag(Enum):
    USE_NEW_TOOL_REGISTRY = "use_new_tool_registry"  # Route to new registry
    USE_AGENT_FRAMEWORK = "use_agent_framework"      # Use AgentBuilder
    USE_DOCKER_MCP = "use_docker_mcp"                # Enable Docker MCP integrations
    ENABLE_TOOL_LIST_CONFIG = "enable_tool_list_config"  # Use enabled_tools field

class FeatureFlagManager:
    """Manage feature flags per client"""

    @staticmethod
    def is_enabled(flag: FeatureFlag, cliente_id: UUID) -> bool:
        """Check if feature is enabled for client"""
        # Load from DB or environment
        # Can override per client for canary rollout
        pass

# Usage:
# if FeatureFlagManager.is_enabled(FeatureFlag.USE_NEW_TOOL_REGISTRY, client_id):
#     tools = ToolRegistry.get_available_tools(...)
# else:
#     tools = load_tools_old_way(...)
Checklist:

 Create FeatureFlag enum
 Implement FeatureFlagManager
 Add feature flag checks at decision points
 Document rollout strategy
 Plan canary deployment (10% → 50% → 100%)
TESTING STRATEGY
Unit Tests (All Phases)
vizu_tool_registry tests:

Python
# tests/test_registry.py

def test_get_available_tools_basic_tier():
    """Clients on BASIC tier only get basic tools"""
    available = ToolRegistry.get_available_tools(
        enabled_tools=["executar_rag_cliente", "executar_sql_agent"],
        tier="BASIC"
    )
    assert len(available) == 1
    assert available[0].name == "executar_rag_cliente"

def test_upgrade_tier_adds_tools():
    """Upgrading tier automatically enables new tools"""
    tools = TierValidator.upgrade_tier_tools(
        enabled_tools=["executar_rag_cliente"],
        new_tier="SME"
    )
    assert "executar_sql_agent" in tools
    assert "agendar_consulta" in tools

def test_validate_client_tools_invalid_tier():
    """Validation fails if client has tools beyond their tier"""
    is_valid, invalid_tools = ToolRegistry.validate_client_tools(
        enabled_tools=["executar_sql_agent"],
        tier="BASIC"
    )
    assert not is_valid
    assert len(invalid_tools) > 0
Checklist - Unit Tests:

 ToolRegistry tests (20+)
 TierValidator tests (15+)
 DockerMCPBridge tests (10+)
 PromptLoader tests (15+)
 AgentBuilder tests (20+)
 TokenValidator tests (10+)
 ElicitationStrategy tests (15+)
Total: 115+ unit tests

Integration Tests (Phases 3-5)
tool_pool_api integration tests:

Python
# services/tool_pool_api/tests/integration/test_dynamic_tools.py

@pytest.mark.asyncio
async def test_client_receives_only_enabled_tools():
    """Client MCP request only returns enabled tools"""
    # Create client with enabled_tools=["rag"]
    # Request tools list
    # Assert only RAG tool returned (not SQL)

@pytest.mark.asyncio
async def test_tier_based_tool_access():
    """Tier-based tool access is enforced"""
    # Create BASIC tier client
    # Try to access SQL tool
    # Assert 403 Forbidden

@pytest.mark.asyncio
async def test_docker_mcp_tool_routing():
    """Docker MCP tools are discovered and routed"""
    # Enable Docker MCP integration
    # Verify GitHub tool registered
    # Call GitHub tool
    # Assert result from Docker container
Checklist - Integration Tests:

 Dynamic tool loading (5 tests)
 Tier-based access control (5 tests)
 Docker MCP discovery & routing (5 tests)
 End-to-end agent + tools (5 tests)
 Migration script validation (3 tests)
 Feature flag rollout (3 tests)
Total: 26+ integration tests

End-to-End Tests (Phase 4-6)
New agents with framework:

Python
# services/vendas_agent/tests/e2e/test_vendas_agent_e2e.py

@pytest. mark.asyncio
async def test_vendas_agent_with_dynamic_tools():
    """Vendas agent receives only enabled tools"""
    # Create SME client with tools
    # Start vendas agent
    # Send chat message
    # Assert agent uses only enabled tools

@pytest.mark.asyncio
async def test_multi_agent_tool_isolation():
    """Different agents get different tool subsets"""
    # atendente_core: rag + sql
    # vendas_agent: rag only
    # Send same query to both
    # Assert different tools used
Checklist - E2E Tests:

 Vendas agent basic flow (2 tests)
 Support agent basic flow (2 tests)
 Multi-agent tool isolation (2 tests)
 Cross-agent context sharing (2 tests)
 Docker MCP tool integration (2 tests)
Total: 10+ E2E tests

DEPLOYMENT CHECKLIST
Pre-Deployment (on staging)
 All 115+ unit tests pass
 All 26+ integration tests pass
 All 10+ E2E tests pass
 Database