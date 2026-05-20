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
            enabled_tools=["executar_rag_cliente"],
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
        "executar_rag_cliente": ToolMetadata(
            name="executar_rag_cliente",
            category=ToolCategory.RAG,
            description="Busca informações na base de conhecimento do cliente (RAG)",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["rag", "search", "knowledge-base"],
        ),
        "executar_sql_agent": ToolMetadata(
            name="executar_sql_agent",
            category=ToolCategory.SQL,
            description=(
                "Executes SQL queries on structured data (products, orders, inventory). "
                "Only requires 'query' parameter - client_id is auto-injected."
            ),
            tier_required=TierLevel.SME,
            requires_confirmation=False,
            tags=["sql", "database", "analytics"],
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
        # Phase 2: Negotiation & WhatsApp tools
        "suggest_counter_offer": ToolMetadata(
            name="suggest_counter_offer",
            category=ToolCategory.CUSTOM,
            description="Suggest counter-offer prices based on historical data.",
            tier_required=TierLevel.BASIC,
            requires_confirmation=False,
            tags=["rfq", "procurement", "negotiation"],
        ),
        "dispatch_rfq_whatsapp": ToolMetadata(
            name="dispatch_rfq_whatsapp",
            category=ToolCategory.CUSTOM,
            description="Send an RFQ to a supplier via WhatsApp.",
            tier_required=TierLevel.SME,
            requires_confirmation=False,
            tags=["rfq", "procurement", "whatsapp"],
        ),
        "parse_supplier_reply": ToolMetadata(
            name="parse_supplier_reply",
            category=ToolCategory.CUSTOM,
            description="Parse free-text supplier reply into structured quote data using LLM.",
            tier_required=TierLevel.SME,
            requires_confirmation=False,
            tags=["rfq", "procurement", "whatsapp", "parsing"],
        ),
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
            tier_required=TierLevel.PREMIUM,
            requires_confirmation=False,
            tags=["google", "docs", "create"],
        ),
        "google_docs_read": ToolMetadata(
            name="google_docs_read",
            category=ToolCategory.GOOGLE,
            description="Read content from a Google Docs document.",
            tier_required=TierLevel.PREMIUM,
            requires_confirmation=False,
            tags=["google", "docs", "read"],
        ),
        "google_docs_write": ToolMetadata(
            name="google_docs_write",
            category=ToolCategory.GOOGLE,
            description="Write or append content to a Google Docs document.",
            tier_required=TierLevel.PREMIUM,
            requires_confirmation=False,
            tags=["google", "docs", "write"],
        ),
        "google_docs_list": ToolMetadata(
            name="google_docs_list",
            category=ToolCategory.GOOGLE,
            description="List Google Docs documents accessible to the client.",
            tier_required=TierLevel.PREMIUM,
            requires_confirmation=False,
            tags=["google", "docs", "list"],
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
        "slack_read": ToolMetadata(
            name="slack_read",
            category=ToolCategory.DOCKER_MCP,
            description="Read Slack messages and channels",
            tier_required=TierLevel.ENTERPRISE,
            docker_mcp_integration="slack",
            requires_confirmation=False,
            tags=["slack", "messaging", "chat"],
        ),
        "slack_send": ToolMetadata(
            name="slack_send",
            category=ToolCategory.DOCKER_MCP,
            description="Send Slack messages",
            tier_required=TierLevel.ENTERPRISE,
            docker_mcp_integration="slack",
            requires_confirmation=True,
            tags=["slack", "messaging", "chat"],
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
