"""
Worker Registry — Maps worker types to configs for the supervisor.

Each worker is a specialized agent that the supervisor can delegate to
via meta-tools (delegate_to_*). The registry controls:
- Which workers exist and their descriptions (for the supervisor prompt)
- Which tools each worker needs
- Which prompt fragments compose the worker's system prompt
- Tier-gated availability (e.g., document-intelligence = SME+)
"""

import logging
from dataclasses import dataclass, field

from vizu_tool_registry.tool_metadata import TierLevel

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkerConfig:
    """Configuration for a single worker agent."""

    name: str
    slug: str
    description: str  # Shown to supervisor LLM for routing decisions
    agent_slug: str  # Maps to AGENT_FRAGMENTS key in standalone factory
    enabled_tools: list[str] = field(default_factory=list)
    fragments: list[str] = field(default_factory=list)
    tier_required: TierLevel = TierLevel.BASIC
    routing_hint: str = ""  # Extra hint for the supervisor on when to use


# ---------------------------------------------------------------------------
# Worker definitions
# ---------------------------------------------------------------------------

_WORKERS: dict[str, WorkerConfig] = {
    "data-analyst": WorkerConfig(
        name="Data Analyst",
        slug="data-analyst",
        description=(
            "Analyses structured data by generating and executing SQL queries on "
            "the client's analytics database. Use for revenue, rankings, trends, "
            "aggregations, comparisons, and any question about business metrics."
        ),
        agent_slug="data-analyst",
        enabled_tools=[
            "execute_sql",
            "executar_sql_agent",
            "execute_csv_query",
            "list_csv_datasets",
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
    ),
    "knowledge-assistant": WorkerConfig(
        name="Knowledge Assistant",
        slug="knowledge-assistant",
        description=(
            "Searches the client's knowledge base (RAG) to answer questions "
            "about policies, processes, company information, and documents."
        ),
        agent_slug="knowledge-assistant",
        enabled_tools=[
            "executar_rag_cliente",
        ],
        fragments=[
            "fragment/standalone-base",
            "fragment/rag-search",
            "fragment/rag-rules",
            "fragment/knowledge-assistant-workflow",
            "fragment/standalone-response",
        ],
        tier_required=TierLevel.BASIC,
        routing_hint="Questions about policies, processes, company info, documentation, how-to.",
    ),
    "report-generator": WorkerConfig(
        name="Report Generator",
        slug="report-generator",
        description=(
            "Combines data analysis and knowledge to produce comprehensive reports. "
            "Can query SQL, search RAG, and export results to Google Sheets/Docs."
        ),
        agent_slug="report-generator",
        enabled_tools=[
            "execute_sql",
            "executar_sql_agent",
            "executar_rag_cliente",
            "execute_csv_query",
            "list_csv_datasets",
            "write_to_sheet",
            "export_to_sheet",
            "create_spreadsheet_with_data",
            "google_docs_create",
            "google_docs_write",
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
    ),
    "document-intelligence": WorkerConfig(
        name="Document Intelligence",
        slug="document-intelligence",
        description=(
            "Extracts text, tables, and structured data from uploaded documents "
            "using OCR. Compiles time series and saves summaries to the knowledge base."
        ),
        agent_slug="document-intelligence",
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
    ),
}


class WorkerRegistry:
    """
    Central registry of worker agents available to the supervisor.

    Methods are classmethods so the registry can be used without instantiation,
    matching the ToolRegistry pattern.
    """

    @classmethod
    def get_worker(cls, slug: str) -> WorkerConfig | None:
        """Get a worker config by slug."""
        return _WORKERS.get(slug)

    @classmethod
    def get_all_workers(cls) -> dict[str, WorkerConfig]:
        """Get all registered workers."""
        return dict(_WORKERS)

    @classmethod
    def get_available_workers(cls, tier: str) -> list[WorkerConfig]:
        """
        Get workers accessible at a given tier level.

        Args:
            tier: Client tier string (e.g., "BASIC", "SME", "PREMIUM")

        Returns:
            List of WorkerConfig objects accessible at this tier
        """
        tier_order = TierLevel.get_order(tier)
        available = []
        for worker in _WORKERS.values():
            if TierLevel.get_order(worker.tier_required.value) <= tier_order:
                available.append(worker)
        logger.debug(
            f"[WorkerRegistry] Available workers for tier {tier}: "
            f"{[w.slug for w in available]}"
        )
        return available

    @classmethod
    def build_workers_description(cls, tier: str) -> str:
        """
        Build a formatted description of available workers for the supervisor prompt.

        Args:
            tier: Client tier for filtering

        Returns:
            Markdown-formatted worker list for {{ workers_description }}
        """
        workers = cls.get_available_workers(tier)
        if not workers:
            return "No specialist workers available."

        lines = []
        for w in workers:
            lines.append(f"- **{w.name}** (`delegate_to_{w.slug.replace('-', '_')}`): {w.description}")
            if w.routing_hint:
                lines.append(f"  _When to use:_ {w.routing_hint}")
        return "\n".join(lines)
