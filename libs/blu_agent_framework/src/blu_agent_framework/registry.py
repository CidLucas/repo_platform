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
    # fragment list passed to compose_prompt(); ignored when prompt_name is set
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
    # Data Analyst — SQL + CSV analytics
    # ------------------------------------------------------------------
    "data-analyst": AgentTypeConfig(
        name="Data Analyst",
        slug="data-analyst",
        description=(
            "Analyses structured data by generating and executing SQL queries on "
            "the client's analytics database. Use for revenue, rankings, trends, "
            "aggregations, comparisons, and any question about business metrics."
        ),
        enabled_tools=[
            "execute_sql",
            "execute_csv_query",
            "list_csv_datasets",
            "peek_csv_columns",
            "get_knowledge_status",
        ],
        fragments=[
            "fragment/standalone-base",
            "fragment/sql-schema",
            "fragment/sql-rules",
            "fragment/sql-examples",
            "fragment/fallback-strategy",
            "fragment/data-analyst-workflow",
            "fragment/standalone-response",
        ],
        tier_required=TierLevel.SME,
        routing_hint="Questions about numbers, totals, rankings, revenue, suppliers, clients, products.",
        max_turns=3,
        tags=["analytics", "sql", "csv"],
    ),
    # ------------------------------------------------------------------
    # Knowledge Assistant — RAG search
    # ------------------------------------------------------------------
    "knowledge-assistant": AgentTypeConfig(
        name="Knowledge Assistant",
        slug="knowledge-assistant",
        description=(
            "Searches the client's knowledge base (RAG) to answer questions "
            "about policies, processes, company information, and documents."
        ),
        enabled_tools=[
            "executar_rag_cliente",
            "get_knowledge_status",
        ],
        fragments=[
            "fragment/standalone-base",
            "fragment/rag-search",
            "fragment/knowledge-assistant-workflow",
            "fragment/standalone-response",
        ],
        tier_required=TierLevel.BASIC,
        routing_hint="Questions about policies, processes, company info, documentation, how-to.",
        max_turns=3,
        tags=["rag", "knowledge-base", "search"],
    ),
    # ------------------------------------------------------------------
    # Report Generator — SQL + RAG + Google Sheets export
    # ------------------------------------------------------------------
    "report-generator": AgentTypeConfig(
        name="Report Generator",
        slug="report-generator",
        description=(
            "Combines data analysis and knowledge to produce comprehensive reports. "
            "Can query SQL, search RAG, and export results to Google Sheets/Docs."
        ),
        enabled_tools=[
            "executar_sql_agent",
            "executar_rag_cliente",
            "execute_csv_query",
            "list_csv_datasets",
            "peek_csv_columns",
            "write_to_sheet",
            "export_to_sheet",
            "create_spreadsheet_with_data",
            "google_docs_create",
            "google_docs_write",
            "get_knowledge_status",
        ],
        fragments=[
            "fragment/standalone-base",
            "fragment/csv-tools",
            "fragment/rag-search",
            "fragment/google-export",
            "fragment/report-generator-workflow",
            "fragment/standalone-response",
        ],
        tier_required=TierLevel.SME,
        routing_hint="Requests for reports, exports, combined data+knowledge analyses.",
        max_turns=4,
        tags=["analytics", "rag", "google", "report"],
    ),
    # ------------------------------------------------------------------
    # Document Intelligence — OCR + extraction + time-series
    # ------------------------------------------------------------------
    "document-intelligence": AgentTypeConfig(
        name="Document Intelligence",
        slug="document-intelligence",
        description=(
            "Extracts text, tables, and structured data from uploaded documents "
            "using OCR. Compiles time series and saves summaries to the knowledge base."
        ),
        enabled_tools=[
            "extract_document_with_ocr",
            "summarize_document_sections",
            "extract_structured_data",
            "compile_time_series",
            "write_summary_to_kb",
            "executar_rag_cliente",
        ],
        fragments=[
            "fragment/standalone-base",
            "fragment/rag-search",
            "fragment/document-intelligence-tools",
            "fragment/document-intelligence-workflow",
            "fragment/standalone-response",
        ],
        tier_required=TierLevel.SME,
        routing_hint="Requests involving uploaded documents, OCR, extraction, time-series compilation.",
        max_turns=4,
        tags=["ocr", "documents", "extraction"],
    ),
    # ------------------------------------------------------------------
    # Customer Support — routine management (no fragments; uses a named prompt)
    # ------------------------------------------------------------------
    "customer-support": AgentTypeConfig(
        name="Customer Support",
        slug="customer-support",
        description=(
            "Helps users manage their automation routines: lists catalog and custom "
            "routines, creates new custom routines step-by-step, activates catalog "
            "routines, and submits drafts for approval."
        ),
        enabled_tools=[
            "listar_rotinas_catalogo",
            "listar_rotinas_personalizadas",
            "criar_rotina_personalizada",
            "ativar_rotina_catalogo",
            "enviar_rotina_para_aprovacao",
        ],
        prompt_name="agents/customer-support",
        tier_required=TierLevel.BASIC,
        routing_hint=(
            "Requests about creating, listing, activating, or managing automation "
            "routines. Rotinas, automações, criar rotina, ativar rotina."
        ),
        max_turns=5,
        tags=["routines", "automation", "support"],
    ),
    # ------------------------------------------------------------------
    # RFQ Agent — full procurement cycle
    # ------------------------------------------------------------------
    "rfq-agent": AgentTypeConfig(
        name="Procurement / RFQ Agent",
        slug="rfq-agent",
        description=(
            "Handles the full procurement cycle: parses buying lists, manages the "
            "supplier roster, dispatches RFQs to multiple suppliers, collects and "
            "compares quotes, optimises allocation across suppliers with concentration "
            "caps, generates purchase orders, and exports results to Google Sheets."
        ),
        enabled_tools=[
            "parse_buying_list",
            "validate_buying_list",
            "list_suppliers",
            "add_supplier",
            "update_supplier",
            "remove_supplier",
            "dispatch_rfq",
            "dispatch_rfq_whatsapp",
            "check_rfq_responses",
            "submit_mock_response",
            "parse_supplier_reply",
            "suggest_counter_offer",
            "optimize_allocation",
            "generate_po_report",
            "create_purchase_order",
            "approve_purchase_order",
            "import_buying_list_from_sheets",
            "export_po_to_sheets",
        ],
        fragments=[
            "fragment/standalone-base",
            "fragment/rfq-orchestrator",
            "fragment/rfq-supplier-liaison",
            "fragment/rfq-optimizer",
            "fragment/rfq-report-composer",
            "fragment/google-export",
            "fragment/standalone-response",
        ],
        tier_required=TierLevel.BASIC,
        routing_hint=(
            "Buying lists, purchasing, quotations, supplier management, RFQs, "
            "purchase orders, procurement, cotações, compras, fornecedores."
        ),
        max_turns=6,
        on_max_turns="raise",  # Transactional: partial dispatch is invalid
        tags=["rfq", "procurement", "dispatch"],
    ),
    # ------------------------------------------------------------------
    # Config Helper — onboarding / configuration assistant
    # Only in standalone_agent_api today; added here for Phase 5 parity.
    # ------------------------------------------------------------------
    "config-helper": AgentTypeConfig(
        name="Configuration Assistant",
        slug="config-helper",
        description=(
            "Guides users through account setup, integration configuration, and "
            "onboarding workflows."
        ),
        enabled_tools=[],  # config tools TBD
        fragments=[
            "fragment/standalone-base",
            "fragment/config-helper-workflow",
            "fragment/standalone-response",
        ],
        tier_required=TierLevel.BASIC,
        routing_hint="Account setup, integration configuration, onboarding.",
        max_turns=5,
        tags=["config", "onboarding", "setup"],
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
