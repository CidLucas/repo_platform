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
            "strategies. Used in routines for reengagement campaigns and follow-ups."
        ),
        prompt_name="agents/frontdesk",
        enabled_tools=[
            "executar_rag_cliente",
            "execute_sql",
        ],
        tier_required=TierLevel.BASIC,
        routing_hint="Writing client emails, personalised outreach, CRM campaigns.",
        max_turns=5,
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
        prompt_name="agents/frontdesk",
        enabled_tools=[
            "executar_rag_cliente",
            "execute_sql",
        ],
        tier_required=TierLevel.BASIC,
        routing_hint="Strategic analysis, business performance reviews, growth recommendations.",
        max_turns=5,
        tags=["strategy", "analytics", "kpi", "growth"],
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
        routing_hint="Follow-up scheduling, client contact prioritisation, calendar planning.",
        max_turns=5,
        tags=["scheduling", "follow-up", "calendar", "clients"],
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
        routing_hint="Document search, knowledge base digests, content gap analysis.",
        max_turns=5,
        tags=["documents", "knowledge-base", "rag", "digest"],
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
        """Return all agent types accessible at *tier*."""
        tier_order = TierLevel.get_order(tier)
        result = [
            cfg for cfg in _AGENT_TYPES.values()
            if TierLevel.get_order(cfg.tier_required.value) <= tier_order
        ]
        logger.debug(
            "[AgentTypeRegistry] Available for tier %s: %s",
            tier, [c.slug for c in result],
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
