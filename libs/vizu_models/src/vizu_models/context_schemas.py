# libs/vizu_models/src/vizu_models/context_schemas.py
"""
JSON schemas for context section content (Context 2.0).

These define the structure of each section's JSONB content.
Used for validation, documentation, and type hints.

Each schema corresponds to a ContextSection enum value and defines
the expected structure when storing/retrieving that section.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# CORE IDENTITY SECTIONS (Quarterly updates)
# =============================================================================


class CompanyProfile(BaseModel):
    """
    Section: COMPANY_PROFILE - Who we are and where we're going.

    Contains the fundamental identity of the company that rarely changes.
    Used by all agents to understand the company's purpose and positioning.
    """

    # Basic Identity
    legal_name: str | None = Field(None, description="Razão social")
    trading_name: str | None = Field(None, description="Nome fantasia")
    tagline: str | None = Field(None, description="Slogan ou frase de efeito")

    # Business Classification
    business_archetype: str | None = Field(
        None,
        description="e.g., 'B2B SaaS', 'E-commerce', 'Environmental Services'",
    )
    industry: str | None = Field(None, description="Setor de atuação")

    # Purpose
    mission: str | None = Field(None, description="Missão da empresa")
    vision: str | None = Field(None, description="Visão de futuro")
    core_values: list[str] = Field(
        default_factory=list,
        description="Valores fundamentais com descrições curtas",
    )

    # Company Info
    founding_year: int | None = None
    headquarters_city: str | None = None
    employee_count_range: str | None = Field(
        None,
        description="e.g., '1-10', '11-50', '51-200', '201-500', '500+'",
    )


class BrandVoice(BaseModel):
    """
    Section: BRAND_VOICE - How we communicate.

    Defines the communication style and personality for all AI interactions.
    Critical for respond nodes to maintain brand consistency.
    """

    # Tone & Style
    tone: str | None = Field(
        None,
        description="e.g., 'profissional mas acessível', 'técnico e preciso'",
    )
    personality_traits: list[str] = Field(
        default_factory=list,
        description="e.g., ['inovador', 'confiável', 'parceiro']",
    )

    # Language Settings
    language: str = Field(default="pt-BR", description="Primary language code")
    formality_level: str | None = Field(
        None,
        description="'formal', 'semi-formal', 'casual'",
    )

    # Vocabulary Control
    key_phrases_to_use: list[str] = Field(
        default_factory=list,
        description="Phrases that reinforce brand identity",
    )
    phrases_to_avoid: list[str] = Field(
        default_factory=list,
        description="Phrases that damage brand (e.g., greenwashing terms)",
    )
    preferred_terms: list[str] = Field(
        default_factory=list,
        description="Technical terms the brand prefers",
    )

    # Guidelines
    communication_guidelines: str | None = Field(
        None,
        description="Free-form guidelines for AI responses",
    )


# =============================================================================
# OPERATIONS SECTIONS (Weekly updates)
# =============================================================================


class CurrentMoment(BaseModel):
    """
    Section: CURRENT_MOMENT - What we're focusing on NOW.

    This is the most dynamic section, updated weekly or more frequently.
    Critical for agents to understand current priorities and context.
    """

    # Company Stage
    stage: str | None = Field(
        None,
        description="'startup', 'growth', 'scaling', 'maturity'",
    )

    # Current Focus
    current_priorities: list[str] = Field(
        default_factory=list,
        description="Top 3-5 priorities right now",
    )
    current_challenges: list[str] = Field(
        default_factory=list,
        description="Main obstacles being faced",
    )
    recent_wins: list[str] = Field(
        default_factory=list,
        description="Recent achievements to celebrate",
    )

    # Metrics (non-sensitive aggregates only)
    key_metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Current KPIs (e.g., {'mrr_growth': '15% MoM', 'nps': 72})",
    )

    # Activities
    active_campaigns: list[str] = Field(
        default_factory=list,
        description="Marketing/sales campaigns in progress",
    )
    upcoming_events: list[str] = Field(
        default_factory=list,
        description="Events, launches, deadlines",
    )

    # Timing
    period: str | None = Field(
        None,
        description="Period this moment refers to (e.g., 'Q4 2024', '2024-W04')",
    )
    last_updated: str | None = Field(
        None,
        description="When this was last updated (ISO date)",
    )


class TeamMember(BaseModel):
    """Key team member for context."""

    role: str
    name: str | None = None
    responsibility: str | None = Field(None, description="What they handle")
    contact_preference: str | None = Field(
        None,
        description="e.g., 'Slack para urgências, email para formal'",
    )


class TeamStructure(BaseModel):
    """
    Section: TEAM_STRUCTURE - Who to contact.

    Provides contact information and escalation paths.
    """

    key_contacts: list[TeamMember] = Field(default_factory=list)
    main_contact: str | None = Field(
        None,
        description="Primary contact name and role",
    )
    escalation_path: list[str] = Field(
        default_factory=list,
        description="Who to escalate to and when",
    )
    communication_channels: dict[str, str] = Field(
        default_factory=dict,
        description="e.g., {'urgent': 'Slack', 'formal': 'email'}",
    )

    # Location
    headquarters: str | None = None
    operational_locations: list[str] = Field(default_factory=list)
    business_hours: str | None = Field(
        None,
        description="e.g., 'Seg-Sex 8h-18h (BRT)'",
    )


class Policies(BaseModel):
    """
    Section: POLICIES - Rules and guardrails.

    Defines what agents can and cannot do, and communication rules.
    """

    # Communication Rules
    communication_rules: list[str] = Field(
        default_factory=list,
        description="What to say/not say",
    )
    tone_with_partners: str | None = Field(
        None,
        description="Special tone for partners/suppliers",
    )

    # Operational Limits
    operational_limits: list[str] = Field(
        default_factory=list,
        description="What actions are restricted",
    )

    # Approval Workflows
    approval_requirements: dict[str, list[str]] = Field(
        default_factory=dict,
        description="{'autonomous': [...], 'requires_approval': [...]}",
    )

    # Risk Management
    red_flags: list[str] = Field(
        default_factory=list,
        description="Situations that should trigger alerts",
    )

    # Compliance
    compliance_notes: str | None = None
    data_handling_rules: list[str] = Field(default_factory=list)


# =============================================================================
# TECHNICAL SECTIONS (On-change updates)
# =============================================================================


class TableSchemaInfo(BaseModel):
    """
    Detailed schema information for a single table.

    Used by SQL agents to understand table structure and generate queries.
    Populated from sql_table_config entries.
    """

    table_name: str = Field(..., description="Full table name (e.g., analytics_v2.fact_sales)")
    display_name: str | None = Field(None, description="Human-readable name")
    description: str | None = Field(None, description="What this table contains")
    is_primary: bool = Field(False, description="Primary table for queries (fact table)")

    # Column information
    columns: dict[str, str] = Field(
        default_factory=dict,
        description="Column name → description mapping",
    )

    # Enum/valid values for categorical columns
    enum_values: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Column name → list of valid values (case-sensitive)",
    )

    # Example queries for this table
    example_queries: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of {'question': ..., 'sql': ...} examples",
    )

    # Join hints
    join_keys: list[str] = Field(
        default_factory=list,
        description="Primary/foreign keys for joins (e.g., 'customer_id', 'supplier_id')",
    )


class DataSchema(BaseModel):
    """
    Section: DATA_SCHEMA - What data is available.

    Describes available data for SQL/RAG agents.
    Now includes detailed table schemas for SQL generation.
    """

    available_tables: list[str] = Field(default_factory=list)
    key_fields: dict[str, str] = Field(
        default_factory=dict,
        description="Field name → description mapping",
    )
    data_formats: dict[str, str] = Field(
        default_factory=dict,
        description="e.g., {'dates': 'DD/MM/YYYY', 'currency': 'BRL'}",
    )
    data_freshness: str | None = Field(
        None,
        description="How often data is updated",
    )
    data_sources: list[str] = Field(
        default_factory=list,
        description="Where data comes from (BigQuery, internal, etc.)",
    )

    # NEW: Detailed table schemas for SQL generation
    table_schemas: list[TableSchemaInfo] = Field(
        default_factory=list,
        description="Detailed schema information from sql_table_config",
    )


class AvailableTools(BaseModel):
    """
    Section: AVAILABLE_TOOLS - What the AI can do.

    Describes tool capabilities and limits for init/routing nodes.
    """

    tier: str = "BASIC"
    enabled_tool_names: list[str] = Field(default_factory=list)
    tool_descriptions: dict[str, str] = Field(
        default_factory=dict,
        description="Tool name → description",
    )

    # Permissions
    autonomous_actions: list[str] = Field(
        default_factory=list,
        description="Actions AI can take without approval",
    )
    restricted_actions: list[str] = Field(
        default_factory=list,
        description="Actions that require human approval",
    )

    # Limits
    usage_limits: dict[str, Any] = Field(
        default_factory=dict,
        description="Rate limits, quotas, etc.",
    )

    # Default prompt
    default_system_prompt: str | None = Field(
        None,
        description="Default instruction for all agents of this client",
    )


# =============================================================================
# SCHEMA REGISTRY
# =============================================================================

# Mapping from section type string to schema class
SECTION_SCHEMAS: dict[str, type[BaseModel]] = {
    "company_profile": CompanyProfile,
    "brand_voice": BrandVoice,
    "current_moment": CurrentMoment,
    "team_structure": TeamStructure,
    "policies": Policies,
    "data_schema": DataSchema,
    "available_tools": AvailableTools,
}


def get_section_schema(section_type: str) -> type[BaseModel] | None:
    """Get the Pydantic schema class for a section type."""
    return SECTION_SCHEMAS.get(section_type)


def validate_section_content(section_type: str, content: dict) -> BaseModel:
    """
    Validate content against its section schema.

    Args:
        section_type: The section type (e.g., 'company_profile')
        content: The content dict to validate

    Returns:
        Validated Pydantic model instance

    Raises:
        ValueError: If section type is unknown
        ValidationError: If content doesn't match schema
    """
    schema_class = SECTION_SCHEMAS.get(section_type)
    if schema_class is None:
        raise ValueError(f"Unknown section type: {section_type}")
    return schema_class.model_validate(content)
