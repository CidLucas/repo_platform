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
    print(skill.prompt_name)   # "skill:analyze_csv:system"
    print(skill.required_tool_names)
"""

from __future__ import annotations

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
# Skill Registry — top-6 skills covering the main standalone-agent domains
# =============================================================================
#
# prompt_name follows the convention "skill:{name}:system"; those prompts are
# stored in Langfuse under label="production" and fetched by SkillFactory via
# blu_prompt_management.get_prompt_loader().load(skill.prompt_name).
#
# required_tool_names must be a subset of the agent's own enabled_tools;
# SkillFactory intersects them at runtime so an agent without CSV access cannot
# accidentally run the analyze_csv skill.

SKILL_REGISTRY: dict[str, SkillDefinition] = {
    # ------------------------------------------------------------------
    # CSV / Analytics
    # ------------------------------------------------------------------
    "analyze_csv": SkillDefinition(
        name="analyze_csv",
        description=(
            "Execute SQL queries on uploaded CSV datasets and return "
            "structured results (tables, aggregates, trends)."
        ),
        required_tool_names=[
            "peek_csv_columns",
        ],
        prompt_name="skill:analyze_csv:system",
        max_turns=5,
        on_max_turns="return_partial",
        tags=["analytics", "csv", "sql"],
    ),
    # ------------------------------------------------------------------
    # RAG / Knowledge
    # ------------------------------------------------------------------
    "rag_search": SkillDefinition(
        name="rag_search",
        description=(
            "Search the client knowledge base via vector similarity and "
            "synthesise an answer from the retrieved passages."
        ),
        required_tool_names=["executar_rag_cliente"],
        prompt_name="skill:rag_search:system",
        max_turns=3,
        on_max_turns="return_partial",
        tags=["rag", "knowledge-base", "search"],
    ),
    # ------------------------------------------------------------------
    # Document Intelligence / OCR
    # ------------------------------------------------------------------
    "extract_document": SkillDefinition(
        name="extract_document",
        description=(
            "Extract text, tables, and structured fields from uploaded documents "
            "using OCR; optionally summarise sections."
        ),
        required_tool_names=[
            "extract_document_with_ocr",
            "summarize_document_sections",
            "extract_structured_data",
        ],
        prompt_name="skill:extract_document:system",
        max_turns=4,
        on_max_turns="return_partial",
        tags=["ocr", "documents", "extraction"],
    ),
    # ------------------------------------------------------------------
    # Knowledge-base persistence
    # ------------------------------------------------------------------
    "write_to_kb": SkillDefinition(
        name="write_to_kb",
        description=(
            "Save an analysis result, extracted data, or summary to the client "
            "knowledge base for future retrieval."
        ),
        required_tool_names=["write_summary_to_kb"],
        prompt_name="skill:write_to_kb:system",
        max_turns=2,
        on_max_turns="return_partial",
        tags=["knowledge-base", "persistence", "documents"],
    ),
    # ==========================================================================
    # L3 Routine Skills — narrative generation for automated routines
    # These skills are called by the routine engine (step type "skill") and are
    # agent-agnostic: any agent can include them via its skill_slugs config.
    # ==========================================================================

    # ------------------------------------------------------------------
    # Morning Chain
    # ------------------------------------------------------------------
    "morning_plan": SkillDefinition(
        name="morning_plan",
        description=(
            "Generate a prioritised daily plan narrative from KPIs, calendar agenda, "
            "pending approvals, and integration alerts. Used by the morning_sync routine."
        ),
        required_tool_names=[],  # receives pre-fetched context from routine engine
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

    # ------------------------------------------------------------------
    # Financeiro
    # ------------------------------------------------------------------
    "reconciliation_report": SkillDefinition(
        name="reconciliation_report",
        description=(
            "Generate a monthly cash reconciliation narrative: spot anomalies in "
            "categories, highlight top merchants, and flag discrepancies."
        ),
        required_tool_names=[],
        prompt_name="skill:reconciliation_report:system",
        max_turns=3,
        on_max_turns="return_partial",
        tags=["routines", "finance", "reconciliation", "narrative"],
    ),

    # ------------------------------------------------------------------
    # Clientes
    # ------------------------------------------------------------------
    "collection_messages": SkillDefinition(
        name="collection_messages",
        description=(
            "Draft personalised collection messages for overdue customers, adapting "
            "tone by days overdue (friendly / firm / urgent)."
        ),
        required_tool_names=[],
        prompt_name="skill:collection_messages:system",
        max_turns=2,
        on_max_turns="return_partial",
        tags=["routines", "clients", "collection", "messages"],
    ),
    "followup_draft": SkillDefinition(
        name="followup_draft",
        description=(
            "Write a post-sale follow-up message for a specific customer, optionally "
            "including cross-sell suggestions based on purchase history."
        ),
        required_tool_names=[],
        prompt_name="skill:followup_draft:system",
        max_turns=2,
        on_max_turns="return_partial",
        tags=["routines", "clients", "followup", "sales"],
    ),
    "reactivation_proposal": SkillDefinition(
        name="reactivation_proposal",
        description=(
            "Compose a contextualised reactivation proposal for an inactive customer, "
            "referencing their purchase history and optionally including a special offer."
        ),
        required_tool_names=[],
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
        required_tool_names=[],
        prompt_name="skill:satisfaction_survey:system",
        max_turns=2,
        on_max_turns="return_partial",
        tags=["routines", "clients", "nps", "satisfaction"],
    ),

    # ------------------------------------------------------------------
    # Agenda / Reuniões
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Estratégia
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Monitor skills — domain-scoped health snapshots for monitor routines
    # ------------------------------------------------------------------
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
            "Generate a procurement and inventory digest: low-stock alerts, supplier delays, "
            "purchase order status, and cost anomalies. Used by compras_monitor routine."
        ),
        required_tool_names=[],
        prompt_name="skill:inventory_digest:system",
        max_turns=3,
        on_max_turns="return_partial",
        tags=["routines", "procurement", "monitor", "report", "alert"],
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
}