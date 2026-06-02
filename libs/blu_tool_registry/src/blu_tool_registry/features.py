"""
blu_tool_registry.features
~~~~~~~~~~~~~~~~~~~~~~~~~~

FeatureRegistry — business capability layer between Tier and Resources.

Architecture:
    Tier -> Features (business capabilities) -> Resources (agents + tools)

Each Feature represents a coherent business capability that a client can access.
Features are cumulative: PREMIUM includes all SME features, SME includes all BASIC, etc.

Agent slugs (v3 — 12 agents):
    frontdesk, data-entry, platform, financeiro, compras, crm,
    agenda, data-analyst, strategy, doc-writer, context-gatherer, fiscal-agent

Removed (v2 → v3):
    documentos  → absorbed by doc-writer / context-gatherer
    estrategia  → merged into strategy
    synthesis   → merged into strategy
    supplier-agent → absorbed by compras

Design decisions encoded here:
    D1  execute_sql absorbs executar_sql_agent (single SQL tool)
    D3  data-entry is the ONLY agent with register_transaction (ledger feature)
    D4  HITL is middleware (requires_confirmation in ToolRegistry), not a feature
    D11 scope=read enforced per-agent via feature participation:
        agents that need SQL read get sql_analytics;
        only data-entry gets ledger (register_transaction).
        execute_sql is intentionally write-capable at DB level — enforcement
        of SELECT-only for non-ledger agents is reinforced via system prompts.
        A future FeatureConfig.read_only_tools field will make this structural.

Usage:
    from blu_tool_registry.features import FeatureRegistry, FeatureConfig

    features = FeatureRegistry.get_features_for_tier("SME")
    agents   = FeatureRegistry.get_agents_for_tier("SME")
    tools    = FeatureRegistry.get_tools_for_tier("SME")
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
# Master feature definitions — keep in sync with docs/AGENT_SYSTEM_PANORAMA.md
# ---------------------------------------------------------------------------

_F = FeatureConfig  # alias for brevity

FEATURES: dict[str, FeatureConfig] = {

    # =========================================================================
    # FREE
    # =========================================================================

    "chat_basico": _F(
        name="chat_basico",
        description="Chat with the assistant — no business data access.",
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

    # =========================================================================
    # BASIC
    # =========================================================================

    # -- Core skill: data_access (read) ---------------------------------------
    # RAG + catalog available to almost every agent at BASIC.
    # execute_sql is gated at SME via sql_analytics.
    # D12: executar_rag_cliente is part of data_access, not a domain skill.
    "data_access": _F(
        name="data_access",
        description=(
            "Transversal read layer: semantic KB search (RAG) and data catalog. "
            "Available to all agents that need client context. "
            "SQL access gated separately at SME tier via sql_analytics."
        ),
        agents=(
            "frontdesk", "data-entry", "financeiro", "compras", "crm",
            "agenda", "data-analyst", "strategy", "doc-writer",
            "context-gatherer", "fiscal-agent",
        ),
        tools=("executar_rag_cliente", "query_data_catalog"),
        tier_min=TierLevel.BASIC,
    ),

    # -- Core skill: ledger (write) — data-entry ONLY -------------------------
    # D3: single agent responsible for all transactional writes.
    # register_transaction is intentionally absent from every other feature.
    "ledger": _F(
        name="ledger",
        description=(
            "Transactional write layer. data-entry is the ONLY agent allowed to "
            "register transactions. Other agents read financial data via data_access "
            "and sql_analytics; they redirect write requests to data-entry."
        ),
        agents=("data-entry",),
        tools=("register_transaction",),  # requires_confirmation=True in ToolRegistry
        tier_min=TierLevel.BASIC,
    ),

    # -- Core skill: knowledge_base (write) — context-gatherer + doc-writer --
    "knowledge_base_write": _F(
        name="knowledge_base_write",
        description=(
            "Write to the client knowledge base: persist summaries, update context "
            "documents, check KB coverage. Restricted to agents that manage content."
        ),
        agents=("context-gatherer", "doc-writer"),
        tools=("write_summary_to_kb", "get_knowledge_status", "update_context_document"),
        tier_min=TierLevel.BASIC,
    ),

    # -- Onboarding / context-gatherer core -----------------------------------
    "onboarding": _F(
        name="onboarding",
        description=(
            "Initial context collection, schema mapping, config registration. "
            "Triggered by onboarding_complete, doc_ingested webhooks, or daily routine. "
            "is_frontdesk=false — not exposed in chat rooms."
        ),
        agents=("context-gatherer",),
        tools=(
            # config tools
            "check_config_completeness",
            "save_config_field",
            "get_agent_requirements",
            "finalize_config",
            # schema_ops skill
            "list_data_sources",
            "suggest_column_mapping",
            "update_schema_mapping",  # HITL via ToolRegistry requires_confirmation
            # data_parsing
            "peek_csv_columns",
            # web context collection
            "crawl_website",
            "extract_company_context",
            # google account discovery
            "list_google_accounts",
        ),
        tier_min=TierLevel.BASIC,
    ),

    # -- Visualization --------------------------------------------------------
    "analytics_charts": _F(
        name="analytics_charts",
        description="HTML Chart.js generation. Available to all analytics agents.",
        agents=("financeiro", "crm", "data-analyst", "strategy"),
        tools=("generate_chart_html",),
        tier_min=TierLevel.BASIC,
    ),

    # -- CSV inspection -------------------------------------------------------
    "csv_analytics": _F(
        name="csv_analytics",
        description="CSV/tabular file inspection: column peek before import or analysis.",
        agents=("data-analyst", "financeiro", "data-entry", "fiscal-agent"),
        tools=("peek_csv_columns",),
        tier_min=TierLevel.BASIC,
    ),

    # -- Web monitoring -------------------------------------------------------
    "monitoramento_web": _F(
        name="monitoramento_web",
        description="Web monitoring: product features, keywords, brand mentions.",
        agents=("frontdesk",),
        tools=("monitor_feature", "monitor_keywords", "monitor_company"),
        tier_min=TierLevel.BASIC,
    ),

    # =========================================================================
    # SME
    # =========================================================================

    # -- SQL (read scope for all listed agents) -------------------------------
    # D1: executar_sql_agent removed — execute_sql is the single SQL tool
    #     with mode=direct|agent.
    # D11: write-scope enforcement via system prompts; ledger feature is the
    #      structural gate for register_transaction.
    "sql_analytics": _F(
        name="sql_analytics",
        description=(
            "SQL queries over structured business data (sales, stock, clients, financials). "
            "Single tool: execute_sql (mode=direct|agent). "
            "All listed agents are expected to issue SELECT-only queries; "
            "write operations are routed to data-entry via ledger."
        ),
        agents=(
            "frontdesk", "data-entry", "financeiro", "compras", "crm",
            "agenda", "data-analyst", "strategy", "context-gatherer", "fiscal-agent",
        ),
        tools=("execute_sql",),  # D1: executar_sql_agent removed
        tier_min=TierLevel.BASIC,
    ),

    # -- Platform ops ---------------------------------------------------------
    "platform_ops": _F(
        name="platform_ops",
        description="Create and manage automated routines and business goals via NL.",
        agents=("platform",),
        tools=(
            "criar_rotina",
            "listar_rotinas_catalogo",
            "listar_rotinas_personalizadas",
            "criar_rotina_personalizada",
            "enviar_rotina_para_aprovacao",
            "ativar_rotina_catalogo",
            "definir_meta",
            "listar_metas",
        ),
        tier_min=TierLevel.BASIC,
    ),

    # -- Financial analysis ---------------------------------------------------
    # D3: register_transaction removed — financeiro is read-only.
    "financeiro_ops": _F(
        name="financeiro_ops",
        description=(
            "Financial analysis: cash flow, revenue, expenses, anomaly monitoring. "
            "Read-only — transactions are registered exclusively by data-entry."
        ),
        agents=("financeiro",),
        tools=(
            "executar_rag_cliente",  # also in data_access; dedup handled by FeatureRegistry
            "execute_sql",
        ),
        tier_min=TierLevel.BASIC,
    ),

    # -- Procurement ----------------------------------------------------------
    "compras_ops": _F(
        name="compras_ops",
        description=(
            "Full procurement cycle: supplier CRUD, buying list pipeline, "
            "RFQ dispatch, PO creation and approval."
        ),
        agents=("compras",),
        tools=(
            # supplier_mgmt
            "list_suppliers", "add_supplier", "update_supplier", "remove_supplier",
            # procurement_pipeline
            "parse_buying_list", "validate_buying_list", "optimize_allocation",
            "generate_po_report",
            "create_purchase_order",   # HITL via ToolRegistry
            "approve_purchase_order",  # HITL via ToolRegistry
            "suggest_counter_offer",
            # rfq_ops
            "dispatch_rfq", "check_rfq_responses",
            # legacy import/export helpers
            "import_buying_list_from_sheets", "export_po_to_sheets",
        ),
        tier_min=TierLevel.BASIC,
    ),

    # -- CRM operations -------------------------------------------------------
    "crm_ops": _F(
        name="crm_ops",
        description=(
            "CRM analysis: churn, LTV, segmentation, reactivation, NPS. "
            "Read-only SQL + RAG."
        ),
        agents=("crm",),
        tools=(
            "executar_rag_cliente",
            "execute_sql",
        ),
        tier_min=TierLevel.BASIC,
    ),

    # -- Communication (D5) ---------------------------------------------------
    # send_message + send_rfq_via_channel + parse_incoming_reply
    # Módulo: communication_module.py (v3)
    "communication": _F(
        name="communication",
        description=(
            "Outbound/inbound communication: draft & send messages to client contacts (CRM), "
            "dispatch RFQs to suppliers via WhatsApp, and parse free-text replies "
            "(rfq | nps | payment)."
        ),
        agents=("compras", "crm"),
        tools=(
            "send_message",           # draft + send consumer reply (CRM)
            "send_rfq_via_channel",   # D5: absorbs dispatch_rfq_whatsapp
            "parse_incoming_reply",   # D5: absorbs parse_supplier_reply; context_type param
            "read_emails",            # Gmail read for crm/compras agents
        ),
        tier_min=TierLevel.BASIC,
    ),

    # -- Agenda / Calendar ----------------------------------------------------
    "agenda_ops": _F(
        name="agenda_ops",
        description="Schedule planning and follow-up via SQL and RAG context.",
        agents=("agenda",),
        tools=("executar_rag_cliente", "execute_sql"),
        tier_min=TierLevel.BASIC,
    ),

    # -- Monday.com -----------------------------------------------------------
    # Note: 7 API-wrapper tools remain for now.
    # D9 (semantic consolidation to 3 tools) is a tool_pool_api refactor
    # tracked separately. When done, replace with get_project_summary,
    # sync_tasks, update_project_status.
    "monday": _F(
        name="monday",
        description=(
            "Monday.com project management: boards, items, status, summaries. "
            "TODO(D9): consolidate 7 API wrappers → 3 semantic tools."
        ),
        agents=("agenda",),
        tools=(
            "monday_query", "monday_write", "monday_brief",
        ),
        tier_min=TierLevel.BASIC,
    ),

    # -- Document IO (Google Docs + Sheets) -----------------------------------
    # D6: google_docs + google_workspace merged into document_io.
    # query_calendar NOT included here — belongs to calendar feature (PREMIUM).
    "document_io": _F(
        name="document_io",
        description=(
            "Google Docs (create, read, write, list) and Google Sheets "
            "(write, list, export, create). Used by data-analyst for reporting "
            "and doc-writer for collaborative document creation."
        ),
        agents=("data-analyst", "doc-writer"),
        tools=(
            # Google Docs
            "google_docs_create", "google_docs_read",
            "google_docs_write", "google_docs_list",
            # Google Sheets
            "write_to_sheet", "list_spreadsheets",
            "export_to_sheet", "create_spreadsheet_with_data",
            # Reports
            "list_report_templates",
            "generate_report",
        ),
        tier_min=TierLevel.BASIC,
    ),

    # -- Document curation (ingest pipeline) ----------------------------------
    # D7: kb_management split → document_curation (ingest) + knowledge_base_write (write).
    "document_curation": _F(
        name="document_curation",
        description=(
            "Document ingestion pipeline: OCR extraction, section summarization, "
            "structured data extraction, time-series compilation. "
            "context-gatherer uses for trigger-based ingest; "
            "doc-writer uses for processing uploaded documents before KB write."
        ),
        agents=("context-gatherer", "doc-writer"),
        tools=(
            "extract_document_with_ocr",
            "summarize_document_sections",
            "extract_structured_data",
            "compile_time_series",
        ),
        tier_min=TierLevel.BASIC,
    ),

    # -- Notion ---------------------------------------------------------------
    "notion": _F(
        name="notion",
        description="Read and write in Notion (pages, databases).",
        agents=("doc-writer",),
        tools=(
            "notion_search", "notion_read_page", "notion_query_database",
            "notion_list_databases", "notion_list_pages", "notion_create_page",
            "notion_update_page", "notion_append_blocks", "notion_delete_block",
        ),
        tier_min=TierLevel.BASIC,
    ),

    # =========================================================================
    # PREMIUM
    # =========================================================================

    # -- Google Calendar (write + import) -------------------------------------
    # Calendar is PREMIUM — agenda_ops (SME) covers SQL/RAG scheduling only.
    "calendar": _F(
        name="calendar",
        description=(
            "Google Calendar integration: query events, write/update events, "
            "import schedule from Google Sheets."
        ),
        agents=("agenda",),
        tools=(
            "query_calendar",
            "google_calendar_write",
            "import_spreadsheet_schedule",
        ),
        tier_min=TierLevel.BASIC,
    ),

    # -- Strategy (merged estrategia + synthesis) -----------------------------
    "strategy_ops": _F(
        name="strategy_ops",
        description=(
            "Strategic analysis: cross-domain KPI patterns, growth opportunities, "
            "competitor intelligence. Merged from estrategia + synthesis (v2)."
        ),
        agents=("strategy", "data-analyst"),
        tools=("executar_rag_cliente", "execute_sql"),
        tier_min=TierLevel.BASIC,
    ),

    # -- CRM advanced (WhatsApp campaigns at PREMIUM) -------------------------
    "crm_avancado": _F(
        name="crm_avancado",
        description=(
            "CRM advanced: WhatsApp engagement campaigns, batch messaging. "
            "Basic CRM ops (SQL + RAG) are at SME via crm_ops."
        ),
        agents=("crm",),
        tools=(
            "whatsapp_enviar_mensagem",
            "whatsapp_enviar_lote",
        ),
        tier_min=TierLevel.BASIC,
    ),

    # -- Slack ----------------------------------------------------------------
    "slack": _F(
        name="slack",
        description="Read and send Slack messages: channels, threads, summaries.",
        agents=("crm",),
        tools=(
            "slack_list_channels", "slack_read_channel", "slack_summarize_channel",
            "slack_post_message", "slack_get_unread",
        ),
        tier_min=TierLevel.BASIC,
    ),

    # -- Asana / Linear -------------------------------------------------------
    "asana_linear": _F(
        name="asana_linear",
        description="Task management in Asana and Linear: create, update, search, comment.",
        agents=("agenda", "crm"),
        tools=(
            "asana_list_projects",
            "asana_get_project_tasks",
            "asana_create_task", "asana_update_task", "asana_search_tasks",
            "asana_get_task_stories", "asana_add_task_comment",
            "linear_list_issues",
            "linear_get_project_summary",
            "linear_create_issue", "linear_update_issue", "linear_list_teams",
            "linear_list_cycles", "linear_add_comment",
        ),
        tier_min=TierLevel.BASIC,
    ),

    # =========================================================================
    # ENTERPRISE
    # =========================================================================

    # -- Fiscal ---------------------------------------------------------------
    # Note: candidate to become a skill of financeiro post-MVP (tracked in PANORAMA).
    "fiscal": _F(
        name="fiscal",
        description=(
            "NF-e / NFS-e issuance, fiscal data validation, SEFAZ integration. "
            "Candidate to merge into financeiro post-MVP."
        ),
        agents=("fiscal-agent",),
        tools=(
            "fiscal_preparar_dados_nfe",
            "fiscal_status_integracao",
            # data_access tools duplicated here so fiscal-agent gets them
            # even before data_access feature is resolved at ENTERPRISE tier.
            "executar_rag_cliente",
            "execute_sql",
        ),
        tier_min=TierLevel.BASIC,
    ),

    # -- Docker MCP -----------------------------------------------------------
    "docker_mcp": _F(
        name="docker_mcp",
        description="Docker MCP integrations: GitHub, Slack, Stripe, PostgreSQL, Jira.",
        agents=("frontdesk",),
        tools=(
            "github_read", "github_write", "slack_docker_read", "slack_docker_send",
            "stripe_read", "stripe_charge", "postgres_query", "jira_read", "jira_write",
        ),
        tier_min=TierLevel.BASIC,
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
    def all_feature_names(cls) -> list[str] :
        """Return every registered feature name."""
        return list(FEATURES)
