"""
blu_tool_registry.registry
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Central registry of all available tools.

This module provides the ToolRegistry class which maintains a catalog of
all builtin and Docker MCP tools, with methods for querying and validating
tool access based on client configuration.
"""

import logging

from .tool_metadata import TierLevel, ToolCategory, ToolMetadata

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central registry of all available tools.

    Provides methods for:
    - Querying available tools based on client configuration
    - Validating tool access permissions
    - Discovering Docker MCP tools (when enabled)

    Usage:
        # Get tools for a client
        tools = ToolRegistry.get_available_tools(
            enabled_tools=["search_knowledge_base"],
            tier="BASIC"
        )

        # Validate configuration
        is_valid, errors = ToolRegistry.validate_client_tools(
            enabled_tools=["executar_sql_agent"],
            tier="BASIC"
        )
    """

    # =========================================================================
    # BUILTIN TOOLS - Always available in FastMCP
    # =========================================================================
    BUILTIN_TOOLS: dict[str, ToolMetadata] = {
        "search_knowledge_base": ToolMetadata(
            name="search_knowledge_base",
            category=ToolCategory.RAG,
            description="Busca informações na base de conhecimento do cliente (RAG)",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["rag", "search", "knowledge-base"],
        ),
        "execute_sql": ToolMetadata(
            name="execute_sql",
            category=ToolCategory.SQL,
            description=(
                "Executes a pre-generated SQL query on analytics database. "
                "Use when supervisor LLM generates SQL directly. "
                "Parameters: sql (the query). client_id is auto-injected."
            ),
            tier_required=TierLevel.SME,
            requires_confirmation=False,
            tags=["sql", "database", "analytics", "direct-sql"],
        ),
        "ferramenta_publica_de_teste": ToolMetadata(
            name="ferramenta_publica_de_teste",
            category=ToolCategory.PUBLIC,
            description="Ferramenta de diagnóstico interno (sempre disponível)",
            tier_required=TierLevel.FREE,
            requires_confirmation=False,
            tags=["test", "diagnostic", "public"],
        ),
        "route_to_specialist": ToolMetadata(
            name="route_to_specialist",
            category=ToolCategory.PUBLIC,
            description=(
                "Signal the service layer to delegate the current request to a domain "
                "specialist agent. Used exclusively by the frontdesk agent."
            ),
            tier_required=TierLevel.FREE,
            requires_confirmation=False,
            tags=["routing", "handoff", "specialist", "frontdesk"],
        ),
        "monitor_feature": ToolMetadata(
            name="monitor_feature",
            category=ToolCategory.PUBLIC,
            description=(
                "Detecta novas páginas de produtos em destaque dentro do domínio informado "
                "usando o serviço de monitoramento web (crawl4ai + embeddings)."
            ),
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["monitoring", "web", "feature-pages"],
        ),
        "monitor_keywords": ToolMetadata(
            name="monitor_keywords",
            category=ToolCategory.PUBLIC,
            description=(
                "Busca conteúdos atuais em um domínio que mencionam palavras-chave, tópicos ou reviews."
            ),
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["monitoring", "web", "keywords"],
        ),
        "monitor_company": ToolMetadata(
            name="monitor_company",
            category=ToolCategory.PUBLIC,
            description=(
                "Rastreia menções da marca/empresa em diversos domínios usando buscas semânticas web."
            ),
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["monitoring", "web", "brand"],
        ),
        "extract_document_with_ocr": ToolMetadata(
            name="extract_document_with_ocr",
            category=ToolCategory.RAG,
            description=(
                "Extract text, tables, and structured data from uploaded documents "
                "using configurable OCR (language, table accuracy mode). "
                "Returns markdown + tables as structured JSON."
            ),
            tier_required=TierLevel.SME,
            requires_confirmation=False,
            tags=["ocr", "extraction", "tables", "documents"],
        ),
        "summarize_document_sections": ToolMetadata(
            name="summarize_document_sections",
            category=ToolCategory.RAG,
            description=(
                "Summarize text sections extracted from a document using LLM. "
                "Use after extract_document_with_ocr."
            ),
            tier_required=TierLevel.SME,
            requires_confirmation=False,
            tags=["ocr", "summarization", "documents"],
        ),
        "extract_structured_data": ToolMetadata(
            name="extract_structured_data",
            category=ToolCategory.RAG,
            description=(
                "Extract structured data from uploaded documents into a JSON table "
                "using LLM-powered field extraction."
            ),
            tier_required=TierLevel.SME,
            requires_confirmation=False,
            tags=["extraction", "structured-data", "documents"],
        ),
        "compile_time_series": ToolMetadata(
            name="compile_time_series",
            category=ToolCategory.RAG,
            description=(
                "Compile structured data records into a sorted time series with statistics."
            ),
            tier_required=TierLevel.SME,
            requires_confirmation=False,
            tags=["time-series", "analytics", "documents"],
        ),
        "write_summary_to_kb": ToolMetadata(
            name="write_summary_to_kb",
            category=ToolCategory.RAG,
            description=(
                "Save analysis summary or extracted data to the knowledge base."
            ),
            tier_required=TierLevel.SME,
            requires_confirmation=False,
            tags=["knowledge-base", "persistence", "documents"],
        ),
        "check_config_completeness": ToolMetadata(
            name="check_config_completeness",
            category=ToolCategory.PUBLIC,
            description="Check which configuration fields are still missing.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["config", "setup", "helper"],
        ),
        "save_config_field": ToolMetadata(
            name="save_config_field",
            category=ToolCategory.PUBLIC,
            description="Save a single configuration field value.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["config", "setup", "helper"],
        ),
        "get_agent_requirements": ToolMetadata(
            name="get_agent_requirements",
            category=ToolCategory.PUBLIC,
            description="Get the list of required configuration fields for an agent type.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["config", "setup", "helper"],
        ),
        "finalize_config": ToolMetadata(
            name="finalize_config",
            category=ToolCategory.PUBLIC,
            description="Finalize and validate the agent configuration.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["config", "setup", "helper"],
        ),
        "peek_csv_columns": ToolMetadata(
            name="peek_csv_columns",
            category=ToolCategory.PUBLIC,
            description="Preview column names and sample data from a CSV dataset.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["csv", "preview", "helper"],
        ),
        # RFQ / Procurement tools
        "parse_buying_list": ToolMetadata(
            name="parse_buying_list",
            category=ToolCategory.CUSTOM,
            description="Parse a buying list from text or uploaded file into structured items.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["rfq", "procurement", "parsing"],
        ),
        "validate_buying_list": ToolMetadata(
            name="validate_buying_list",
            category=ToolCategory.CUSTOM,
            description="Validate parsed buying list for completeness and correctness.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["rfq", "procurement", "validation"],
        ),
        "list_suppliers": ToolMetadata(
            name="list_suppliers",
            category=ToolCategory.CUSTOM,
            description="List available suppliers for the current tenant.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["rfq", "procurement", "suppliers"],
        ),
        "dispatch_rfq": ToolMetadata(
            name="dispatch_rfq",
            category=ToolCategory.CUSTOM,
            description="Send an RFQ to a specific supplier.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["rfq", "procurement", "dispatch"],
        ),
        "check_rfq_responses": ToolMetadata(
            name="check_rfq_responses",
            category=ToolCategory.CUSTOM,
            description="Check the status of all RFQ requests for the current session.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["rfq", "procurement", "status"],
        ),
        "submit_mock_response": ToolMetadata(
            name="submit_mock_response",
            category=ToolCategory.CUSTOM,
            description="Submit a mock supplier response for testing (Phase 1).",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["rfq", "procurement", "mock"],
        ),
        "optimize_allocation": ToolMetadata(
            name="optimize_allocation",
            category=ToolCategory.CUSTOM,
            description="Optimize item allocation across suppliers based on quotes.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["rfq", "procurement", "optimization"],
        ),
        "generate_po_report": ToolMetadata(
            name="generate_po_report",
            category=ToolCategory.CUSTOM,
            description="Generate a Markdown procurement report from optimization results.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["rfq", "procurement", "report"],
        ),
        "create_purchase_order": ToolMetadata(
            name="create_purchase_order",
            category=ToolCategory.CUSTOM,
            description="Create a draft Purchase Order for a supplier.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=True,
            tags=["rfq", "procurement", "po"],
        ),
        "approve_purchase_order": ToolMetadata(
            name="approve_purchase_order",
            category=ToolCategory.CUSTOM,
            description="Approve a draft Purchase Order.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=True,
            tags=["rfq", "procurement", "po", "approval"],
        ),
        # Phase 2: Negotiation — suggest_counter_offer remains active
        "suggest_counter_offer": ToolMetadata(
            name="suggest_counter_offer",
            category=ToolCategory.CUSTOM,
            description="Suggest counter-offer prices based on historical data.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["rfq", "procurement", "negotiation"],
        ),
        # NOTE: dispatch_rfq_whatsapp and parse_supplier_reply removed (D5).
        # Replaced by send_rfq_via_channel and parse_incoming_reply in communication_module.
        # Phase 3: Google Sheets Integration & Supplier Management
        "import_buying_list_from_sheets": ToolMetadata(
            name="import_buying_list_from_sheets",
            category=ToolCategory.CUSTOM,
            description="Import buying list from Google Sheets spreadsheet.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["rfq", "procurement", "google", "sheets", "import"],
        ),
        "export_po_to_sheets": ToolMetadata(
            name="export_po_to_sheets",
            category=ToolCategory.CUSTOM,
            description="Export Purchase Orders to Google Sheets spreadsheet.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["rfq", "procurement", "google", "sheets", "export"],
        ),
        "add_supplier": ToolMetadata(
            name="add_supplier",
            category=ToolCategory.CUSTOM,
            description="Add a new supplier to the tenant's roster.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["rfq", "procurement", "suppliers", "crud"],
        ),
        "update_supplier": ToolMetadata(
            name="update_supplier",
            category=ToolCategory.CUSTOM,
            description="Update an existing supplier's information.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["rfq", "procurement", "suppliers", "crud"],
        ),
        "remove_supplier": ToolMetadata(
            name="remove_supplier",
            category=ToolCategory.CUSTOM,
            description="Deactivate a supplier from the roster (soft-delete).",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["rfq", "procurement", "suppliers", "crud"],
        ),
        "register_transaction": ToolMetadata(
            name="register_transaction",
            category=ToolCategory.CUSTOM,
            description=(
                "Register a business transaction (venda, compra, despesa) into analytics_v2. "
                "Routes to fato_transacoes or fato_compras based on tipo_transacao. "
                "Resolves dim surrogate keys by name lookup."
            ),
            tier_required=TierLevel.BASIC,
            requires_confirmation=True,
            tags=["context", "transactions", "analytics"],
        ),
        "list_data_sources": ToolMetadata(
            name="list_data_sources",
            category=ToolCategory.CUSTOM,
            description=(
                "Return row counts for analytics_v2 fact/dim tables and the 10 most "
                "recent ingestion jobs. Used to orient schema-mapping conversations."
            ),
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["context", "analytics", "data-sources"],
        ),
        "query_data_catalog": ToolMetadata(
            name="query_data_catalog",
            category=ToolCategory.CUSTOM,
            description=(
                "Query client_data_sources: registered files, column-mapping health "
                "(mapped/unmapped/needs_review), detected entity context, sync status, "
                "and ingestion quality. Read-only — no confirmation needed."
            ),
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["context", "schema-mapping", "data-catalog"],
        ),
        "suggest_column_mapping": ToolMetadata(
            name="suggest_column_mapping",
            category=ToolCategory.CUSTOM,
            description=(
                "Call the match-columns engine to suggest canonical field mappings for "
                "a registered data source. Returns matched, unmatched, needs_review, "
                "confidence_scores, and detected_context. Read-only."
            ),
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["context", "schema-mapping", "match-columns"],
        ),
        "update_schema_mapping": ToolMetadata(
            name="update_schema_mapping",
            category=ToolCategory.CUSTOM,
            description=(
                "Persist a user-confirmed column mapping to client_data_sources. "
                "Sets column_mapping, reviewed_at, unmapped_columns, and user_column_changes."
            ),
            tier_required=TierLevel.BASIC,
            requires_confirmation=True,
            tags=["context", "schema-mapping", "write"],
        ),
        "get_knowledge_status": ToolMetadata(
            name="get_knowledge_status",
            category=ToolCategory.CUSTOM,
            description=(
                "Return the knowledge completeness status for this client across all "
                "document types. Filters by agent_slug to surface only relevant types "
                "and coverage thresholds. Read-only — no confirmation needed."
            ),
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["context", "knowledge", "completeness"],
        ),
        "update_context_document": ToolMetadata(
            name="update_context_document",
            category=ToolCategory.CUSTOM,
            description=(
                "Upsert a client_knowledge_documents row, merging field_coverage and metadata. "
                "Internal bookkeeping — no user confirmation needed."
            ),
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["context", "knowledge", "write"],
        ),
        "fiscal_prepare_nfe_data": ToolMetadata(
            name="fiscal_prepare_nfe_data",
            category=ToolCategory.CUSTOM,
            description="Prepare and validate data for NF-e or NFS-e invoice issuance. Validates mandatory fields without emitting.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["fiscal", "nfe", "nfse", "invoice"],
        ),
        "fiscal_integration_status": ToolMetadata(
            name="fiscal_integration_status",
            category=ToolCategory.CUSTOM,
            description="Return current SEFAZ fiscal integration status (NF-e/NFS-e).",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["fiscal", "nfe", "nfse", "status"],
        ),

        # ── Shared Memory (Fase 4: TTL / retention) ───────────────────────────
        "shared_memory_read": ToolMetadata(
            name="shared_memory_read",
            category=ToolCategory.CUSTOM,
            description=(
                "[Shared Memory] Read a single fact from shared business memory "
                "by its composite key (client_id, entity_type, entity_name, key). "
                "Valid entity types: skill | client | contact | supplier | user | snapshot. "
                "Returns the full record including value, metadata, version, and timestamps. "
                "Supports optional ttl_tier for retention policy classification."
            ),
            tier_required=TierLevel.SME,
            requires_confirmation=False,
            parameters={
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "description": "Entity type (skill | client | contact | supplier | user | snapshot)",
                    },
                    "entity_name": {
                        "type": "string",
                        "description": "Entity name (case-insensitive, normalized to lowercase)",
                    },
                    "key": {
                        "type": "string",
                        "description": "Fact key (e.g. 'tom_amigavel', 'preferencia_horario')",
                    },
                    "ttl_tier": {
                        "type": "string",
                        "enum": ["curated", "migration", "specialist", "memory_agent_hi", "memory_agent_lo"],
                        "description": (
                            "Tier de retencao TTL. Define politica de expiracao do fato. "
                            "curated = sem expiracao, migration = 90d, specialist = 30d (default), "
                            "memory_agent_hi = 14d, memory_agent_lo = 7d. "
                            "Default varia por source."
                        ),
                    },
                },
                "required": ["entity_type", "entity_name", "key"],
            },
            tags=["shared-memory", "memory", "read", "retention", "ttl"],
        ),
        "shared_memory_write": ToolMetadata(
            name="shared_memory_write",
            category=ToolCategory.CUSTOM,
            description=(
                "[Shared Memory] Write a new fact into shared business memory. "
                "By default this is a strict INSERT — it fails if the composite key "
                "(client_id, entity_type, entity_name, key) already exists. "
                "Set supersede=true to overwrite. "
                "The value parameter maps directly to the jsonb column. "
                "Supports optional ttl_tier for retention policy classification."
            ),
            tier_required=TierLevel.SME,
            requires_confirmation=False,
            parameters={
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "description": "Entity type (skill | client | contact | supplier | user | snapshot)",
                    },
                    "entity_name": {
                        "type": "string",
                        "description": "Entity name (case-insensitive, normalized to lowercase)",
                    },
                    "key": {
                        "type": "string",
                        "description": "Fact key (e.g. 'tom_amigavel', 'preferencia_horario')",
                    },
                    "value": {
                        "type": "object",
                        "description": "The fact value (dict — maps to 'value' jsonb column)",
                    },
                    "category": {
                        "type": "string",
                        "description": "Semantic category for filtering/routing",
                    },
                    "source": {
                        "type": "string",
                        "description": "Provenance — 'manual' | 'memory_agent' | 'specialist' | 'migration' | 'system'",
                        "default": "manual",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence score (0.0-1.0, default 1.0)",
                        "default": 1.0,
                    },
                    "supersede": {
                        "type": "boolean",
                        "description": "If true, upsert to overwrite existing entry. Default false.",
                        "default": False,
                    },
                    "ttl_tier": {
                        "type": "string",
                        "enum": ["curated", "migration", "specialist", "memory_agent_hi", "memory_agent_lo"],
                        "description": (
                            "Tier de retencao TTL. Define politica de expiracao do fato. "
                            "curated = sem expiracao, migration = 90d, specialist = 30d (default), "
                            "memory_agent_hi = 14d, memory_agent_lo = 7d. "
                            "Default varia por source."
                        ),
                    },
                },
                "required": ["entity_type", "entity_name", "key", "value"],
            },
            tags=["shared-memory", "memory", "write", "insert", "retention", "ttl"],
        ),
        "shared_memory_upsert": ToolMetadata(
            name="shared_memory_upsert",
            category=ToolCategory.CUSTOM,
            description=(
                "[Shared Memory] Insert or update a fact in shared business memory. "
                "Uses upsert semantics: creates a new row if the composite key "
                "(client_id, entity_type, entity_name, key) doesn't exist, "
                "or updates the existing row (incrementing version). "
                "body maps to the 'value' column (the fact content); "
                "frontmatter maps to the 'metadata' column (provenance). "
                "Supports optional ttl_tier for retention policy classification."
            ),
            tier_required=TierLevel.SME,
            requires_confirmation=False,
            parameters={
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "description": "Entity type (skill | client | contact | supplier | user | snapshot)",
                    },
                    "entity_name": {
                        "type": "string",
                        "description": "Entity name (case-insensitive, normalized to lowercase)",
                    },
                    "key": {
                        "type": "string",
                        "description": "Fact key (e.g. 'tom_amigavel', 'preferencia_horario')",
                    },
                    "body": {
                        "type": "object",
                        "description": "The fact value (dict — maps to 'value' column)",
                    },
                    "frontmatter": {
                        "type": "object",
                        "description": "Optional metadata dict (maps to 'metadata' column)",
                    },
                    "source": {
                        "type": "string",
                        "description": "Provenance — 'manual' | 'memory_agent' | 'specialist' | 'migration' | 'system'",
                        "default": "manual",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence score (0.0-1.0, default 1.0)",
                        "default": 1.0,
                    },
                    "ttl_tier": {
                        "type": "string",
                        "enum": ["curated", "migration", "specialist", "memory_agent_hi", "memory_agent_lo"],
                        "description": (
                            "Tier de retencao TTL. Define politica de expiracao do fato. "
                            "curated = sem expiracao, migration = 90d, specialist = 30d (default), "
                            "memory_agent_hi = 14d, memory_agent_lo = 7d. "
                            "Default varia por source."
                        ),
                    },
                },
                "required": ["entity_type", "entity_name", "key", "body"],
            },
            tags=["shared-memory", "memory", "upsert", "retention", "ttl"],
        ),
        "shared_memory_list": ToolMetadata(
            name="shared_memory_list",
            category=ToolCategory.CUSTOM,
            description=(
                "[Shared Memory] List all entities that have business-memory "
                "entries for the current client. Optionally filter by entity_type "
                "(skill | client | contact | supplier | user). "
                "Returns a summary breakdown and the full entity list with "
                "key-counts and last-updated timestamps. "
                "Use this to discover what entities exist before calling "
                "shared_memory_read for a specific one."
            ),
            tier_required=TierLevel.SME,
            requires_confirmation=False,
            parameters={
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "description": "Optional filter: 'skill', 'client', 'contact', 'supplier', or 'user'. When omitted all entity types are returned.",
                    },
                },
            },
            tags=["shared-memory", "memory", "list", "entities"],
        ),
        "shared_memory_link": ToolMetadata(
            name="shared_memory_link",
            category=ToolCategory.CUSTOM,
            description=(
                "[Shared Memory] Create a semantic link between two entities. "
                "Links represent relationships like 'contact Joao works_for supplier Distribuidora X'. "
                "link_type is free-form: works_for, applies_to, prefers, reports_to, depends_on, etc. "
                "Valid entity types: skill | client | contact | supplier | user."
            ),
            tier_required=TierLevel.SME,
            requires_confirmation=False,
            parameters={
                "type": "object",
                "properties": {
                    "source_entity_type": {
                        "type": "string",
                        "description": "Entity type of the source (skill | client | contact | supplier | user)",
                    },
                    "source_entity_name": {
                        "type": "string",
                        "description": "Name of the source entity (case-insensitive, normalized to lowercase)",
                    },
                    "target_entity_type": {
                        "type": "string",
                        "description": "Entity type of the target (skill | client | contact | supplier | user)",
                    },
                    "target_entity_name": {
                        "type": "string",
                        "description": "Name of the target entity (case-insensitive)",
                    },
                    "link_type": {
                        "type": "string",
                        "description": "Relationship label — e.g. 'works_for', 'applies_to', 'prefers'",
                    },
                    "source": {
                        "type": "string",
                        "description": "Origin of the link — 'manual' | 'memory_agent' | 'specialist' | 'migration' | 'system'",
                        "default": "manual",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence score (0.0-1.0, default 1.0)",
                        "default": 1.0,
                    },
                    "metadata": {
                        "type": "string",
                        "description": "Optional JSON string with extra link metadata",
                    },
                },
                "required": ["source_entity_type", "source_entity_name", "target_entity_type", "target_entity_name", "link_type"],
            },
            tags=["shared-memory", "memory", "link", "graph", "semantic"],
        ),
        "shared_memory_unlink": ToolMetadata(
            name="shared_memory_unlink",
            category=ToolCategory.CUSTOM,
            description=(
                "[Shared Memory] Remove a semantic link between entities by its id. "
                "Use shared_memory_get_links to find the link id first."
            ),
            tier_required=TierLevel.SME,
            requires_confirmation=False,
            parameters={
                "type": "object",
                "properties": {
                    "link_id": {
                        "type": "string",
                        "description": "UUID of the link to remove (from shared_memory_get_links)",
                    },
                },
                "required": ["link_id"],
            },
            tags=["shared-memory", "memory", "unlink", "graph"],
        ),
        "shared_memory_get_links": ToolMetadata(
            name="shared_memory_get_links",
            category=ToolCategory.CUSTOM,
            description=(
                "[Shared Memory] Query semantic links by entity and/or link_type. "
                "Returns outgoing links (where entity is the source), incoming links "
                "(where entity is the target), or both. "
                "Filter by entity_type, entity_name, and/or link_type."
            ),
            tier_required=TierLevel.SME,
            requires_confirmation=False,
            parameters={
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "description": "Optional — filter links involving this entity type",
                    },
                    "entity_name": {
                        "type": "string",
                        "description": "Optional — filter links involving this entity name",
                    },
                    "link_type": {
                        "type": "string",
                        "description": "Optional — filter links of this type (e.g. 'works_for')",
                    },
                    "direction": {
                        "type": "string",
                        "enum": ["outgoing", "incoming", "both"],
                        "description": "'outgoing' | 'incoming' | 'both' (default)",
                        "default": "both",
                    },
                },
            },
            tags=["shared-memory", "memory", "links", "graph", "query"],
        ),
    }

    # =========================================================================
    # GOOGLE INTEGRATION TOOLS
    # =========================================================================
    GOOGLE_TOOLS: dict[str, ToolMetadata] = {
        "write_to_sheet": ToolMetadata(
            name="write_to_sheet",
            category=ToolCategory.GOOGLE,
            description="Write data to a Google Sheets spreadsheet.",
            tier_required=TierLevel.PREMIUM,
            requires_confirmation=False,
            tags=["google", "sheets", "write"],
        ),
        "read_emails": ToolMetadata(
            name="read_emails",
            category=ToolCategory.GOOGLE,
            description="Read emails from the connected Google account.",
            tier_required=TierLevel.PREMIUM,
            requires_confirmation=False,
            tags=["google", "gmail", "email"],
        ),
        "query_calendar": ToolMetadata(
            name="query_calendar",
            category=ToolCategory.GOOGLE,
            description="Query events from Google Calendar.",
            tier_required=TierLevel.PREMIUM,
            requires_confirmation=False,
            tags=["google", "calendar", "events"],
        ),
        "list_google_accounts": ToolMetadata(
            name="list_google_accounts",
            category=ToolCategory.GOOGLE,
            description="List connected Google accounts for the current client.",
            tier_required=TierLevel.PREMIUM,
            requires_confirmation=False,
            tags=["google", "accounts", "oauth"],
        ),
        "list_spreadsheets": ToolMetadata(
            name="list_spreadsheets",
            category=ToolCategory.GOOGLE,
            description="List available Google Sheets spreadsheets.",
            tier_required=TierLevel.PREMIUM,
            requires_confirmation=False,
            tags=["google", "sheets", "list"],
        ),
        "export_to_sheet": ToolMetadata(
            name="export_to_sheet",
            category=ToolCategory.GOOGLE,
            description="Export data to a Google Sheets spreadsheet.",
            tier_required=TierLevel.PREMIUM,
            requires_confirmation=False,
            tags=["google", "sheets", "export"],
        ),
        "create_spreadsheet_with_data": ToolMetadata(
            name="create_spreadsheet_with_data",
            category=ToolCategory.GOOGLE,
            description="Create a new Google Sheets spreadsheet with initial data.",
            tier_required=TierLevel.PREMIUM,
            requires_confirmation=False,
            tags=["google", "sheets", "create"],
        ),
        "google_docs_create": ToolMetadata(
            name="google_docs_create",
            category=ToolCategory.GOOGLE,
            description="Create a new Google Docs document.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["google", "docs", "create", "document", "report"],
        ),
        "google_docs_read": ToolMetadata(
            name="google_docs_read",
            category=ToolCategory.GOOGLE,
            description="Read content from a Google Docs document.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["google", "docs", "read", "document"],
        ),
        "google_docs_write": ToolMetadata(
            name="google_docs_write",
            category=ToolCategory.GOOGLE,
            description="Write or append content to a Google Docs document.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["google", "docs", "write", "document", "report"],
        ),
        "google_docs_list": ToolMetadata(
            name="google_docs_list",
            category=ToolCategory.GOOGLE,
            description="List Google Docs documents accessible to the client.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["google", "docs", "list", "document"],
        ),
        "generate_chart_html": ToolMetadata(
            name="generate_chart_html",
            category=ToolCategory.PUBLIC,
            description=(
                "Generate a self-contained HTML file with an interactive Chart.js chart "
                "(bar, line, pie, doughnut). Returns the file path."
            ),
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["chart", "graph", "visualization", "html", "analytics", "report"],
        ),
        "import_spreadsheet_schedule": ToolMetadata(
            name="import_spreadsheet_schedule",
            category=ToolCategory.GOOGLE,
            description=(
                "Import Google Sheets data and map columns to schedule schema "
                "(tarefa, data_inicio, data_fim, responsavel, status, notas)."
            ),
            tier_required=TierLevel.PREMIUM,
            requires_confirmation=False,
            tags=["google", "sheets", "import", "schedule", "cronograma"],
        ),
        "google_calendar_write": ToolMetadata(
            name="google_calendar_write",
            category=ToolCategory.GOOGLE,
            description="Create or update events in Google Calendar.",
            tier_required=TierLevel.PREMIUM,
            requires_confirmation=False,
            tags=["google", "calendar", "write", "events"],
        ),

        # ── D5: Communication module (v3) ─────────────────────────────────────
        # Absorbs dispatch_rfq_whatsapp + parse_supplier_reply (rfq_whatsapp_module).
        "send_message": ToolMetadata(
            name="send_message",
            category=ToolCategory.CUSTOM,
            description=(
                "Draft and send a message to a client contact (CRM reply, NPS follow-up, "
                "payment reminder). Used by crm agent."
            ),
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["communication", "crm", "message", "whatsapp"],
        ),
        "send_rfq_via_channel": ToolMetadata(
            name="send_rfq_via_channel",
            category=ToolCategory.CUSTOM,
            description=(
                "Send an RFQ to a supplier via the configured channel (WhatsApp, email). "
                "Replaces dispatch_rfq_whatsapp (D5)."
            ),
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["communication", "rfq", "procurement", "whatsapp"],
        ),
        "parse_business_reply": ToolMetadata(
            name="parse_business_reply",
            category=ToolCategory.CUSTOM,
            description=(
                "Parse a free-text inbound message into structured data. "
                "context_type param: rfq | nps | payment. "
                "Replaces parse_supplier_reply (D5)."
            ),
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["communication", "parsing", "rfq", "nps", "whatsapp"],
        ),
        # ── Platform / Routines ───────────────────────────────────────────────
        "create_routine": ToolMetadata(
            name="create_routine",
            category=ToolCategory.CUSTOM,
            description="Create a new automated business routine from natural language.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["platform", "routines", "automation"],
        ),
        "list_routine_catalog": ToolMetadata(
            name="list_routine_catalog",
            category=ToolCategory.CUSTOM,
            description="List available routine templates from the catalog.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["platform", "routines", "catalog"],
        ),
        "list_custom_routines": ToolMetadata(
            name="list_custom_routines",
            category=ToolCategory.CUSTOM,
            description="List the tenant's custom/active routines.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["platform", "routines", "custom"],
        ),
        "create_custom_routine": ToolMetadata(
            name="create_custom_routine",
            category=ToolCategory.CUSTOM,
            description="Create a personalized routine for the tenant.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["platform", "routines", "custom"],
        ),
        "submit_routine_for_approval": ToolMetadata(
            name="submit_routine_for_approval",
            category=ToolCategory.CUSTOM,
            description="Submit a routine draft for human approval (HITL).",
            tier_required=TierLevel.BASIC,
            requires_confirmation=True,
            tags=["platform", "routines", "approval", "hitl"],
        ),
        "activate_catalog_routine": ToolMetadata(
            name="activate_catalog_routine",
            category=ToolCategory.CUSTOM,
            description="Activate a catalog routine for the tenant.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["platform", "routines", "catalog"],
        ),
        "define_goal": ToolMetadata(
            name="define_goal",
            category=ToolCategory.CUSTOM,
            description="Define or update a business goal for the tenant.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["platform", "goals", "meta"],
        ),
        "list_goals": ToolMetadata(
            name="list_goals",
            category=ToolCategory.CUSTOM,
            description="List the tenant's current business goals.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["platform", "goals", "meta"],
        ),
        # ── Monday.com ────────────────────────────────────────────────────────
        # TODO(D9): consolidate monday_query/monday_write/monday_brief → 3 semantic tools.
        "monday_query": ToolMetadata(
            name="monday_query",
            category=ToolCategory.CUSTOM,
            description="Query Monday.com boards, items, status, and summaries.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["monday", "project-management", "read"],
        ),
        "monday_write": ToolMetadata(
            name="monday_write",
            category=ToolCategory.CUSTOM,
            description="Create or update Monday.com items and statuses.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["monday", "project-management", "write"],
        ),
        "monday_brief": ToolMetadata(
            name="monday_brief",
            category=ToolCategory.CUSTOM,
            description="Generate a project summary brief from Monday.com board data.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["monday", "project-management", "summary"],
        ),
        # ── WhatsApp (client module) ──────────────────────────────────────────
        "send_whatsapp_message": ToolMetadata(
            name="send_whatsapp_message",
            category=ToolCategory.CUSTOM,
            description="Send a WhatsApp message to a single client contact.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["whatsapp", "communication", "crm", "message"],
        ),
        "send_whatsapp_batch": ToolMetadata(
            name="send_whatsapp_batch",
            category=ToolCategory.CUSTOM,
            description="Send batch WhatsApp messages to a list of client contacts (CRM campaigns).",
            tier_required=TierLevel.BASIC,
            requires_confirmation=True,
            tags=["whatsapp", "communication", "crm", "batch"],
        ),
        "check_whatsapp_replies": ToolMetadata(
            name="check_whatsapp_replies",
            category=ToolCategory.CUSTOM,
            description="Check and retrieve incoming WhatsApp replies from clients or suppliers.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["whatsapp", "communication", "inbound", "replies"],
        ),
        "send_email": ToolMetadata(
            name="send_email",
            category=ToolCategory.CUSTOM,
            description="Send an email message to a client or supplier.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["email", "communication", "outreach"],
        ),
        # ── Slack (real implementation — slack_module.py) ─────────────────────
        # NOTE: distinct from Docker MCP slack_read/slack_send stubs.
        "slack_list_channels": ToolMetadata(
            name="slack_list_channels",
            category=ToolCategory.CUSTOM,
            description="List Slack channels accessible to the tenant.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["slack", "messaging", "list"],
        ),
        "slack_read_channel": ToolMetadata(
            name="slack_read_channel",
            category=ToolCategory.CUSTOM,
            description="Read recent messages from a Slack channel.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["slack", "messaging", "read"],
        ),
        "slack_summarize_channel": ToolMetadata(
            name="slack_summarize_channel",
            category=ToolCategory.CUSTOM,
            description="Generate an LLM summary of recent messages in a Slack channel.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["slack", "messaging", "summary"],
        ),
        "slack_post_message": ToolMetadata(
            name="slack_post_message",
            category=ToolCategory.CUSTOM,
            description="Post a message to a Slack channel.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["slack", "messaging", "write"],
        ),
        "slack_get_unread": ToolMetadata(
            name="slack_get_unread",
            category=ToolCategory.CUSTOM,
            description="Get unread Slack messages for the tenant.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["slack", "messaging", "unread"],
        ),
        # ── Notion ────────────────────────────────────────────────────────────
        "notion_search": ToolMetadata(
            name="notion_search",
            category=ToolCategory.CUSTOM,
            description="Search pages and databases in Notion.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["notion", "search"],
        ),
        "notion_read_page": ToolMetadata(
            name="notion_read_page",
            category=ToolCategory.CUSTOM,
            description="Read content from a Notion page.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["notion", "read", "page"],
        ),
        "notion_query_database": ToolMetadata(
            name="notion_query_database",
            category=ToolCategory.CUSTOM,
            description="Query a Notion database with filters and sorts.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["notion", "database", "query"],
        ),
        "notion_list_databases": ToolMetadata(
            name="notion_list_databases",
            category=ToolCategory.CUSTOM,
            description="List Notion databases accessible to the tenant.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["notion", "database", "list"],
        ),
        "notion_list_pages": ToolMetadata(
            name="notion_list_pages",
            category=ToolCategory.CUSTOM,
            description="List Notion pages accessible to the tenant.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["notion", "page", "list"],
        ),
        "notion_create_page": ToolMetadata(
            name="notion_create_page",
            category=ToolCategory.CUSTOM,
            description="Create a new Notion page.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["notion", "page", "create"],
        ),
        "notion_update_page": ToolMetadata(
            name="notion_update_page",
            category=ToolCategory.CUSTOM,
            description="Update properties of an existing Notion page.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["notion", "page", "update"],
        ),
        "notion_append_blocks": ToolMetadata(
            name="notion_append_blocks",
            category=ToolCategory.CUSTOM,
            description="Append content blocks to a Notion page.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["notion", "page", "write"],
        ),
        "notion_delete_block": ToolMetadata(
            name="notion_delete_block",
            category=ToolCategory.CUSTOM,
            description="Delete a block from a Notion page.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["notion", "page", "delete"],
        ),
        # ── Asana / Linear (pm_module) ────────────────────────────────────────
        "asana_create_task": ToolMetadata(
            name="asana_create_task",
            category=ToolCategory.CUSTOM,
            description="Create a new task in Asana.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["asana", "task", "create", "project-management"],
        ),
        "asana_update_task": ToolMetadata(
            name="asana_update_task",
            category=ToolCategory.CUSTOM,
            description="Update an existing Asana task.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["asana", "task", "update", "project-management"],
        ),
        "asana_search_tasks": ToolMetadata(
            name="asana_search_tasks",
            category=ToolCategory.CUSTOM,
            description="Search tasks in Asana by keyword or filter.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["asana", "task", "search", "project-management"],
        ),
        "asana_get_task_stories": ToolMetadata(
            name="asana_get_task_stories",
            category=ToolCategory.CUSTOM,
            description="Get activity stories (comments, changes) for an Asana task.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["asana", "task", "history", "project-management"],
        ),
        "asana_add_task_comment": ToolMetadata(
            name="asana_add_task_comment",
            category=ToolCategory.CUSTOM,
            description="Add a comment to an Asana task.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["asana", "task", "comment", "project-management"],
        ),
        "linear_create_issue": ToolMetadata(
            name="linear_create_issue",
            category=ToolCategory.CUSTOM,
            description="Create a new issue in Linear.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["linear", "issue", "create", "project-management"],
        ),
        "linear_update_issue": ToolMetadata(
            name="linear_update_issue",
            category=ToolCategory.CUSTOM,
            description="Update an existing Linear issue.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["linear", "issue", "update", "project-management"],
        ),
        "linear_list_teams": ToolMetadata(
            name="linear_list_teams",
            category=ToolCategory.CUSTOM,
            description="List teams in the Linear workspace.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["linear", "teams", "project-management"],
        ),
        "linear_list_cycles": ToolMetadata(
            name="linear_list_cycles",
            category=ToolCategory.CUSTOM,
            description="List sprints/cycles in Linear.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["linear", "cycles", "sprint", "project-management"],
        ),
        "linear_add_comment": ToolMetadata(
            name="linear_add_comment",
            category=ToolCategory.CUSTOM,
            description="Add a comment to a Linear issue.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["linear", "issue", "comment", "project-management"],
        ),
        # ── PM extras (read-only, complement asana_linear feature) ───────────
        "asana_list_projects": ToolMetadata(
            name="asana_list_projects",
            category=ToolCategory.CUSTOM,
            description="List Asana projects for the tenant workspace.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["asana", "project-management", "list"],
        ),
        "asana_get_project_tasks": ToolMetadata(
            name="asana_get_project_tasks",
            category=ToolCategory.CUSTOM,
            description="List tasks in an Asana project.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["asana", "project-management", "tasks"],
        ),
        "linear_list_issues": ToolMetadata(
            name="linear_list_issues",
            category=ToolCategory.CUSTOM,
            description="List issues in Linear with optional filters.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["linear", "project-management", "list"],
        ),
        "linear_get_project_summary": ToolMetadata(
            name="linear_get_project_summary",
            category=ToolCategory.CUSTOM,
            description="Get a summary of a Linear project: progress, members, issues.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["linear", "project-management", "summary"],
        ),
        # ── Web crawl / context (onboarding + data_access agents) ────────────
        "crawl_website": ToolMetadata(
            name="crawl_website",
            category=ToolCategory.CUSTOM,
            description=(
                "Crawl a website domain and return page content as markdown. "
                "Used in onboarding to collect company context from the client's website."
            ),
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["web", "crawl", "onboarding", "context"],
        ),
        "extract_company_context": ToolMetadata(
            name="extract_company_context",
            category=ToolCategory.CUSTOM,
            description=(
                "Extract structured company context (sector, products, tone) "
                "from crawled website content using LLM."
            ),
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["web", "crawl", "onboarding", "context", "extraction"],
        ),
        # ── Reports (document_io agents) ──────────────────────────────────────
        "list_report_templates": ToolMetadata(
            name="list_report_templates",
            category=ToolCategory.CUSTOM,
            description="List available report templates (financial, CRM, operational, etc.).",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["report", "templates", "document"],
        ),
        "generate_report": ToolMetadata(
            name="generate_report",
            category=ToolCategory.CUSTOM,
            description=(
                "Generate a formatted report from a template and data. "
                "Output formats: markdown, Google Docs, Google Sheets."
            ),
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["report", "document", "analytics", "export"],
        ),
    }

    # =========================================================================
    # DOCKER MCP TOOLS - Optional, loaded from Docker MCP toolkit
    # =========================================================================
    DOCKER_MCP_TOOLS: dict[str, ToolMetadata] = {
        "github_read": ToolMetadata(
            name="github_read",
            category=ToolCategory.DOCKER_MCP,
            description="Read GitHub repositories, issues, and pull requests",
            tier_required=TierLevel.ENTERPRISE,
            docker_mcp_integration="github",
            requires_confirmation=False,
            tags=["github", "vcs", "code"],
        ),
        "github_write": ToolMetadata(
            name="github_write",
            category=ToolCategory.DOCKER_MCP,
            description="Create/update GitHub issues and pull requests",
            tier_required=TierLevel.ENTERPRISE,
            docker_mcp_integration="github",
            requires_confirmation=True,
            tags=["github", "vcs", "code"],
        ),
        # ── Slack Docker MCP stubs (renamed to avoid collision with slack_module.py) ──
        "slack_docker_read": ToolMetadata(
            name="slack_docker_read",
            category=ToolCategory.DOCKER_MCP,
            description="Read Slack messages and channels (via Docker MCP bridge)",
            tier_required=TierLevel.ENTERPRISE,
            docker_mcp_integration="slack",
            requires_confirmation=False,
            tags=["slack", "messaging", "chat", "docker-mcp"],
        ),
        "slack_docker_send": ToolMetadata(
            name="slack_docker_send",
            category=ToolCategory.DOCKER_MCP,
            description="Send Slack messages (via Docker MCP bridge)",
            tier_required=TierLevel.ENTERPRISE,
            docker_mcp_integration="slack",
            requires_confirmation=True,
            tags=["slack", "messaging", "chat", "docker-mcp"],
        ),
        "stripe_read": ToolMetadata(
            name="stripe_read",
            category=ToolCategory.DOCKER_MCP,
            description="Read Stripe payment information",
            tier_required=TierLevel.ENTERPRISE,
            docker_mcp_integration="stripe",
            requires_confirmation=False,
            tags=["stripe", "payments", "billing"],
        ),
        "stripe_charge": ToolMetadata(
            name="stripe_charge",
            category=ToolCategory.DOCKER_MCP,
            description="Process Stripe payments",
            tier_required=TierLevel.ENTERPRISE,
            docker_mcp_integration="stripe",
            requires_confirmation=True,
            tags=["stripe", "payments", "billing"],
        ),
        "postgres_query": ToolMetadata(
            name="postgres_query",
            category=ToolCategory.DOCKER_MCP,
            description="Query external PostgreSQL databases",
            tier_required=TierLevel.ENTERPRISE,
            docker_mcp_integration="postgres",
            requires_confirmation=False,
            tags=["postgres", "database", "sql"],
        ),
        "jira_read": ToolMetadata(
            name="jira_read",
            category=ToolCategory.DOCKER_MCP,
            description="Read Jira issues and projects",
            tier_required=TierLevel.ENTERPRISE,
            docker_mcp_integration="jira",
            requires_confirmation=False,
            tags=["jira", "project-management", "issues"],
        ),
        "jira_write": ToolMetadata(
            name="jira_write",
            category=ToolCategory.DOCKER_MCP,
            description="Create/update Jira issues",
            tier_required=TierLevel.ENTERPRISE,
            docker_mcp_integration="jira",
            requires_confirmation=True,
            tags=["jira", "project-management", "issues"],
        ),
    }

    # =========================================================================
    # CLASS METHODS
    # =========================================================================

    @classmethod
    def get_all_tools(cls) -> dict[str, ToolMetadata]:
        """Get all registered tools (builtin + Google + Docker MCP)."""
        all_tools = {}
        all_tools.update(cls.BUILTIN_TOOLS)
        all_tools.update(cls.GOOGLE_TOOLS)
        all_tools.update(cls.DOCKER_MCP_TOOLS)
        return all_tools

    @classmethod
    def get_tool(cls, tool_name: str) -> ToolMetadata | None:
        """
        Get tool metadata by name.

        Args:
            tool_name: Name of the tool to look up

        Returns:
            ToolMetadata if found, None otherwise
        """
        return (
            cls.BUILTIN_TOOLS.get(tool_name)
            or cls.GOOGLE_TOOLS.get(tool_name)
            or cls.DOCKER_MCP_TOOLS.get(tool_name)
        )

    @classmethod
    def get_available_tools(
        cls,
        enabled_tools: list[str],
        tier: str,
        include_docker_mcp: bool = False,
        include_google: bool = True,
    ) -> list[ToolMetadata]:
        """
        Get tools available for a client based on enabled list and tier.

        This is the main method used by agents to determine which tools
        are available for a specific client.

        Args:
            enabled_tools: List of tool names from client config
            tier: Client tier (BASIC, SME, ENTERPRISE)
            include_docker_mcp: Whether to check Docker MCP tools
            include_google: Whether to check Google integration tools

        Returns:
            List of accessible ToolMetadata objects
        """
        available = []

        # Always check builtin tools
        for tool_name in enabled_tools:
            tool = cls.BUILTIN_TOOLS.get(tool_name)
            if tool and tool.enabled and tool.is_accessible_by_tier(tier):
                available.append(tool)

        # Optionally check Google tools
        if include_google:
            for tool_name in enabled_tools:
                tool = cls.GOOGLE_TOOLS.get(tool_name)
                if tool and tool.enabled and tool.is_accessible_by_tier(tier):
                    available.append(tool)

        # Optionally check Docker MCP tools (only for ENTERPRISE tier)
        if include_docker_mcp:
            for tool_name in enabled_tools:
                tool = cls.DOCKER_MCP_TOOLS.get(tool_name)
                if tool and tool.enabled and tool.is_accessible_by_tier(tier):
                    available.append(tool)

        logger.debug(
            f"Available tools for tier {tier}: {[t.name for t in available]}"
        )
        return available

    @classmethod
    def validate_client_tools(
        cls, enabled_tools: list[str], tier: str
    ) -> tuple[bool, list[str]]:
        """
        Validate that client's enabled_tools are compatible with tier.

        Use this to check configuration validity, e.g., when updating
        a client's tier or enabled tools.

        Args:
            enabled_tools: List of tool names from client config
            tier: Client tier as string

        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        errors = []

        for tool_name in enabled_tools:
            tool = cls.get_tool(tool_name)

            if not tool:
                errors.append(f"{tool_name} (tool not found in registry)")
            elif not tool.is_accessible_by_tier(tier):
                errors.append(
                    f"{tool_name} (requires {tool.tier_required.value}, "
                    f"client has {tier})"
                )
            elif not tool.enabled:
                errors.append(f"{tool_name} (tool is globally disabled)")

        is_valid = len(errors) == 0
        return is_valid, errors

    @classmethod
    def get_tools_for_tier(cls, tier: str) -> list[ToolMetadata]:
        """
        Get all tools accessible at a given tier.

        Useful for showing what tools become available at each tier.

        Args:
            tier: Target tier

        Returns:
            List of tools accessible at that tier
        """
        accessible = []

        for tool in cls.get_all_tools().values():
            if tool.enabled and tool.is_accessible_by_tier(tier):
                accessible.append(tool)

        return accessible

    @classmethod
    def get_for_task(
        cls,
        enabled_tools: list[str],
        tier: str,
        intent_tags: list[str] | None = None,
        available_context: list[str] | None = None,
        max_tools: int = 8,
    ) -> list[str]:
        """
        Return up to max_tools tool names ranked by relevance to the current intent.

        When intent_tags is empty or None, returns the first max_tools accessible
        tools with no relevance filtering (safe default for first-turn / unknown intent).

        When intent_tags is provided, each eligible tool is scored by the fraction of
        intent tags that appear in its own tags list. Tools are returned highest-score
        first; zero-score tools fill remaining slots to reach max_tools.

        available_context is accepted for future required_context gating but unused now.

        Args:
            enabled_tools: Agent whitelist of tool names (from agent_catalog config)
            tier: Client tier string ("BASIC", "SME", "PREMIUM", "ENTERPRISE")
            intent_tags: Tags extracted from the current user intent, e.g. ["rfq", "suppliers"]
            available_context: Keys present in client_context (reserved, not yet filtered on)
            max_tools: Maximum number of tool names to return

        Returns:
            Ordered list of tool name strings, up to max_tools, relevance-first
        """
        all_tools = cls.get_all_tools()
        intent_set = set(intent_tags) if intent_tags else set()

        eligible: list[tuple[float, str]] = []
        for name in enabled_tools:
            meta = all_tools.get(name)
            if not meta or not meta.enabled or not meta.is_accessible_by_tier(tier):
                continue
            score = (
                len(intent_set & set(meta.tags)) / len(intent_set)
                if intent_set
                else 0.0
            )
            eligible.append((score, name))

        if intent_set:
            # Stable sort: ties preserve insertion (enabled_tools) order
            eligible.sort(key=lambda x: x[0], reverse=True)

        return [name for _, name in eligible[:max_tools]]

    @classmethod
    def get_tools_by_category(cls, category: ToolCategory) -> list[ToolMetadata]:
        """
        Get all tools in a specific category.

        Args:
            category: Tool category to filter by

        Returns:
            List of tools in that category
        """
        return [
            tool
            for tool in cls.get_all_tools().values()
            if tool.category == category
        ]

    @classmethod
    def get_confirmation_required_tools(cls) -> list[ToolMetadata]:
        """Get all tools that require user confirmation."""
        return [
            tool
            for tool in cls.get_all_tools().values()
            if tool.requires_confirmation
        ]

    @classmethod
    def register_custom_tool(cls, tool: ToolMetadata) -> None:
        """
        Register a custom tool at runtime.

        Use this for dynamic tool registration, e.g., from database
        or configuration files.

        Args:
            tool: ToolMetadata to register
        """
        cls.BUILTIN_TOOLS[tool.name] = tool
        logger.info(f"Registered custom tool: {tool.name}")

    @classmethod
    def register_docker_mcp_tools(cls, docker_tools: dict[str, ToolMetadata]) -> int:
        """
        Register Docker MCP tools discovered at runtime.

        This is called by DockerMCPAdapter after discovering running
        Docker MCP containers.

        Args:
            docker_tools: Dict mapping tool_name -> ToolMetadata

        Returns:
            Number of tools registered
        """
        count = 0
        for tool_name, tool_metadata in docker_tools.items():
            if tool_name not in cls.DOCKER_MCP_TOOLS:
                cls.DOCKER_MCP_TOOLS[tool_name] = tool_metadata
                logger.info(f"Registered Docker MCP tool: {tool_name}")
                count += 1
            else:
                # Update existing tool metadata
                cls.DOCKER_MCP_TOOLS[tool_name] = tool_metadata
                logger.debug(f"Updated Docker MCP tool: {tool_name}")
        return count

    @classmethod
    def get_docker_mcp_integrations(cls) -> dict[str, list[str]]:
        """
        Get all Docker MCP integrations and their tools.

        Returns:
            Dict mapping integration_name -> list of tool names
        """
        integrations: dict[str, list[str]] = {}
        for tool in cls.DOCKER_MCP_TOOLS.values():
            if tool.docker_mcp_integration:
                if tool.docker_mcp_integration not in integrations:
                    integrations[tool.docker_mcp_integration] = []
                integrations[tool.docker_mcp_integration].append(tool.name)
        return integrations

    @classmethod
    def is_docker_mcp_tool(cls, tool_name: str) -> bool:
        """Check if a tool is a Docker MCP tool."""
        return tool_name in cls.DOCKER_MCP_TOOLS
