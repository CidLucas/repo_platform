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
            "Execute DuckDB SQL queries on uploaded CSV datasets and return "
            "structured results (tables, aggregates, trends)."
        ),
        required_tool_names=[
            "list_csv_datasets",
            "peek_csv_columns",
            "execute_csv_query",
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
    # RFQ / Procurement
    # ------------------------------------------------------------------
    "generate_rfq": SkillDefinition(
        name="generate_rfq",
        description=(
            "Parse a buying list, validate it, select suppliers, and dispatch "
            "RFQ requests. Transactional — partial output is invalid."
        ),
        required_tool_names=[
            "parse_buying_list",
            "validate_buying_list",
            "list_suppliers",
            "dispatch_rfq",
            "check_rfq_responses",
        ],
        prompt_name="skill:generate_rfq:system",
        max_turns=6,
        on_max_turns="raise",  # Transactional: all suppliers must be dispatched
        tags=["rfq", "procurement", "dispatch"],
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
    # ------------------------------------------------------------------
    # Report generation (multi-source)
    # ------------------------------------------------------------------
    "generate_report": SkillDefinition(
        name="generate_report",
        description=(
            "Build an executive report by combining CSV data, knowledge-base "
            "context, and optionally exporting to Google Sheets."
        ),
        required_tool_names=[
            "list_csv_datasets",
            "execute_csv_query",
            "executar_rag_cliente",
            "create_spreadsheet_with_data",
            "write_to_sheet",
        ],
        prompt_name="skill:generate_report:system",
        max_turns=6,
        on_max_turns="return_partial",
        tags=["analytics", "rag", "google", "report"],
    ),
}
