"""
blu_agent_framework.registry
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Unified agent-type catalog.  Single source of truth for every agent type
(workers, standalone agents, future orchestrators) — their tools, prompt
fragments, tier access, and execution budget.

Replaces two diverged registries:
  - atendente_core/core/worker_registry.py   (WorkerConfig / WorkerRegistry)
  - standalone_agent_api/core/factory.py     (AGENT_FRAGMENTS dict)

Usage:
    from blu_agent_framework.registry import AgentTypeConfig, AgentTypeRegistry

    cfg = AgentTypeRegistry.get("data-analyst")
    fragments  = cfg.fragments
    tools      = cfg.enabled_tools
    tier_ok    = AgentTypeRegistry.for_tier("SME")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from blu_llm_service import ModelTier
from blu_tool_registry.tool_metadata import TierLevel

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentTypeConfig:
    """
    Descriptor for a single agent type.

    Covers every dimension needed by both the supervisor-delegation path
    (atendente_core) and the standalone-factory path (standalone_agent_api),
    so fragment lists and tool lists only ever need to be edited here.
    """

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    name: str          # Display name  ("Data Analyst")
    slug: str          # Machine key   ("data-analyst")
    description: str   # One-liner for the supervisor LLM routing prompt

    # ------------------------------------------------------------------
    # Prompt composition
    # ------------------------------------------------------------------
    # fragment list for legacy agents; ignored when prompt_name is set. New agents use prompt_name.
    fragments: list[str] = field(default_factory=list)
    # Langfuse named-prompt key; when non-empty, loaded instead of fragments
    prompt_name: str = ""

    # ------------------------------------------------------------------
    # Tool access
    # ------------------------------------------------------------------
    enabled_tools: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Access control
    # ------------------------------------------------------------------
    tier_required: TierLevel = TierLevel.BASIC

    # ------------------------------------------------------------------
    # Model selection
    # ------------------------------------------------------------------
    model_tier: ModelTier = ModelTier.DEFAULT  # Which LLM tier this agent needs

    # ------------------------------------------------------------------
    # Supervisor routing
    # ------------------------------------------------------------------
    routing_hint: str = ""  # Extra hint shown to supervisor on when to delegate

    # ------------------------------------------------------------------
    # Execution budget (from worker_factory._LLM_MAX_RETRIES / _WORKER_MAX_TURNS)
    # ------------------------------------------------------------------
    max_turns: int = 3
    on_max_turns: str = "return_partial"  # "return_partial" | "raise"
    max_retries: int = 2                  # LLM transient-error retries per turn

    # ------------------------------------------------------------------
    # Metadata / future use
    # ------------------------------------------------------------------
    tags: list[str] = field(default_factory=list)
    output_schema: type | None = None   # Pydantic model for structured output
    graph_topology: str = "default"     # "default" | "fanout" | "supervisor"

    # Backward-compat alias: atendente WorkerConfig had an `agent_slug` field
    # that linked to the standalone AGENT_FRAGMENTS dict.  Now both point at the
    # same registry entry, so agent_slug == slug.
    @property
    def agent_slug(self) -> str:
        return self.slug


# ---------------------------------------------------------------------------
# Agent type definitions — single source of truth
# ---------------------------------------------------------------------------
#
# Fragment naming conventions:
#   fragment/standalone-base          — preamble: identity, language, response style
#   fragment/sql-schema               — client DB schema (injected at compose time)
#   fragment/sql-rules                — SQL generation rules
#   fragment/sql-examples             — few-shot SQL examples
#   fragment/fallback-strategy        — what to do when SQL fails
#   fragment/csv-tools                — DuckDB CSV tool guidance
#   fragment/rag-search               — RAG vector search tool guidance
#   fragment/google-export            — Sheets/Docs export tool guidance
#   fragment/document-intelligence-*  — OCR + extraction guidance
#   fragment/rfq-*                    — procurement domain fragments
#   fragment/standalone-response      — closing instructions (tone, format)
#   fragment/*-workflow               — agent-specific step-by-step workflow

_AGENT_TYPES: dict[str, AgentTypeConfig] = {
    # ------------------------------------------------------------------
    # Frontdesk — entry point specialist
    # Handles simple RAG/SQL inline; routes complex tasks to orchestrator
    # or context-gatherer.
    # ------------------------------------------------------------------
    "frontdesk": AgentTypeConfig(
        name="Frontdesk",
        slug="frontdesk",
        description=(
            "Entry point specialist. Handles simple RAG and SQL queries directly. "
            "Routes complex or multi-domain tasks to the appropriate specialist via handoff tool. "
            "Use as the first point of contact for all user requests."
        ),
        prompt_name="agents/frontdesk",
        enabled_tools=[
            "executar_rag_cliente",
            "execute_sql",
            "ferramenta_publica_de_teste",
        ],
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.FAST,
        routing_hint="Entry point. Simple knowledge questions, basic data queries.",
        max_turns=10,
        tags=["frontdesk", "routing", "rag", "sql"],
    ),
    # ------------------------------------------------------------------
    # Context Gatherer — data mapping, transaction registration,
    # routine creation, and knowledge base curation.
    # Foundational skill: every other skill depends on its output.
    # ------------------------------------------------------------------
    "context-gatherer": AgentTypeConfig(
        name="Context Agent",
        slug="context-gatherer",
        description=(
            "Structured data gathering and mapping specialist. Registers transactions "
            "from natural language, creates automation routine definitions, maps "
            "spreadsheet columns to database fields, and curates the knowledge base. "
            "Use when the user wants to record data, set up automations, or organise "
            "their information landscape."
        ),
        enabled_tools=[
            # --- Routine creation (routines_module) ---
            "listar_rotinas_catalogo",
            "listar_rotinas_personalizadas",
            "criar_rotina_personalizada",
            "enviar_rotina_para_aprovacao",
            # --- Knowledge curation (document_intelligence_module) ---
            "write_summary_to_kb",
            "executar_rag_cliente",
            # --- Transactions + data catalog (context_module) ---
            "register_transaction",
            "list_data_sources",
            "query_data_catalog",
            "suggest_column_mapping",
            "update_schema_mapping",
            # --- Knowledge completeness (context_module) ---
            "get_knowledge_status",
            "update_context_document",
        ],
        fragments=[
            "fragment/context-gatherer-base",
            "fragment/transaction-extraction-rules",
            "fragment/schema-mapping-workflow",
            "fragment/routine-definition-workflow",
            "fragment/knowledge-curation-workflow",
            "fragment/confirmation-patterns",
        ],
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.DEFAULT,
        routing_hint=(
            "Recording sales, purchases, expenses, or events. Setting up automations "
            "or routines. Mapping data sources or spreadsheet columns. Organising "
            "documents, tagging knowledge base files, cleaning up duplicates. "
            "Anything that prepares data for other skills to use."
        ),
        max_turns=6,
        tags=["context", "mapping", "transactions", "routines", "knowledge"],
    ),
    # ------------------------------------------------------------------
    # CRM — client relationship and communication specialist
    # Used by routine skill steps: reengagement emails, client outreach.
    # ------------------------------------------------------------------
    "crm": AgentTypeConfig(
        name="CRM Specialist",
        slug="crm",
        description=(
            "Client relationship and communication specialist. Writes personalised "
            "outreach emails, analyses client segments, and recommends engagement "
            "strategies. Used in routines for reengagement campaigns and follow-ups. "
            "LTV analysis, cohort tracking, churn prediction and NPS deep-dives."
        ),
        prompt_name="agents/crm-specialist",
        enabled_tools=[
            "executar_rag_cliente",
            "execute_sql",
            "whatsapp_enviar_mensagem",
            "whatsapp_enviar_lote",
            "slack_list_channels",
            "slack_read_channel",
            "slack_summarize_channel",
            "slack_post_message",
            "asana_get_task_stories",
            "asana_add_task_comment",
            "linear_add_comment",
        ],
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.POWERFUL,
        routing_hint="Writing client emails, personalised outreach, CRM campaigns.",
        max_turns=8,
        tags=["crm", "email", "clients", "reengagement"],
    ),
    # ------------------------------------------------------------------
    # Estratégia — business strategy and performance analysis specialist
    # Used by routine skill steps: strategic briefs, recommendations.
    # ------------------------------------------------------------------
    "estrategia": AgentTypeConfig(
        name="Strategy Specialist",
        slug="estrategia",
        description=(
            "Business strategy and performance analysis specialist. Analyses KPIs, "
            "identifies growth opportunities, and writes strategic briefs. Used in "
            "routines for monthly reviews and low-acquisition alerts."
        ),
        prompt_name="agents/strategic-planner",
        enabled_tools=[
            "executar_rag_cliente",
            "execute_sql",
        ],
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.POWERFUL,
        routing_hint="Strategic analysis, business performance reviews, growth recommendations.",
        max_turns=8,
        tags=["strategy", "analytics", "kpi", "growth", "planning", "briefs"],
    ),
    # ------------------------------------------------------------------
    # Compras — procurement and supplier analysis specialist
    # ------------------------------------------------------------------
    "compras": AgentTypeConfig(
        name="Procurement Specialist",
        slug="compras",
        description=(
            "Procurement and supplier analysis specialist. Analyses purchase patterns, "
            "identifies supplier risks, and recommends cost optimisation strategies. "
            "Used in routines for monthly procurement reviews."
        ),
        prompt_name="agents/frontdesk",
        enabled_tools=[
            "executar_rag_cliente",
            "execute_sql",
        ],
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.DEFAULT,
        routing_hint="Procurement analysis, supplier reviews, purchasing cost optimisation.",
        max_turns=5,
        tags=["procurement", "suppliers", "purchases", "cost"],
    ),
    # ------------------------------------------------------------------
    # Financeiro — financial health and reporting specialist
    # ------------------------------------------------------------------
    "financeiro": AgentTypeConfig(
        name="Financial Specialist",
        slug="financeiro",
        description=(
            "Financial health and reporting specialist. Analyses revenue trends, "
            "ticket averages, and cash flow indicators. Used in routines for weekly "
            "financial snapshots and alerts."
        ),
        prompt_name="agents/frontdesk",
        enabled_tools=[
            "executar_rag_cliente",
            "execute_sql",
        ],
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.POWERFUL,
        routing_hint="Financial reports, revenue analysis, cash flow monitoring.",
        max_turns=5,
        tags=["finance", "revenue", "reporting", "cashflow"],
    ),
    # ------------------------------------------------------------------
    # Agenda — scheduling and follow-up planning specialist
    # ------------------------------------------------------------------
    "agenda": AgentTypeConfig(
        name="Scheduling Specialist",
        slug="agenda",
        description=(
            "Scheduling and follow-up planning specialist. Creates structured follow-up "
            "schedules, prioritises client contacts, and recommends engagement timing. "
            "Used in routines for weekly follow-up reminders."
        ),
        prompt_name="agents/frontdesk",
        enabled_tools=[
            "executar_rag_cliente",
            "execute_sql",
        ],
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.FAST,
        routing_hint="Follow-up scheduling, client contact prioritisation, calendar planning.",
        max_turns=5,
        tags=["scheduling", "follow-up", "calendar", "clients", "agenda"],
    ),
    # ------------------------------------------------------------------
    # Documentos — knowledge base and document analysis specialist
    # ------------------------------------------------------------------
    "documentos": AgentTypeConfig(
        name="Documents Specialist",
        slug="documentos",
        description=(
            "Knowledge base and document analysis specialist. Searches and summarises "
            "stored documents, identifies knowledge gaps, and produces weekly digests. "
            "Used in routines for knowledge base maintenance."
        ),
        prompt_name="agents/frontdesk",
        enabled_tools=[
            "executar_rag_cliente",
            "execute_sql",
        ],
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.DEFAULT,
        routing_hint="Document search, knowledge base digests, content gap analysis.",
        max_turns=5,
        tags=["documents", "knowledge-base", "rag", "digest"],
    ),
    # ------------------------------------------------------------------
    # Synthesis — cross-dimensional analysis and strategic synthesis
    # ------------------------------------------------------------------
    "synthesis": AgentTypeConfig(
        name="Synthesis Agent",
        slug="synthesis",
        description=(
            "Cross-dimensional analysis agent. Synthesises insights that span multiple "
            "business dimensions (financeiro, compras, clientes, agenda). Activated when "
            "the user asks a question that touches 2+ dimensions or uses strategic "
            "language (investimento, prioridade, custo, tendência, estratégia)."
        ),
        prompt_name="agents/synthesis",
        enabled_tools=[
            "executar_rag_cliente",
            "execute_sql",
            "slack_summarize_channel",
            "slack_list_channels",
            "notion_search",
            "notion_read_page",
            "notion_query_database",
            "notion_list_databases",
            "slack_get_unread",
            "asana_search_tasks",
            "linear_list_cycles",
        ],
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.POWERFUL,
        routing_hint="Cross-dimensional analysis, strategic synthesis, multi-domain insights.",
        max_turns=8,
        tags=["synthesis", "cross-domain", "strategy", "analysis", "multi-dimension"],
    ),
    # ------------------------------------------------------------------
    # DataAnalyst — quantitative cross-dimensional data specialist
    # ------------------------------------------------------------------
    "data-analyst": AgentTypeConfig(
        name="Data Analyst",
        slug="data-analyst",
        description=(
            "Quantitative data analyst specialist. Performs trend analysis, "
            "correlation discovery, and scenario modelling across financial, "
            "purchasing, and client data. Convoked by the Synthesis Agent for "
            "number-heavy questions."
        ),
        prompt_name="agents/data-analyst",
        enabled_tools=[
            "executar_rag_cliente",
            "execute_sql",
        ],
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.POWERFUL,
        routing_hint="Trend analysis, correlation, scenario modelling, quantitative insights.",
        max_turns=6,
        tags=["data", "analysis", "trends", "correlation", "quantitative", "finance", "purchases", "clients"],
    ),
    # ------------------------------------------------------------------
    # Platform — operational configuration and routine/goal management
    # ------------------------------------------------------------------
    "platform": AgentTypeConfig(
        name="Platform Agent",
        slug="platform",
        description=(
            "Platform agent that converts natural language requests into operational "
            "configurations. Activates routines, sets goals, and records structured "
            "data. Triggered by imperative phrases like 'cria uma rotina', 'define "
            "uma meta', 'adiciona um fornecedor'."
        ),
        prompt_name="agents/platform",
        enabled_tools=[
            "criar_rotina",
            "listar_rotinas_catalogo",
            "definir_meta",
            "listar_metas",
            "executar_rag_cliente",
        ],
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.DEFAULT,
        routing_hint="Routine management, goal setting, operational configuration via natural language.",
        max_turns=6,
        tags=["platform", "routines", "goals", "config", "operations"],
    ),
    # ------------------------------------------------------------------
    # SupplierAgent — supplier communication and RFQ specialist
    # ------------------------------------------------------------------
    "supplier-agent": AgentTypeConfig(
        name="Supplier Agent",
        slug="supplier-agent",
        description=(
            "Supplier communication specialist. Sends RFQs via WhatsApp/email, "
            "parses supplier replies, and recommends optimal allocation. "
            "Triggered by requests to contact suppliers, request quotes, or review offers."
        ),
        prompt_name="agents/supplier-agent",
        enabled_tools=[
            "list_suppliers",
            "dispatch_rfq_whatsapp",
            "parse_supplier_reply",
            "whatsapp_enviar_mensagem",
            "executar_rag_cliente",
            "execute_sql",
        ],
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.DEFAULT,
        routing_hint="Supplier quotes, RFQ dispatch, WhatsApp supplier communication.",
        max_turns=6,
        tags=["suppliers", "rfq", "whatsapp", "quotes", "procurement"],
    ),
    # ------------------------------------------------------------------
    # SchedulerAgent — calendar and timeline optimisation specialist
    # ------------------------------------------------------------------
    "scheduler-agent": AgentTypeConfig(
        name="Scheduler Agent",
        slug="scheduler-agent",
        description=(
            "Calendar and timeline optimisation specialist. Checks availability, "
            "detects scheduling conflicts, and recommends optimal meeting/deadline slots. "
            "Uses Google Calendar integration. Triggered by requests about scheduling, "
            "availability checks, or deadline management."
        ),
        prompt_name="agents/scheduler-agent",
        enabled_tools=[
            "query_calendar",
            "executar_rag_cliente",
            "execute_sql",
            "monday_list_boards",
            "monday_list_items",
            "monday_create_item",
            "monday_update_item_status",
            "monday_get_board_summary",
            "monday_get_item_updates",
            "monday_summarize_board",
            "asana_create_task",
            "asana_update_task",
            "asana_search_tasks",
            "linear_create_issue",
            "linear_update_issue",
            "linear_list_teams",
            "linear_list_cycles",
        ],
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.FAST,
        routing_hint="Calendar availability, scheduling conflicts, deadline management.",
        max_turns=5,
        tags=["calendar", "scheduling", "deadlines", "availability", "meetings"],
    ),
    # ------------------------------------------------------------------
    # DocWriter — strategic document creation specialist
    # ------------------------------------------------------------------
    "doc-writer": AgentTypeConfig(
        name="Document Writer",
        slug="doc-writer",
        description=(
            "Strategic document creation specialist. Searches the knowledge base, "
            "writes structured documents (briefs, SOPs, proposals, reports), and "
            "submits them for human review via the HITL approval flow. "
            "Triggered by requests to write, draft, or create documents."
        ),
        prompt_name="agents/doc-writer",
        enabled_tools=[
            "executar_rag_cliente",
            "execute_sql",
            "google_docs_create",
            "google_docs_write",
            "google_docs_read",
            "notion_list_pages",
            "notion_read_page",
            "notion_search",
            "notion_create_page",
            "notion_update_page",
            "notion_append_blocks",
            "notion_delete_block",
            "notion_query_database",
            "notion_list_databases",
        ],
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.POWERFUL,
        routing_hint="Document writing, drafting briefs, SOPs, proposals, knowledge base.",
        max_turns=8,
        tags=["documents", "writing", "drafts", "briefs", "sops", "proposals"],
    ),
    # ------------------------------------------------------------------
    # FiscalAgent — NF-e / NFS-e issuance specialist (stub — external dep)
    # ------------------------------------------------------------------
    "fiscal-agent": AgentTypeConfig(
        name="Fiscal Agent",
        slug="fiscal-agent",
        description=(
            "NF-e and NFS-e issuance specialist. Issues invoices, queries fiscal "
            "status, and validates fiscal data. Requires NF-e/NFS-e integration "
            "(SEFAZ partner). Currently in stub mode — informs user of pending integration."
        ),
        prompt_name="agents/fiscal-agent",
        enabled_tools=[
            "executar_rag_cliente",
            "execute_sql",
            "fiscal_preparar_dados_nfe",
            "fiscal_status_integracao",
        ],
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.DEFAULT,
        routing_hint="Invoice issuance, NF-e, NFS-e, fiscal compliance, SEFAZ.",
        max_turns=4,
        tags=["fiscal", "nfe", "nfse", "invoice", "sefaz", "tax"],
    ),
}


class AgentTypeRegistry:
    """
    Central catalog of all agent types.

    Class-method API mirrors the old WorkerRegistry so existing callers can
    be shimmed without changing call sites.
    """

    @classmethod
    def get(cls, slug: str) -> AgentTypeConfig | None:
        """Return config for *slug*, or None if unknown."""
        return _AGENT_TYPES.get(slug)

    @classmethod
    def all(cls) -> dict[str, AgentTypeConfig]:
        """Return a copy of the full registry."""
        return dict(_AGENT_TYPES)

    @classmethod
    def for_tier(cls, tier: str) -> list[AgentTypeConfig]:
        """Return all agent types accessible at *tier*.

        Normalises *tier* (case-insensitive, strips whitespace) before
        comparison so ``"sme"``, ``" SME "`` and ``"SME"`` are equivalent.

        If *tier* is not a recognised TierLevel value a warning is logged and
        the method returns only BASIC-level agents (safe minimum) instead of
        silently treating the unknown tier as FREE.
        """
        normalised = tier.strip().upper() if isinstance(tier, str) else ""
        try:
            tier_order = TierLevel.get_order(normalised)
        except ValueError:
            logger.warning(
                "[AgentTypeRegistry] Unknown tier %r — falling back to BASIC. "
                "Check that AgentConfig.tier / client_context['tier'] is a valid TierLevel value.",
                tier,
            )
            tier_order = TierLevel.get_order("BASIC")

        result = [
            cfg for cfg in _AGENT_TYPES.values()
            if TierLevel.get_order(cfg.tier_required.value) <= tier_order
        ]
        logger.debug(
            "[AgentTypeRegistry] Available for tier %s: %s",
            normalised, [c.slug for c in result],
        )
        return result

    @classmethod
    def build_supervisor_description(cls, tier: str) -> str:
        """
        Build the ``{{ workers_description }}`` block for the supervisor prompt.

        Lists each accessible agent type with its delegation tool name,
        description, and routing hint.
        """
        configs = cls.for_tier(tier)
        if not configs:
            return "No specialist workers available."

        lines: list[str] = []
        for cfg in configs:
            tool_name = f"delegate_to_{cfg.slug.replace('-', '_')}"
            lines.append(f"- `{tool_name}`: {cfg.description}")
            if cfg.routing_hint:
                lines.append(f"  Use for: {cfg.routing_hint}")
        return "\n".join(lines)
