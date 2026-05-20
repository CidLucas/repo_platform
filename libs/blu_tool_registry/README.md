# blu_tool_registry

Centralized tool catalog and tier-based access control for the Blu agent system.

## Overview

Every tool that agents can call is registered here with its `ToolMetadata`. The registry
drives two things:

1. **Tool discovery** — agents ask for the tools they need by name; the registry resolves
   metadata, validates tier access, and returns filtered lists.
2. **Tier enforcement** — tools declare a minimum tier; clients below that tier cannot use
   the tool, even if it is listed in their `enabled_tools`.

## Installation

```bash
poetry add blu-tool-registry
```

## Key Concepts

### TierLevel

Ordered access levels (lowest → highest):

```
FREE(0) → BASIC(1) → SME(2) → PREMIUM(3) → ENTERPRISE(4) → ADMIN(99)
```

### ToolCategory

```
RAG · SQL · SCHEDULING · DOCKER_MCP · PUBLIC · GOOGLE · CUSTOM
```

### ToolMetadata

```python
@dataclass
class ToolMetadata:
    name: str                           # MCP tool name (must match tool_pool_api)
    display_name: str
    description: str
    category: ToolCategory
    min_tier: TierLevel
    requires_confirmation: bool = False # Gates execution behind user approval
    tags: list[str] = field(default_factory=list)
```

## Usage

```python
from blu_tool_registry import ToolRegistry, TierLevel

# Get tools available for a client
available = ToolRegistry.get_available_tools(
    enabled_tools=["executar_rag_cliente", "execute_sql"],
    tier=TierLevel.SME,
)

# Validate client configuration
is_valid, errors = ToolRegistry.validate_client_tools(
    enabled_tools=["execute_sql"],
    tier=TierLevel.BASIC,
)
# is_valid=False, errors=["execute_sql requires SME, client has BASIC"]
```

## Tier Access Summary

| Tier       | Typical Tools Available                                            |
| ---------- | ------------------------------------------------------------------ |
| FREE       | `ferramenta_publica_de_teste`                                      |
| BASIC      | RAG, config setup, data catalog, routines, procurement, monitoring |
| SME        | + SQL, CSV analytics, document OCR, WhatsApp RFQ dispatch          |
| PREMIUM    | SME + premium integrations                                         |
| ENTERPRISE | All tools + Docker MCP                                             |
| ADMIN      | Unrestricted                                                       |

## Tool Catalog

### RAG & Knowledge

| Tool                          | Min Tier |
| ----------------------------- | -------- |
| `executar_rag_cliente`        | BASIC    |
| `extract_document_with_ocr`   | SME      |
| `summarize_document_sections` | SME      |
| `extract_structured_data`     | SME      |
| `write_summary_to_kb`         | SME      |

### SQL & Analytics

| Tool                 | Min Tier |
| -------------------- | -------- |
| `execute_sql`        | SME      |
| `executar_sql_agent` | SME      |
| `execute_csv_query`  | SME      |
| `list_csv_datasets`  | SME      |
| `peek_csv_columns`   | BASIC    |

### Data Catalog & Context

| Tool                      | Min Tier |
| ------------------------- | -------- |
| `register_transaction`    | BASIC    |
| `list_data_sources`       | BASIC    |
| `query_data_catalog`      | BASIC    |
| `suggest_column_mapping`  | BASIC    |
| `update_schema_mapping`   | BASIC    |
| `get_knowledge_status`    | BASIC    |
| `update_context_document` | BASIC    |

### Routines

| Tool                            | Min Tier |
| ------------------------------- | -------- |
| `listar_rotinas_catalogo`       | BASIC    |
| `listar_rotinas_personalizadas` | BASIC    |
| `criar_rotina_personalizada`    | BASIC    |
| `enviar_rotina_para_aprovacao`  | BASIC    |

### Procurement / RFQ

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
| `import_buying_list_from_sheets` | BASIC    |                           |
| `export_po_to_sheets`            | BASIC    |                           |
| `add_supplier`                   | BASIC    |                           |
| `dispatch_rfq_whatsapp`          | SME      |                           |
| `parse_supplier_reply`           | SME      |                           |

### Monitoring

| Tool               | Min Tier |
| ------------------ | -------- |
| `monitor_feature`  | BASIC    |
| `monitor_keywords` | BASIC    |
| `monitor_company`  | BASIC    |

### Setup & Config

| Tool                        | Min Tier |
| --------------------------- | -------- |
| `check_config_completeness` | BASIC    |
| `save_config_field`         | BASIC    |
| `get_agent_requirements`    | BASIC    |
| `finalize_config`           | BASIC    |

### Diagnostic

| Tool                          | Min Tier |
| ----------------------------- | -------- |
| `ferramenta_publica_de_teste` | FREE     |

## Registering a New Tool

Add a `ToolMetadata` entry to `registry.py`:

```python
ToolRegistry.register(ToolMetadata(
    name="my_new_tool",
    display_name="My New Tool",
    description="Does X for the client.",
    category=ToolCategory.CUSTOM,
    min_tier=TierLevel.BASIC,
    requires_confirmation=False,
    tags=["my-domain"],
))
```

The `name` must match exactly what `tool_pool_api` exposes over MCP.

Then add the tool to the relevant `AgentTypeConfig.enabled_tools` list in
`libs/blu_agent_framework/src/blu_agent_framework/registry.py` and/or to a
`SkillDefinition.required_tools` in `skills.py`.

See `docs/agent_system_map.md` for the full tool-to-agent mapping.
