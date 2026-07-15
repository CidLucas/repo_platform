"""
blu_agent_framework.skills
~~~~~~~~~~~~~~~~~~~~~~~~~~

Skill definitions and registry for the Agent-as-Skill pattern.

A SkillDefinition describes a focused, ephemeral sub-agent that executes a
single narrow task (CSV analysis, RAG search, document extraction, etc.) with
its own tool subset, turn budget, and system prompt stored in Langfuse.

Usage:
    from blu_agent_framework.skills import SKILL_REGISTRY, SkillDefinition

    skill = SKILL_REGISTRY["analyze_csv"]
    logger.info(skill.prompt_name)   # "skill:analyze_csv:system")
    logger.info(skill.required_tool_names)
"""

from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

from dataclasses import dataclass, field


class SkillTurnLimitError(Exception):
    """
    Raised when a skill exceeds max_turns and on_max_turns='raise'.

    Callers that set on_max_turns='raise' treat the skill as transactional
    (e.g., RFQ dispatch): partial output is invalid, so the error propagates
    to let the parent agent surface it to the user.
    """

    def __init__(self, skill_name: str, max_turns: int) -> None:
        self.skill_name = skill_name
        self.max_turns = max_turns
        super().__init__(
            f"Skill '{skill_name}' exceeded max_turns={max_turns}. "
            "Set on_max_turns='return_partial' if partial output is acceptable."
        )


@dataclass
class SkillDefinition:
    """
    Descriptor for a single reusable skill.

    Attributes:
        name: Unique skill identifier (e.g. "analyze_csv").
        description: One-line description used by the planner to select skills.
        required_tool_names: Tool whitelist for this skill's AgentBuilder instance.
        prompt_name: Langfuse text-prompt key (convention: "skill:{name}:system").
        max_turns: Maximum LLM ↔ tool cycles before the skill stops.
        output_schema: Optional Pydantic model for structured output validation.
        on_max_turns: Behaviour when max_turns is hit.
            "return_partial" — return whatever state exists (default; safe for
                               summarisation and read-only skills).
            "raise"          — raise SkillTurnLimitError (use for transactional
                               skills where partial output is invalid).
    """

    name: str
    description: str
    required_tool_names: list[str]
    prompt_name: str
    max_turns: int = 4
    output_schema: type | None = None
    on_max_turns: str = "return_partial"
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.on_max_turns not in ("return_partial", "raise"):
            raise ValueError(
                f"SkillDefinition.on_max_turns must be 'return_partial' or 'raise', "
                f"got '{self.on_max_turns}'"
            )


# =============================================================================
# Skill Registry
# =============================================================================
#
# prompt_name follows the convention "skill:{name}:system"; those prompts are
# stored in Langfuse under label="production" and fetched by SkillFactory via
# blu_prompt_management.get_prompt_loader().load(skill.prompt_name).
#
# required_tool_names must be a subset of the agent's own enabled_tools;
# SkillFactory intersects them at runtime so an agent without CSV access cannot
# accidentally run the analyze_csv skill.
#
# Naming conventions:
#   Domain capabilities  → snake_case noun (sql_analytics, rag_search, analyze_csv)
#   Routine narratives   → snake_case verb+noun (reconciliation_report, followup_draft)
#   Platform actions     → snake_case noun (plataforma, monday, agenda)
#   Google integrations  → google_workspace (full suite) or google_docs (docs only)
#   KB management        → kb_management (was "documentos" — renamed to avoid
#                          collision with the "documentos" agent slug)

SKILL_REGISTRY: dict[str, SkillDefinition] = {

    # ==========================================================================
    # Core capabilities — high-reuse primitives
    # These appear on many agents. Consider them "base capabilities" rather than
    # specialist skills; they are explicit here so required_tool_names is
    # always the source of truth for tool resolution.
    # ==========================================================================

    "reconciliation_report": SkillDefinition(
        name="reconciliation_report",
        description=(
            "Generate a monthly cash reconciliation narrative: spot anomalies in "
            "categories, highlight top merchants, and flag discrepancies."
        ),
        required_tool_names=[],  # pure narrative — context pre-injected by routine engine
        prompt_name="skill:reconciliation_report:system",
        max_turns=3,
        on_max_turns="return_partial",
        tags=["routines", "finance", "reconciliation", "narrative"],
    ),

    "register_transaction": SkillDefinition(
        name="register_transaction",
        description=(
            "Register financial transactions from natural language: sales, purchases, "
            "expenses, and receipts. Extracts structured fields and persists to the "
            "client's financial ledger."
        ),
        required_tool_names=["register_transaction"],
        prompt_name="skill:register_transaction:system",
        max_turns=3,
        on_max_turns="raise",
        tags=["finance", "transactions", "data-entry", "ledger"],
    ),

    # ==========================================================================
    # Domain — CRM & Clientes
    # ==========================================================================


    "followup_draft": SkillDefinition(
        name="followup_draft",
        description=(
            "Write a post-sale follow-up message for a specific customer, optionally "
            "including cross-sell suggestions based on purchase history."
        ),
        required_tool_names=["execute_sql", "executar_rag_cliente"],  # draft only — sending via communication skill
        prompt_name="skill:followup_draft:system",
        max_turns=2,
        on_max_turns="return_partial",
        tags=["routines", "clients", "followup", "sales"],
    ),

    "collection_messages": SkillDefinition(
        name="collection_messages",
        description=(
            "Draft personalised collection messages for overdue customers, adapting "
            "tone by days overdue (friendly / firm / urgent)."
        ),
        required_tool_names=["execute_sql", "executar_rag_cliente"],  # draft only — sending via communication skill
        prompt_name="skill:collection_messages:system",
        max_turns=2,
        on_max_turns="return_partial",
        tags=["routines", "clients", "collection", "messages"],
    ),

    "reactivation_proposal": SkillDefinition(
        name="reactivation_proposal",
        description=(
            "Compose a contextualised reactivation proposal for an inactive customer, "
            "referencing their purchase history and optionally including a special offer."
        ),
        required_tool_names=["execute_sql", "executar_rag_cliente"],  # draft only — sending via communication skill
        prompt_name="skill:reactivation_proposal:system",
        max_turns=2,
        on_max_turns="return_partial",
        tags=["routines", "clients", "reactivation", "retention"],
    ),

    "satisfaction_survey": SkillDefinition(
        name="satisfaction_survey",
        description=(
            "Generate a personalised post-delivery satisfaction survey message, "
            "adapted to the customer's profile and recent purchase."
        ),
        required_tool_names=["execute_sql", "executar_rag_cliente"],  # draft only — sending via communication skill
        prompt_name="skill:satisfaction_survey:system",
        max_turns=2,
        on_max_turns="return_partial",
        tags=["routines", "clients", "nps", "satisfaction"],
    ),

    # crm_ops removida — era skill:*:system eliminada. Capacidades de CRM distribuídas
    # nos agentes: frontdesk (relacionamento), financeiro (cobrança), strategy (segmentação).
    # churn_risk_analysis e nps_response_drafter: não implementar por ora (decisão Jun/2026).

    # ==========================================================================
    # Domain — Compras / Fornecedores
    # ==========================================================================


    "monday": SkillDefinition(
        name="monday",
        description=(
            "Read, create, and update Monday.com boards and items: "
            "list boards/items, update status and dates, retrieve comments, summarize board state."
        ),
        required_tool_names=[
            "monday_list_boards",
            "monday_list_items",
            "monday_create_item",
            "monday_update_item_status",
            "monday_get_board_summary",
            "monday_get_item_updates",
            "monday_summarize_board",
        ],
        prompt_name="skill:monday:system",
        max_turns=5,
        on_max_turns="raise",
        tags=["monday", "tasks", "project-management"],
    ),

    "meeting_brief": SkillDefinition(
        name="meeting_brief",
        description=(
            "Produce a pre-meeting briefing with participant context, business history, "
            "key talking points, and suggested agenda items."
        ),
        required_tool_names=[],
        prompt_name="skill:meeting_brief:system",
        max_turns=3,
        on_max_turns="return_partial",
        tags=["routines", "agenda", "scheduling", "meeting", "briefing"],
    ),

    # ==========================================================================
    # Domain — Estratégia & Síntese
    # ==========================================================================

    # Infra: rotina de catálogo sbm_lightrag_weekly_synthesis (cron semanal)
    # despacha este slug como skill step — sem esta entrada o engine caía no
    # fallback de agent slug inexistente e o ciclo nunca rodava de verdade.
    "sbm_to_lightrag_synthesis": SkillDefinition(
        name="sbm_to_lightrag_synthesis",
        description=(
            "Weekly SBM → LightRAG knowledge-graph synthesis (infra). "
            "Reads curated shared business memory and upserts entity "
            "syntheses into the client's knowledge graph."
        ),
        required_tool_names=["sbm_to_lightrag_synthesis"],
        prompt_name="skill:sbm_to_lightrag_synthesis:system",
        max_turns=3,
        on_max_turns="return_partial",
        tags=["routines", "knowledge-graph", "lightrag", "infra"],
    ),

    "insights_synthesis": SkillDefinition(
        name="insights_synthesis",
        description=(
            "Synthesise cross-domain insights from finance, clients, procurement, and agenda "
            "data into a unified strategic narrative. Used by daily_insights routine."
        ),
        required_tool_names=[],
        prompt_name="skill:insights_synthesis:system",
        max_turns=4,
        on_max_turns="return_partial",
        tags=["routines", "synthesis", "strategy", "analysis", "narrative"],
    ),

    "hidden_patterns": SkillDefinition(
        name="hidden_patterns",
        description=(
            "Analyse sales time-series and KPIs to identify anomalies, seasonality, "
            "unexpected peaks/drops, and generate an explanatory narrative with recommendations."
        ),
        required_tool_names=[],
        prompt_name="skill:hidden_patterns:system",
        max_turns=3,
        on_max_turns="return_partial",
        tags=["routines", "strategy", "analytics", "patterns"],
    ),

    "strategy_analysis": SkillDefinition(
        name="strategy_analysis",
        description=(
            "Deep cross-domain strategic analysis: parallel fanout across Financial, CRM, "
            "Purchasing, and Operations domains, then synthesises patterns and produces "
            "Top 3 prioritised initiatives each with a target KPI, timeline, and risk."
        ),
        required_tool_names=[],
        prompt_name="skill:strategy_analysis:system",
        max_turns=6,
        on_max_turns="return_partial",
        tags=["strategy", "analysis", "cross-domain", "initiatives"],
    ),

    "competitor_analysis": SkillDefinition(
        name="competitor_analysis",
        description=(
            "Produce a competitive analysis comparing the client's performance against "
            "scraped competitor content: positioning, gaps, opportunities, and threats."
        ),
        required_tool_names=[],
        prompt_name="skill:competitor_analysis:system",
        max_turns=4,
        on_max_turns="return_partial",
        tags=["routines", "strategy", "competitive", "analysis"],
    ),

    # ==========================================================================
    # Domain — Platform / Rotinas
    # ==========================================================================


    "fiscal": SkillDefinition(
        name="fiscal",
        description=(
            "Issue NF-e/NFS-e invoices, validate fiscal data, and check SEFAZ integration status — raises on incomplete data."
        ),
        required_tool_names=[
            "executar_rag_cliente",
            "fiscal_preparar_dados_nfe",
            "fiscal_status_integracao",
            "execute_sql",
            "whatsapp_enviar_mensagem",
        ],
        prompt_name="skill:fiscal:system",
        max_turns=6,
        on_max_turns="raise",
        tags=["fiscal", "nfe", "nfse", "tax", "sefaz"],
    ),

    # ==========================================================================
    # Onboarding / Contexto
    # ==========================================================================

    "onboarding_context_build": SkillDefinition(
        name="onboarding_context_build",
        description=(
            "Converte dados de onboarding (wizard + website) em contexto estruturado: "
            "company_profile, brand_voice, metas iniciais e context_map.md inicial."
        ),
        required_tool_names=[],
        prompt_name="skill:onboarding_context_build:system",
        max_turns=4,
        on_max_turns="return_partial",
        tags=["onboarding", "context", "company_profile", "brand_voice", "narrative"],
    ),

    # ==========================================================================
    # Routine Narratives — pure-LLM narrative skills (no tools needed)
    # Called DIRECTLY by the routine engine (step type "skill") — NOT via
    # skill dispatch from an agent. Context is pre-injected by the engine;
    # required_tool_names is intentionally empty.
    # These skills do NOT appear in any agent's skill_slugs.
    # ==========================================================================
    # ==========================================================================

    "morning_plan": SkillDefinition(
        name="morning_plan",
        description=(
            "Generate a prioritised daily plan narrative from KPIs, calendar agenda, "
            "pending approvals, and integration alerts. Used by the morning_sync routine."
        ),
        required_tool_names=[],
        prompt_name="skill:morning_plan:system",
        max_turns=2,
        on_max_turns="return_partial",
        tags=["routines", "morning", "planning", "narrative"],
    ),

    "end_of_day_digest": SkillDefinition(
        name="end_of_day_digest",
        description=(
            "Summarise the day's events, completed tasks, and open items into a "
            "concise end-of-day digest. Used by the end_of_day_digest routine."
        ),
        required_tool_names=[],
        prompt_name="skill:end_of_day_digest:system",
        max_turns=2,
        on_max_turns="return_partial",
        tags=["routines", "digest", "narrative", "eod"],
    ),

    "weekly_summary": SkillDefinition(
        name="weekly_summary",
        description=(
            "Generate a weekly performance summary with highlights, KPI trends, "
            "and recommended focus areas for the following week."
        ),
        required_tool_names=[],
        prompt_name="skill:weekly_summary:system",
        max_turns=2,
        on_max_turns="return_partial",
        tags=["routines", "weekly", "summary", "narrative"],
    ),

    "finance_monitor_report": SkillDefinition(
        name="finance_monitor_report",
        description=(
            "Generate a financial health snapshot: revenue vs target, top cost centres, "
            "cash-flow alerts, and recommended actions. Used by financeiro_monitor routine."
        ),
        required_tool_names=[],
        prompt_name="skill:finance_monitor_report:system",
        max_turns=3,
        on_max_turns="return_partial",
        tags=["routines", "finance", "monitor", "report", "alert"],
    ),

    "clients_monitor_report": SkillDefinition(
        name="clients_monitor_report",
        description=(
            "Generate a client health snapshot: active vs churned clients, overdue accounts, "
            "NPS signals, and priority engagement actions. Used by clientes_monitor routine."
        ),
        required_tool_names=[],
        prompt_name="skill:clients_monitor_report:system",
        max_turns=3,
        on_max_turns="return_partial",
        tags=["routines", "clients", "monitor", "report", "alert"],
    ),

    "agenda_monitor_report": SkillDefinition(
        name="agenda_monitor_report",
        description=(
            "Generate an agenda health snapshot: overdue follow-ups, upcoming meetings, "
            "client contact gaps, and priority scheduling actions. Used by agenda_monitor routine."
        ),
        required_tool_names=[],
        prompt_name="skill:agenda_monitor_report:system",
        max_turns=3,
        on_max_turns="return_partial",
        tags=["routines", "agenda", "scheduling", "monitor", "report", "alert"],
    ),

    "inventory_digest": SkillDefinition(
        name="inventory_digest",
        description=(
            "Synthesise procurement and inventory data into a structured digest: "
            "low-stock alerts, supplier delays, PO status, and cost anomalies (compras_monitor routine)."
        ),
        required_tool_names=[],
        prompt_name="skill:inventory_digest:system",
        max_turns=3,
        on_max_turns="return_partial",
        tags=["routines", "procurement", "monitor", "report", "alert"],
    ),

    # ==========================================================================
    # v3 CORE — shared transversal skills
    # Added 2026-06-01. These replace the scattered v2 slugs across agents.
    # See docs/AGENT_SYSTEM_PANORAMA.md for architecture decisions D1-D12.
    # ==========================================================================

    # D12: RAG + catalog unified here. execute_sql added via sql_analytics.
    "data_access": SkillDefinition(
        name="data_access",
        description=(
            "Transversal read layer: semantic KB search (RAG), data catalog lookup, "
            "and routine insight cards. Available to almost all agents. "
            "SQL access via sql_analytics."
        ),
        required_tool_names=[
            "executar_rag_cliente",
            "query_data_catalog",
            "listar_insights_cliente",
            "consultar_grafo_conhecimento",
        ],
        prompt_name="skill:data_access:system",
        max_turns=4,
        on_max_turns="return_partial",
        tags=["rag", "knowledge-base", "search", "catalog"],
    ),

    # D3: register_transaction — data-entry ONLY. on_max_turns=raise (transactional).
    "ledger": SkillDefinition(
        name="ledger",
        description=(
            "Transactional write layer. Persists operational transactions (sales, purchases, "
            "expenses, events) via register_transaction. Used exclusively by data-entry."
        ),
        required_tool_names=["register_transaction", "execute_sql", "executar_rag_cliente", "query_data_catalog", "peek_csv_columns"],
        prompt_name="skill:ledger:system",
        max_turns=3,
        on_max_turns="raise",
        tags=["finance", "transactions", "data-entry", "ledger", "write"],
    ),

    # D7: KB write separated from ingest. context-gatherer + doc-writer only.
    "knowledge_base_write": SkillDefinition(
        name="knowledge_base_write",
        description=(
            "Write structured context to the client knowledge base: persist summaries, "
            "update context documents, check KB coverage status."
        ),
        required_tool_names=["executar_rag_cliente", "write_summary_to_kb", "get_knowledge_status", "update_context_document"],
        prompt_name="skill:knowledge_base_write:system",
        max_turns=3,
        on_max_turns="raise",
        tags=["knowledge-base", "persistence", "write", "documents"],
    ),

    # D1: execute_sql absorbs executar_sql_agent (mode=direct|agent).
    # executar_sql_agent kept in ToolRegistry for backward compat but not used here.
    "sql_analytics": SkillDefinition(
        name="sql_analytics",
        description=(
            "Execute SQL queries on structured business data: sales, revenue, stock, "
            "clients, expenses, suppliers. Single tool: execute_sql (mode=direct|agent)."
        ),
        required_tool_names=["execute_sql"],
        prompt_name="skill:sql_analytics:system",
        max_turns=5,
        on_max_turns="return_partial",
        tags=["sql", "analytics", "finance", "sales", "inventory", "clients"],
    ),

    "analytics_charts": SkillDefinition(
        name="analytics_charts",
        description=(
            "Generate self-contained HTML charts (bar, line, pie, doughnut) from "
            "structured data using Chart.js."
        ),
        required_tool_names=["generate_chart_html"],
        prompt_name="skill:analytics_charts:system",
        max_turns=3,
        on_max_turns="return_partial",
        tags=["chart", "visualization", "html", "reports", "analytics"],
    ),

    "csv_analytics": SkillDefinition(
        name="csv_analytics",
        description="Inspect CSV/tabular file columns before import, analysis, or mapping.",
        required_tool_names=["peek_csv_columns"],
        prompt_name="skill:csv_analytics:system",
        max_turns=2,
        on_max_turns="return_partial",
        tags=["csv", "analytics", "import", "parsing"],
    ),

    # ==========================================================================
    # v3 DOMAIN — per-agent specialised skills
    # ==========================================================================

    "platform_ops": SkillDefinition(
        name="platform_ops",
        description="Configure automated routines and business goals by eliciting intent, presenting a plain-language plan, and executing only after explicit user confirmation.",
        required_tool_names=[
            "criar_rotina",
            "listar_rotinas_catalogo",
            "listar_rotinas_personalizadas",
            "criar_rotina_personalizada",
            "enviar_rotina_para_aprovacao",
            "definir_meta",
            "listar_metas",
            "listar_insights_cliente",
            "executar_rag_cliente",
        ],
        prompt_name="skill:plataforma:system",
        max_turns=6,
        on_max_turns="raise",
        tags=["platform", "routines", "goals", "config", "automation"],
    ),

    # D5: parse_business_reply absorbs parse_supplier_reply.
    "communication": SkillDefinition(
        name="communication",
        description=(
            "Draft, review, and send outbound WhatsApp and email messages to clients or suppliers; "
            "parse inbound replies (RFQ, NPS, payment) and extract structured data."
        ),
        required_tool_names=[
            "send_whatsapp_message",
            "send_whatsapp_batch",
            "check_whatsapp_replies",
            "send_email",
            "read_emails",
            "parse_business_reply",
        ],
        prompt_name="skill:communication:system",
        max_turns=4,
        on_max_turns="raise",
        tags=["whatsapp", "email", "communication", "outreach", "rfq"],
    ),

    # D6: calendar separated from document_io.
    "calendar": SkillDefinition(
        name="calendar",
        description=(
            "Google Calendar integration: query events, write/update events, "
            "import schedule from Google Sheets."
        ),
        required_tool_names=[
            "query_calendar",
            "google_calendar_write",
            "import_spreadsheet_schedule",
        ],
        prompt_name="skill:calendar:system",
        max_turns=4,
        on_max_turns="raise",  # transactional: writes calendar events
        tags=["calendar", "google", "scheduling", "events"],
    ),

    # D6: google_docs + google_workspace merged. query_calendar excluded (→ calendar).
    "document_io": SkillDefinition(
        name="document_io",
        description=(
            "Create, read, write, export, and list Google Docs and Sheets: "
            "primary output channel for doc-writer (external/signed documents and data exports)."
        ),
        required_tool_names=[
            "google_docs_create", "google_docs_read",
            "google_docs_update", "google_docs_list",
            "write_to_sheet", "list_spreadsheets",
            "export_to_sheet", "create_spreadsheet_with_data",
        ],
        prompt_name="skill:document_io:system",
        max_turns=5,
        on_max_turns="raise",  # transactional: google_docs_create creates external resource
        tags=["google", "sheets", "docs", "reports", "documents", "export"],
    ),

    # D7: ingest pipeline separated from KB write.
    "document_curation": SkillDefinition(
        name="document_curation",
        description=(
            "Document ingestion pipeline: OCR extraction, section summarisation, "
            "structured data extraction, time-series compilation."
        ),
        required_tool_names=[
            "extract_document_with_ocr",
            "summarize_document_sections",
            "extract_structured_data",
            "compile_time_series",
        ],
        prompt_name="skill:document_curation:system",
        max_turns=5,
        on_max_turns="raise",  # transactional pipeline: partial ingest leaves KB inconsistent
        tags=["documents", "ocr", "extraction", "summarization", "ingest"],
    ),

    "onboarding": SkillDefinition(
        name="onboarding",
        description=(
            "Initial context collection: check config completeness, save config fields, "
            "map data sources, suggest and confirm column mappings."
        ),
        required_tool_names=[
            "check_config_completeness",
            "save_config_field",
            "get_agent_requirements",
            "finalize_config",
            "list_data_sources",
            "suggest_column_mapping",
            "update_schema_mapping",
            "peek_csv_columns",
        ],
        prompt_name="skill:onboarding:system",
        max_turns=6,
        on_max_turns="raise",
        tags=["onboarding", "schema", "mapping", "config", "context"],
    ),

    "notion": SkillDefinition(
        name="notion",
        description="Create, read, update, search, and manage Notion pages and databases as internal knowledge base and wiki.",
        required_tool_names=[
            "notion_search", "notion_read_page", "notion_query_database",
            "notion_list_databases", "notion_list_pages", "notion_create_page",
            "notion_update_page", "notion_append_blocks", "notion_delete_block",
        ],
        prompt_name="skill:notion:system",
        max_turns=5,
        on_max_turns="raise",  # transactional: creates/updates external Notion pages
        tags=["notion", "documents", "knowledge-base", "writing"],
    ),

}

