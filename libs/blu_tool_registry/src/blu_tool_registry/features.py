"""
blu_tool_registry.features
~~~~~~~~~~~~~~~~~~~~~~~~~~

FeatureRegistry — business capability layer between Tier and Resources.

Architecture:
    Tier -> Features (business capabilities) -> Resources (agents + tools)

Each Feature represents a coherent business capability that a client can access.
Features are cumulative: PREMIUM includes all SME features, SME includes all BASIC, etc.

Usage:
    from blu_tool_registry.features import FeatureRegistry, FeatureConfig

    features = FeatureRegistry.get_features_for_tier("SME")
    agents = FeatureRegistry.get_agents_for_tier("SME")
    tools = FeatureRegistry.get_tools_for_tier("SME")
    tools_for_agent = FeatureRegistry.get_tools_for_agent_and_tier("financeiro", "SME")
"""

from __future__ import annotations

from dataclasses import dataclass

from .tool_metadata import TierLevel


@dataclass(frozen=True)
class FeatureConfig:
    """
    Represents a single business capability.

    Attributes:
        name:        Unique slug for the feature (e.g. "financeiro").
        description: Human-readable description of what this feature enables.
        agents:      Agent slugs that participate in this feature.
        tools:       Tool slugs that compose this feature.
        tier_min:    Minimum tier required to access this feature.
    """

    name: str
    description: str
    agents: tuple[str, ...]
    tools: tuple[str, ...]
    tier_min: TierLevel

    def __repr__(self) -> str:
        return f"FeatureConfig(name={self.name!r}, tier_min={self.tier_min.value!r})"


# ---------------------------------------------------------------------------
# Master feature definitions — keep in sync with docs/FEATURE_MAP.md
# ---------------------------------------------------------------------------

_F = FeatureConfig  # alias for brevity

FEATURES: dict[str, FeatureConfig] = {
    # -- FREE -----------------------------------------------------------------
    "chat_basico": _F(
        name="chat_basico",
        description="Chat with the assistant -- no business data access.",
        agents=("frontdesk",),
        tools=("ferramenta_publica_de_teste",),
        tier_min=TierLevel.FREE,
    ),
    "diagnostico": _F(
        name="diagnostico",
        description="System diagnostics and health testing.",
        agents=("frontdesk",),
        tools=("ferramenta_publica_de_teste",),
        tier_min=TierLevel.FREE,
    ),
    # -- BASIC ----------------------------------------------------------------
    "rag": _F(
        name="rag",
        description="Search the client's knowledge base (documents, PDFs, SOPs).",
        agents=("frontdesk", "documentos"),
        tools=("executar_rag_cliente",),
        tier_min=TierLevel.BASIC,
    ),
    "onboarding": _F(
        name="onboarding",
        description="Initial context collection, data mapping, config registration.",
        agents=("context-gatherer",),
        tools=(
            "check_config_completeness",
            "save_config_field",
            "get_agent_requirements",
            "finalize_config",
            "peek_csv_columns",
            "list_data_sources",
            "query_data_catalog",
            "suggest_column_mapping",
            "update_schema_mapping",
            "get_knowledge_status",
            "update_context_document",
            "register_transaction",
            "write_summary_to_kb",
            "executar_rag_cliente",
        ),
        tier_min=TierLevel.BASIC,
    ),
    "monitoramento_web": _F(
        name="monitoramento_web",
        description="Web monitoring: product features, keywords, brand mentions.",
        agents=("frontdesk",),
        tools=("monitor_feature", "monitor_keywords", "monitor_company"),
        tier_min=TierLevel.BASIC,
    ),
    # -- SME ------------------------------------------------------------------
    "sql_analytics": _F(
        name="sql_analytics",
        description="SQL queries over structured business data (sales, stock, clients).",
        agents=(
            "frontdesk", "data-analyst", "financeiro",
            "compras", "agenda", "documentos", "estrategia",
        ),
        tools=("execute_sql", "executar_sql_agent"),
        tier_min=TierLevel.SME,
    ),
    "platform_ops": _F(
        name="platform_ops",
        description="Create and manage automated routines and business goals via NL.",
        agents=("platform", "context-gatherer"),
        tools=(
            "criar_rotina",
            "listar_rotinas_catalogo",
            "listar_rotinas_personalizadas",
            "criar_rotina_personalizada",
            "enviar_rotina_para_aprovacao",
            "definir_meta",
            "listar_metas",
        ),
        tier_min=TierLevel.SME,
    ),
    "synthesis": _F(
        name="synthesis",
        description="Cross-dimensional analysis spanning 2+ business domains.",
        agents=("synthesis", "data-analyst"),
        tools=("executar_rag_cliente", "execute_sql"),
        tier_min=TierLevel.SME,
    ),
    "compras_basico": _F(
        name="compras_basico",
        description="Purchase pattern analysis, supplier management, basic RFQ (no WhatsApp).",
        agents=("compras", "supplier-agent"),
        tools=(
            "executar_rag_cliente", "execute_sql",
            "list_suppliers", "dispatch_rfq", "check_rfq_responses",
            "parse_buying_list", "validate_buying_list", "optimize_allocation",
            "generate_po_report", "create_purchase_order", "approve_purchase_order",
            "suggest_counter_offer", "add_supplier", "update_supplier", "remove_supplier",
            "import_buying_list_from_sheets", "export_po_to_sheets", "submit_mock_response",
        ),
        tier_min=TierLevel.SME,
    ),
    "financeiro": _F(
        name="financeiro",
        description="Financial monitor: cash flow, revenue, expenses, anomaly alerts.",
        agents=("financeiro", "data-analyst"),
        tools=("executar_rag_cliente", "execute_sql", "register_transaction"),
        tier_min=TierLevel.SME,
    ),
    "agenda_basico": _F(
        name="agenda_basico",
        description="Schedule planning and follow-up -- no external integrations.",
        agents=("agenda",),
        tools=("executar_rag_cliente", "execute_sql"),
        tier_min=TierLevel.SME,
    ),
    "documentos": _F(
        name="documentos",
        description="Document search, digestion, OCR and structured extraction.",
        agents=("documentos", "context-gatherer"),
        tools=(
            "executar_rag_cliente", "execute_sql", "write_summary_to_kb",
            "extract_document_with_ocr", "summarize_document_sections",
            "extract_structured_data", "compile_time_series",
        ),
        tier_min=TierLevel.SME,
    ),
    "ocr_extraction": _F(
        name="ocr_extraction",
        description="Text and structured data extraction from PDFs and scanned documents.",
        agents=("documentos", "doc-writer"),
        tools=(
            "extract_document_with_ocr", "summarize_document_sections",
            "extract_structured_data", "compile_time_series", "write_summary_to_kb",
        ),
        tier_min=TierLevel.SME,
    ),
    "notion": _F(
        name="notion",
        description="Read and write in Notion (pages, databases).",
        agents=("synthesis", "doc-writer"),
        tools=(
            "notion_search", "notion_read_page", "notion_query_database",
            "notion_list_databases", "notion_list_pages", "notion_create_page",
            "notion_update_page", "notion_append_blocks", "notion_delete_block",
        ),
        tier_min=TierLevel.SME,
    ),
    "monday": _F(
        name="monday",
        description="Monday.com integration: boards, items, status, updates.",
        agents=("scheduler-agent",),
        tools=(
            "monday_list_boards", "monday_list_items", "monday_create_item",
            "monday_update_item_status", "monday_get_board_summary",
            "monday_get_item_updates", "monday_summarize_board",
        ),
        tier_min=TierLevel.SME,
    ),
    "whatsapp": _F(
        name="whatsapp",
        description=(
            "Send messages via WhatsApp Business (single and batch). "
            "SME: supplier-agent only (RFQ). crm gets WhatsApp via crm_avancado (PREMIUM)."
        ),
        agents=("supplier-agent",),
        tools=("whatsapp_enviar_mensagem", "whatsapp_enviar_lote"),
        tier_min=TierLevel.SME,
    ),
    # -- PREMIUM --------------------------------------------------------------
    "compras_avancado": _F(
        name="compras_avancado",
        description="RFQ via WhatsApp, supplier reply parsing, automated negotiation.",
        agents=("supplier-agent", "compras"),
        tools=(
            "dispatch_rfq_whatsapp", "parse_supplier_reply",
            "whatsapp_enviar_mensagem", "suggest_counter_offer",
        ),
        tier_min=TierLevel.PREMIUM,
    ),
    "crm_avancado": _F(
        name="crm_avancado",
        description="LTV, cohort, churn prediction, client segmentation, re-engagement campaigns.",
        agents=("crm", "data-analyst"),
        tools=(
            "executar_rag_cliente", "execute_sql",
            "whatsapp_enviar_mensagem", "whatsapp_enviar_lote",
        ),
        tier_min=TierLevel.PREMIUM,
    ),
    "google_integrations": _F(
        name="google_integrations",
        description="Google Calendar, Sheets, Docs: read, write, export, create.",
        agents=("scheduler-agent", "doc-writer", "agenda"),
        tools=(
            "query_calendar", "write_to_sheet", "read_emails", "list_google_accounts",
            "list_spreadsheets", "export_to_sheet", "create_spreadsheet_with_data",
            "google_docs_create", "google_docs_read", "google_docs_write",
            "google_docs_list", "import_spreadsheet_schedule",
        ),
        tier_min=TierLevel.PREMIUM,
    ),
    "estrategia": _F(
        name="estrategia",
        description="Strategic planning, KPI analysis, briefs, growth opportunities.",
        agents=("estrategia", "synthesis", "data-analyst"),
        tools=("executar_rag_cliente", "execute_sql", "notion_search", "notion_read_page"),
        tier_min=TierLevel.PREMIUM,
    ),
    "slack": _F(
        name="slack",
        description="Read and send Slack messages: channels, threads, summaries.",
        agents=("crm", "synthesis"),
        tools=(
            "slack_list_channels", "slack_read_channel", "slack_summarize_channel",
            "slack_post_message", "slack_get_unread",
        ),
        tier_min=TierLevel.PREMIUM,
    ),
    "asana_linear": _F(
        name="asana_linear",
        description="Task management in Asana and Linear: create, update, search, comment.",
        agents=("scheduler-agent", "crm"),
        tools=(
            "asana_create_task", "asana_update_task", "asana_search_tasks",
            "asana_get_task_stories", "asana_add_task_comment",
            "linear_create_issue", "linear_update_issue", "linear_list_teams",
            "linear_list_cycles", "linear_add_comment",
        ),
        tier_min=TierLevel.PREMIUM,
    ),
    # -- ENTERPRISE -----------------------------------------------------------
    "fiscal": _F(
        name="fiscal",
        description="NF-e / NFS-e issuance, fiscal data validation, SEFAZ integration (stub).",
        agents=("fiscal-agent",),
        tools=(
            "fiscal_preparar_dados_nfe", "fiscal_status_integracao",
            "executar_rag_cliente", "execute_sql",
        ),
        tier_min=TierLevel.ENTERPRISE,
    ),
    "docker_mcp": _F(
        name="docker_mcp",
        description="Docker MCP integrations: GitHub, Slack, Stripe, PostgreSQL, Jira.",
        agents=("frontdesk",),
        tools=(
            "github_read", "github_write", "slack_read", "slack_send",
            "stripe_read", "stripe_charge", "postgres_query", "jira_read", "jira_write",
        ),
        tier_min=TierLevel.ENTERPRISE,
    ),
}

# ---------------------------------------------------------------------------
# TIER_FEATURES: computed from FEATURES — cumulative per tier.
# A feature is included in a tier if tier_min <= that tier.
# Preserves FEATURES insertion order (defines priority within a tier).
# Adding a new feature to FEATURES automatically populates all tiers.
# ---------------------------------------------------------------------------

_TIER_ORDER: list[TierLevel] = [
    TierLevel.FREE,
    TierLevel.BASIC,
    TierLevel.SME,
    TierLevel.PREMIUM,
    TierLevel.ENTERPRISE,
    TierLevel.ADMIN,
]

TIER_FEATURES: dict[str, tuple[str, ...]] = {
    t.value: tuple(
        name
        for name, f in FEATURES.items()
        if TierLevel.get_order(f.tier_min.value) <= TierLevel.get_order(t.value)
    )
    for t in _TIER_ORDER
}


class FeatureRegistry:
    """
    Query interface over the FEATURES and TIER_FEATURES maps.

    All methods accept both string tier names ("SME") and TierLevel enums.
    Invalid tier names raise ValueError.
    """

    # -- private helpers ------------------------------------------------------

    @staticmethod
    def _normalize_tier(tier: str | TierLevel) -> str:
        if isinstance(tier, TierLevel):
            return tier.value
        normalized = tier.strip().upper()
        if normalized not in TIER_FEATURES:
            raise ValueError(
                f"Unknown tier {tier!r}. Valid tiers: {list(TIER_FEATURES)}"
            )
        return normalized

    @staticmethod
    def _collect_unique(features: list[FeatureConfig], attr: str) -> list[str]:
        """Deduplicated ordered union of a tuple attribute across a list of features."""
        seen: set[str] = set()
        result: list[str] = []
        for feature in features:
            for item in getattr(feature, attr):
                if item not in seen:
                    seen.add(item)
                    result.append(item)
        return result

    # -- public API -----------------------------------------------------------

    @classmethod
    def get_features_for_tier(cls, tier: str | TierLevel) -> list[FeatureConfig]:
        """Return all FeatureConfig objects available to *tier* (cumulative)."""
        t = cls._normalize_tier(tier)
        return [FEATURES[name] for name in TIER_FEATURES[t] if name in FEATURES]

    @classmethod
    def get_feature_names_for_tier(cls, tier: str | TierLevel) -> list[str]:
        """Return feature name slugs available to *tier*."""
        t = cls._normalize_tier(tier)
        return list(TIER_FEATURES[t])

    @classmethod
    def get_agents_for_tier(cls, tier: str | TierLevel) -> list[str]:
        """Return deduplicated agent slugs accessible under *tier*."""
        return cls._collect_unique(cls.get_features_for_tier(tier), "agents")

    @classmethod
    def get_tools_for_tier(cls, tier: str | TierLevel) -> list[str]:
        """Return deduplicated tool slugs accessible under *tier*."""
        return cls._collect_unique(cls.get_features_for_tier(tier), "tools")

    @classmethod
    def get_tools_for_agent_and_tier(
        cls, agent_slug: str, tier: str | TierLevel
    ) -> list[str]:
        """
        Return tools available to *agent_slug* under *tier*.

        Computed as the union of tools from every feature where agent_slug
        participates, restricted to tools accessible at this tier.
        Preserves feature insertion order.
        """
        tier_tools: set[str] = set(cls.get_tools_for_tier(tier))
        seen: set[str] = set()
        result: list[str] = []
        for feature in cls.get_features_for_tier(tier):
            if agent_slug in feature.agents:
                for tool in feature.tools:
                    if tool in tier_tools and tool not in seen:
                        seen.add(tool)
                        result.append(tool)
        return result

    @classmethod
    def get_feature(cls, name: str) -> FeatureConfig | None:
        """Look up a single feature by slug. Returns None if not found."""
        return FEATURES.get(name)

    @classmethod
    def is_agent_accessible(cls, agent_slug: str, tier: str | TierLevel) -> bool:
        """Return True if *agent_slug* is available under *tier*."""
        return agent_slug in cls.get_agents_for_tier(tier)

    @classmethod
    def is_tool_accessible(cls, tool_slug: str, tier: str | TierLevel) -> bool:
        """Return True if *tool_slug* is reachable under *tier* via any feature."""
        return tool_slug in cls.get_tools_for_tier(tier)

    @classmethod
    def all_feature_names(cls) -> list[str]:
        """Return every registered feature name."""
        return list(FEATURES)
