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
    tier_ok    = AgentTypeRegistry.for_tier("SME")
    tags       = AgentTypeRegistry.get_by_tag("analytics")
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

    Tool resolution:
        skill_slugs is the canonical source of truth.  factory.py derives the
        tool whitelist by unioning required_tool_names from each skill in
        SKILL_REGISTRY, then filtering by tier via ResourceResolver.
        enabled_tools is kept ONLY for:
          - frontdesk (intentionally not skill-based)
          - agents mid-migration that haven't moved to skills yet
        All other agents must have enabled_tools=[] (default).
    """

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    name: str          # Display name  ("Data Analyst")
    slug: str          # Machine key   ("data-analyst") — must be kebab-case
    description: str   # One-liner for the supervisor LLM routing prompt

    # ------------------------------------------------------------------
    # Prompt composition
    # ------------------------------------------------------------------
    # fragment list for legacy agents; ignored when prompt_name is set.
    fragments: list[str] = field(default_factory=list)
    # Langfuse named-prompt key; when non-empty, loaded instead of fragments.
    prompt_name: str = ""

    # ------------------------------------------------------------------
    # Tool access — see docstring above.  Leave empty for skill-based agents.
    # ------------------------------------------------------------------
    enabled_tools: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Access control
    # ------------------------------------------------------------------
    tier_required: TierLevel = TierLevel.BASIC

    # ------------------------------------------------------------------
    # Model selection
    # ------------------------------------------------------------------
    model_tier: ModelTier = ModelTier.DEFAULT

    # ------------------------------------------------------------------
    # Supervisor routing
    # ------------------------------------------------------------------
    routing_hint: str = ""  # Short, specific trigger description for frontdesk

    # ------------------------------------------------------------------
    # Execution budget
    # ------------------------------------------------------------------
    max_turns: int = 3
    on_max_turns: str = "return_partial"  # "return_partial" | "raise"
    max_retries: int = 2                  # LLM transient-error retries per turn

    # ------------------------------------------------------------------
    # Graph topology — signals concurrency strategy to get_specialist_graph()
    # ------------------------------------------------------------------
    graph_topology: str = "default"  # "default" | "fanout" | "supervisor"

    # ------------------------------------------------------------------
    # Memory mode — conversation / session state requirements
    # ------------------------------------------------------------------
    memory_mode: str = "none"  # "none" | "session" | "persistent"

    # ------------------------------------------------------------------
    # Agent dependency — agents this config may internally delegate to.
    # Prevents supervisor from double-delegating to sub-agents.
    # ------------------------------------------------------------------
    delegates_to: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------
    tags: list[str] = field(default_factory=list)
    output_schema: type | None = None  # Pydantic model for structured output

    # ------------------------------------------------------------------
    # Frontdesk visibility
    # ------------------------------------------------------------------
    frontdesk_visible: bool = False

    # ------------------------------------------------------------------
    # Skill-based tool resolution (canonical since Phase 2)
    # ------------------------------------------------------------------
    skill_slugs: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Backward-compat: atendente WorkerConfig had `agent_slug` == slug.
    # ------------------------------------------------------------------
    @property
    def agent_slug(self) -> str:
        return self.slug

    def __post_init__(self) -> None:
        # Slug format guard
        expected = self.slug.lower().replace("_", "-")
        if self.slug != expected:
            raise ValueError(
                f"AgentTypeConfig.slug must be kebab-case, got '{self.slug}' "
                f"(expected '{expected}')"
            )
        # Prompt source guard
        if not self.fragments and not self.prompt_name:
            raise ValueError(
                f"{self.slug}: must provide at least one of 'fragments' or 'prompt_name'"
            )
        # Routing hint warning for visible agents
        if self.frontdesk_visible and not self.routing_hint:
            logger.warning(
                "%s: frontdesk_visible=True but routing_hint is empty — "
                "frontdesk may misroute this agent",
                self.slug,
            )


# ---------------------------------------------------------------------------
# Agent type definitions — single source of truth  (v3 — 2026-06-01)
# ---------------------------------------------------------------------------
#
# 12 agents (v3):
#   frontdesk, data-entry, platform, financeiro, compras, crm,
#   agenda, data-analyst, strategy, doc-writer, context-gatherer, fiscal-agent
#
# Removed (v2 → v3):
#   documentos    → absorbed by doc-writer (creation) + context-gatherer (ingest)
#   estrategia    → merged into strategy
#   synthesis     → merged into strategy
#   supplier-agent → absorbed by compras
#
# Skill slug conventions (→ SKILL_REGISTRY keys in skills.py, v3 names):
#   data_access          — search_knowledge_base + query_data_catalog  (almost all agents)
#   sql_analytics        — execute_sql (mode=direct|agent)             (almost all agents)
#   ledger               — register_transaction               (data-entry ONLY; D3)
#   knowledge_base_write — write_summary_to_kb + status       (context-gatherer, doc-writer)
#   onboarding           — schema_ops + config tools          (context-gatherer)
#   document_curation    — OCR/extract pipeline               (context-gatherer, doc-writer)
#   analytics_charts     — generate_chart_html                (financeiro, crm, data-analyst, strategy)
#   csv_analytics        — peek_csv_columns                   (data-entry, financeiro, data-analyst)
#   platform_ops         — routines + goals                   (platform)
#   communication        — WA + email + parse_business_reply  (compras, crm)
#   monday               — Monday.com boards                  (agenda)
#   calendar             — Google Calendar                    (agenda)
#   meeting_brief        — pre-meeting briefing narrative      (agenda)
#   document_io          — Google Docs + Sheets               (data-analyst, doc-writer)
#   notion               — Notion pages/databases             (doc-writer)
#   fiscal               — NF-e / NFS-e                       (fiscal-agent)
#   insights_synthesis   — cross-domain strategic narrative   (strategy)
#   hidden_patterns      — time-series anomaly analysis       (strategy)
#   + routine narrative skills (pure-LLM): ver docs/SKILLS_SYSTEM.md
#
# Ver docs/SKILLS_SYSTEM.md para catálogo completo com ferramentas e agentes consumidores.
#
# D4: hitl_approval removed from all skill_slugs — HITL is middleware
#     (requires_confirmation=True in ToolRegistry), not a skill.
# D11: scope=read enforcement per agent is structural via feature participation
#      in features.py — not a skill parameter.

_AGENT_TYPES: dict[str, AgentTypeConfig] = {

    # ------------------------------------------------------------------
    # Frontdesk — entry point; skill-based for RAG/SQL, explicit for handoff.
    # Handles simple queries directly; routes complex tasks to specialists.
    # enabled_tools contains ONLY routing/handoff tools (no skill equivalent).
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
        skill_slugs=["data_access", "sql_analytics"],  # tools resolved via SKILL_REGISTRY
        enabled_tools=[
            # Handoff tool — no skill equivalent; always injected explicitly.
            "route_to_specialist",
        ],
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.FAST,
        routing_hint="Entry point. Simple knowledge questions, basic data queries.",
        max_turns=10,
        memory_mode="session",
        tags=["frontdesk", "routing", "rag", "sql"],
        frontdesk_visible=False,  # never appears in its own catalog
    ),

    # ------------------------------------------------------------------
    # Data Entry — ÚNICO agente de escrita operacional (D3).
    # Recebe NL do usuário → data_parsing → ledger → register_transaction.
    # Se o usuário quer registrar dentro de outra sala, frontdesk redireciona
    # aqui. Outros agentes são SOMENTE leitura.
    # ------------------------------------------------------------------
    "data-entry": AgentTypeConfig(
        name="Data Entry",
        slug="data-entry",
        description=(
            "Single write gateway for operational transactions. Parses natural language "
            "inputs (sales, purchases, expenses, events) into structured records and "
            "persists them via register_transaction. The ONLY agent allowed to write "
            "transactions — all other agents are read-only and redirect here."
        ),
        prompt_name="agents/data-entry",
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.DEFAULT,
        routing_hint=(
            "Registrar vendas, compras, despesas, receitas, eventos. "
            "Importar planilha de lançamentos. Qualquer pedido de escrita de transação."
        ),
        max_turns=6,
        memory_mode="session",
        tags=["data-entry", "transactions", "ledger", "write", "parsing"],
        skill_slugs=["ledger", "data_access", "csv_analytics", "sql_analytics"],
        frontdesk_visible=True,
    ),

    # ------------------------------------------------------------------
    # Platform — operational configuration and routine/goal management
    # ------------------------------------------------------------------
    "platform": AgentTypeConfig(
        name="Platform Agent",
        slug="platform",
        description=(
            "Platform agent that converts natural language requests into operational "
            "configurations. Activates routines, sets goals, and manages automation "
            "definitions. Triggered by imperative phrases like 'cria uma rotina', "
            "'define uma meta'."
        ),
        prompt_name="agents/platform",
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.DEFAULT,
        routing_hint="Routine management, goal setting, operational configuration via natural language.",
        max_turns=6,
        tags=["platform", "routines", "goals", "config", "operations"],
        skill_slugs=["platform_ops", "data_access"],
        frontdesk_visible=True,
    ),

    # ------------------------------------------------------------------
    # Financeiro — financial health and reporting  (read-only; D3)
    # register_transaction removed — redirect write requests to data-entry.
    # ------------------------------------------------------------------
    "financeiro": AgentTypeConfig(
        name="Financial Specialist",
        slug="financeiro",
        description=(
            "Financial health and reporting specialist. Analyses revenue trends, "
            "ticket averages, cash flow indicators, and expense patterns. "
            "Produces structured financial reports with charts. "
            "Used in routines for weekly snapshots and anomaly alerts. "
            "Read-only — transaction registration is handled by data-entry."
        ),
        prompt_name="agents/financeiro",
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.POWERFUL,
        routing_hint="Financial reports, revenue analysis, cash flow monitoring, expense tracking.",
        max_turns=5,
        tags=["finance", "revenue", "reporting", "cashflow"],
        skill_slugs=[
            "data_access", "sql_analytics",
            "analytics_charts", "csv_analytics",
        ],
        frontdesk_visible=True,
    ),

    # ------------------------------------------------------------------
    # Compras — full procurement cycle
    # D5: dispatch_rfq_whatsapp removed — uses communication(template_id=rfq)
    # D8: fornecedores split into supplier_mgmt + procurement_pipeline + rfq_ops
    #     (all three merged into compras_ops feature for now; sub-skills on skill refactor)
    # ------------------------------------------------------------------
    "compras": AgentTypeConfig(
        name="Procurement Specialist",
        slug="compras",
        description=(
            "Procurement and supplier management specialist. Manages supplier catalogue, "
            "processes buying lists through the optimisation pipeline, dispatches RFQs "
            "via WhatsApp and email, parses supplier replies, and creates purchase orders. "
            "Identifies supplier risks and recommends cost optimisation."
        ),
        prompt_name="agents/compras",
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.DEFAULT,
        routing_hint="Procurement, supplier reviews ('fornecedores', gestão de fornecedores), purchasing cost optimisation, RFQ dispatch, supplier management.",
        max_turns=6,
        tags=["procurement", "suppliers", "purchases", "cost", "rfq", "quotes"],
        skill_slugs=[
            "data_access", "sql_analytics", "communication", "inventory_digest",
        ],
        frontdesk_visible=True,
    ),

    # ------------------------------------------------------------------
    # CRM — client relationship and communication specialist
    # ------------------------------------------------------------------
    "crm": AgentTypeConfig(
        name="CRM Specialist",
        slug="crm",
        description=(
            "Client relationship and communication specialist. Analyses client segments, "
            "LTV, churn risk, NPS and reactivation opportunities. Writes personalised "
            "outreach via WhatsApp and email. "
            "Used in routines for collection, follow-up, and satisfaction campaigns."
        ),
        prompt_name="agents/crm",
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.POWERFUL,
        routing_hint="Client emails or WhatsApp, personalised outreach, CRM campaigns, churn analysis, inactive clients ('clientes inativos'), LTV, cohort analysis, client segmentation, reactivation.",
        max_turns=8,
        tags=["crm", "email", "whatsapp", "clients", "reengagement", "churn", "ltv"],
        skill_slugs=[
            "data_access", "sql_analytics",
            "communication", "analytics_charts",
        ],
        frontdesk_visible=True,
    ),

    # ------------------------------------------------------------------
    # Agenda — calendar, scheduling, and Monday.com
    # Scope: calendar + monday only. No Google Docs/Sheets/Gmail (D6).
    # Google Calendar is PREMIUM — agenda_ops covers SQL/RAG at SME.
    # ------------------------------------------------------------------
    "agenda": AgentTypeConfig(
        name="Scheduler Agent",
        slug="agenda",
        description=(
            "Calendar, scheduling, and project management specialist. "
            "Checks availability, detects conflicts, and recommends optimal slots. "
            "Manages Monday.com boards: list, create, update items and track status. "
            "Produces meeting briefs and agenda digests."
        ),
        prompt_name="agents/agenda",
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.DEFAULT,
        routing_hint="Calendar availability, scheduling conflicts, deadline management, Monday.com boards.",
        max_turns=5,
        tags=["calendar", "scheduling", "deadlines", "monday", "meetings", "agenda"],
        skill_slugs=["data_access", "sql_analytics", "monday", "calendar", "meeting_brief"],
        frontdesk_visible=True,
    ),

    # ------------------------------------------------------------------
    # Data Analyst — quantitative analysis and reporting
    # ------------------------------------------------------------------
    "data-analyst": AgentTypeConfig(
        name="Data Analyst",
        slug="data-analyst",
        description=(
            "Quantitative data analyst specialist. Performs trend analysis, "
            "correlation discovery, and scenario modelling across financial, "
            "purchasing, and client data. Exports reports to Google Docs and Sheets."
        ),
        prompt_name="agents/data-analyst",
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.POWERFUL,
        routing_hint="Trend analysis, correlation, scenario modelling, quantitative data insights.",
        max_turns=6,
        tags=["data", "analysis", "trends", "correlation", "quantitative"],
        skill_slugs=[
            "data_access", "sql_analytics",
            "analytics_charts", "csv_analytics", "document_io",
        ],
        frontdesk_visible=True,
    ),

    # ------------------------------------------------------------------
    # Strategy — merged from estrategia + synthesis (v2)
    # Cross-domain narrative + strategic analysis + performance briefs.
    # graph_topology=fanout: finance + CRM + market data in parallel, then reduce.
    # ------------------------------------------------------------------
    "strategy": AgentTypeConfig(
        name="Strategy Specialist",
        slug="strategy",
        description=(
            "Business strategy and cross-dimensional analysis specialist. "
            "Synthesises insights spanning multiple business dimensions (financeiro, "
            "compras, clientes, agenda). Identifies KPI patterns, growth opportunities, "
            "and competitive positioning. Produces morning/EOD digests and strategic briefs. "
            "Activate for questions touching 2+ business areas or strategic language "
            "(investimento, prioridade, tendência, estratégia)."
        ),
        prompt_name="agents/strategy",
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.POWERFUL,
        routing_hint=(
            "Strategic analysis, KPI trends, cross-domain questions (finance + clients + procurement), "
            "business performance reviews ('como está meu negócio', 'o que está acontecendo', visão geral), "
            "investment analysis ('investimento', 'custo', 'capacidade financeira'), "
            "growth recommendations, morning/EOD briefings, strategic priorities."
        ),
        max_turns=8,
        graph_topology="fanout",
        tags=["strategy", "analytics", "kpi", "growth", "synthesis", "cross-domain", "briefs"],
        skill_slugs=[
            "data_access", "sql_analytics", "analytics_charts",
            "insights_synthesis", "hidden_patterns",  # strategy_analysis removido — skill órfã (prompt deletado); ver BACKLOG_IDEAS.md
        ],
        frontdesk_visible=True,
    ),

    # ------------------------------------------------------------------
    # DocWriter — document creation and KB management
    # D4: hitl_approval removed from skill_slugs (it's middleware).
    # HITL is triggered via requires_confirmation in ToolRegistry.
    # ------------------------------------------------------------------
    "doc-writer": AgentTypeConfig(
        name="Document Writer",
        slug="doc-writer",
        description=(
            "Strategic document creation specialist. Searches the knowledge base, "
            "writes structured documents (briefs, SOPs, proposals, reports), "
            "exports to Google Docs and Sheets, and persists approved content "
            "to the knowledge base. Triggered by requests to write, draft, or create documents."
        ),
        prompt_name="agents/doc-writer",
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.POWERFUL,
        routing_hint="Document writing, drafting briefs, SOPs, proposals, reports with visualisations.",
        max_turns=8,
        tags=["documents", "writing", "drafts", "briefs", "sops", "proposals", "knowledge-base"],
        skill_slugs=[
            "data_access", "knowledge_base_write",
            "document_io", "document_curation", "notion",
        ],
        frontdesk_visible=True,
    ),

    # ------------------------------------------------------------------
    # Context Gatherer — background agent; is_frontdesk=False
    # Triggered by: rotina diária + webhook onboarding_complete + webhook doc_ingested
    # Responsibilities: schema mapping, document ingestion, KB curation.
    # Does NOT register transactions (data-entry owns writes; D3).
    # ------------------------------------------------------------------
    "context-gatherer": AgentTypeConfig(
        name="Context Gatherer",
        slug="context-gatherer",
        description=(
            "Background context collection agent. Maps client data sources to the "
            "platform schema, processes ingested documents (OCR, extraction, summarisation), "
            "and persists structured context to the knowledge base. "
            "Runs on schedule and via triggers (onboarding_complete, doc_ingested). "
            "Not a frontdesk agent — operates as a background system process."
        ),
        prompt_name="agents/context-gatherer",
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.DEFAULT,
        routing_hint="",  # not frontdesk-visible; no routing hint needed
        max_turns=8,
        memory_mode="none",  # stateless per trigger run
        tags=["context", "mapping", "ingest", "knowledge", "background", "schema"],
        skill_slugs=[
            "data_access", "sql_analytics",
            "knowledge_base_write", "onboarding", "document_curation",
        ],
        frontdesk_visible=False,  # background agent — not exposed in chat rooms
    ),

    # ------------------------------------------------------------------
    # FiscalAgent — NF-e / NFS-e issuance (ENTERPRISE, stub)
    # Candidate to merge into financeiro post-MVP (tracked in PANORAMA).
    # ------------------------------------------------------------------
    "fiscal-agent": AgentTypeConfig(
        name="Fiscal Agent",
        slug="fiscal-agent",
        description=(
            "NF-e and NFS-e issuance specialist. Issues invoices, queries fiscal "
            "status, and validates fiscal data against SEFAZ. "
            "Requires NF-e/NFS-e integration (SEFAZ partner). "
            "Post-MVP candidate to merge into financeiro."
        ),
        prompt_name="agents/fiscal-agent",
        tier_required=TierLevel.BASIC,
        model_tier=ModelTier.DEFAULT,
        routing_hint="Invoice issuance, NF-e, NFS-e, fiscal compliance, SEFAZ.",
        max_turns=4,
        tags=["fiscal", "nfe", "nfse", "invoice", "sefaz", "tax"],
        skill_slugs=["fiscal", "data_access", "sql_analytics"],
        frontdesk_visible=True,  # exposed so frontdesk routes NF-e/NFS-e requests correctly
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
        comparison so "sme", " SME " and "SME" are equivalent.
        """
        normalised = tier.strip().upper() if isinstance(tier, str) else ""
        try:
            tier_order = TierLevel.get_order(normalised)
        except ValueError:
            logger.warning(
                "[AgentTypeRegistry] Unknown tier %r — falling back to BASIC.",
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
    def get_by_tag(cls, tag: str) -> list[AgentTypeConfig]:
        """Return all agent configs that include *tag* in their tags list."""
        return [cfg for cfg in _AGENT_TYPES.values() if tag in cfg.tags]

    @classmethod
    def validate(cls, skill_registry: set[str] | None = None) -> list[str]:
        """
        Validate registry integrity.  Returns a list of error strings (empty = ok).

        Checks:
          - All skill_slugs reference known SKILL_REGISTRY keys (when skill_registry given).
          - All agents with frontdesk_visible=True have a non-empty routing_hint.
          - No agent has both enabled_tools and skill_slugs populated (ambiguity).
          - delegates_to references must exist in the registry.
        """
        from blu_agent_framework.skills import SKILL_REGISTRY  # noqa: PLC0415

        known_skills = skill_registry if skill_registry is not None else set(SKILL_REGISTRY.keys())
        errors: list[str] = []

        for cfg in _AGENT_TYPES.values():
            # Unknown skill slugs
            for sk in cfg.skill_slugs:
                if sk not in known_skills:
                    errors.append(f"{cfg.slug}: unknown skill_slug '{sk}'")

            # Visible agents must have routing hints
            if cfg.frontdesk_visible and not cfg.routing_hint:
                errors.append(f"{cfg.slug}: frontdesk_visible=True but routing_hint is empty")

            # Ambiguous tool resolution: both enabled_tools and skill_slugs populated
            if cfg.enabled_tools and cfg.skill_slugs and cfg.slug != "frontdesk":
                errors.append(
                    f"{cfg.slug}: has both enabled_tools and skill_slugs — "
                    "remove enabled_tools or migrate to skills-only"
                )

            # delegates_to must reference known slugs
            for dep in cfg.delegates_to:
                if dep not in _AGENT_TYPES:
                    errors.append(f"{cfg.slug}: delegates_to references unknown slug '{dep}'")

        return errors

    @classmethod
    def build_catalog(cls, format: str = "frontdesk", lang: str = "pt") -> str:
        """
        Build the agent catalog string for injection into system prompts.

        Args:
            format: "frontdesk" (PT-BR bullets for frontdesk prompt) or
                    "supervisor" (EN tool-call list for supervisor prompt).
            lang:   "pt" or "en" — controls the section header language.
                    Ignored in "supervisor" format (always EN).

        Returns:
            Formatted multi-line string.
        """
        if format == "supervisor":
            return cls._build_supervisor_catalog()
        return cls._build_frontdesk_catalog()

    @classmethod
    def _build_frontdesk_catalog(cls) -> str:
        lines: list[str] = []
        for cfg in _AGENT_TYPES.values():
            if not cfg.frontdesk_visible:
                continue
            lines.append(f"- `{cfg.slug}` — {cfg.description}")
            if cfg.routing_hint:
                lines.append(f"  Quando usar: {cfg.routing_hint}")
        if not lines:
            return "Nenhum especialista disponível no momento."
        return "\n".join(lines)

    @classmethod
    def _build_supervisor_catalog(cls) -> str:
        lines: list[str] = []
        for cfg in _AGENT_TYPES.values():
            tool_name = f"delegate_to_{cfg.slug.replace('-', '_')}"
            lines.append(f"- `{tool_name}`: {cfg.description}")
            if cfg.routing_hint:
                lines.append(f"  Use for: {cfg.routing_hint}")
            if cfg.delegates_to:
                lines.append(f"  Note: internally delegates to {cfg.delegates_to} — do not double-delegate.")
        if not lines:
            return "No specialist workers available."
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Backward-compat aliases
    # ------------------------------------------------------------------

    @classmethod
    def build_frontdesk_catalog(cls) -> str:
        """Deprecated: use build_catalog(format='frontdesk') instead."""
        return cls._build_frontdesk_catalog()

    @classmethod
    def build_supervisor_description(cls, tier: str) -> str:
        """Deprecated: use build_catalog(format='supervisor') instead."""
        return cls._build_supervisor_catalog()
