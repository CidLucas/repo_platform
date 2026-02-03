# vizu_models/safe_client_context.py
"""
SafeClientContext - Modular context safe for LLM exposure (Context 2.0).

Contains ONLY data safe for LLM exposure. No sensitive information
(API keys, internal IDs, credentials) should be here.

IMPORTANT: Any data in this model may be included in prompts or LLM responses.

Context 2.0 Features:
- Modular sections that can be loaded/injected independently
- Selective injection based on node requirements
- Immutable to prevent accidental modifications
"""

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .enums import ContextSection, TierCliente
from .context_schemas import (
    AvailableTools,
    BrandVoice,
    CompanyProfile,
    CurrentMoment,
    DataSchema,
    Policies,
    TeamStructure,
    SECTION_SCHEMAS,
)


class SafeClientContext(BaseModel):
    """
    Modular client context safe for LLM exposure (Context 2.0).

    Sections can be loaded independently and compiled into prompt text selectively.

    NÃO INCLUIR:
    - api_key / credenciais
    - IDs internos (UUIDs)
    - dados financeiros detalhados
    - qualquer dado para impersonação

    Usage:
        # Get all loaded context as formatted text
        context.get_compiled_context()

        # Get only specific sections
        context.get_compiled_context([
            ContextSection.BRAND_VOICE,
            ContextSection.CURRENT_MOMENT,
        ])
    """

    model_config = ConfigDict(frozen=True)

    # ===== BASIC IDENTITY (always available) =====
    nome_empresa: str
    tier: str = "BASIC"
    enabled_tools: list[str] = Field(default_factory=list)

    # ===== MODULAR SECTIONS (Context 2.0) =====
    company_profile: CompanyProfile | None = None
    brand_voice: BrandVoice | None = None
    current_moment: CurrentMoment | None = None
    team_structure: TeamStructure | None = None
    policies: Policies | None = None
    data_schema: DataSchema | None = None
    available_tools_config: AvailableTools | None = None

    # ===== METADATA =====
    loaded_sections: list[ContextSection] = Field(default_factory=list)

    def get_section(self, section: ContextSection) -> BaseModel | dict | None:
        """Get a specific section by type."""
        section_map = {
            ContextSection.COMPANY_PROFILE: self.company_profile,
            ContextSection.BRAND_VOICE: self.brand_voice,
            ContextSection.CURRENT_MOMENT: self.current_moment,
            ContextSection.TEAM_STRUCTURE: self.team_structure,
            ContextSection.POLICIES: self.policies,
            ContextSection.DATA_SCHEMA: self.data_schema,
            ContextSection.AVAILABLE_TOOLS: self.available_tools_config,
        }
        return section_map.get(section)

    def has_section(self, section: ContextSection) -> bool:
        """Check if a section is loaded."""
        return section in self.loaded_sections and self.get_section(section) is not None

    def get_compiled_context(
        self,
        sections: list[ContextSection] | None = None,
        include_header: bool = True,
    ) -> str:
        """
        Compile context sections into formatted text for LLM injection.

        Args:
            sections: Specific sections to include. If None, uses loaded_sections.
            include_header: Whether to include company name header.

        Returns:
            Formatted context string ready for prompt injection.
        """
        if sections is None:
            sections = self.loaded_sections if self.loaded_sections else []

        parts = []

        if include_header:
            parts.append(f"# Context: {self.nome_empresa}")
            parts.append(f"**Service Tier:** {self.tier}")

        # Compile each requested section
        for section in sections:
            content = self.get_section(section)
            if content is None:
                continue

            section_text = self._format_section(section, content)
            if section_text:
                parts.append(section_text)

        return "\n\n".join(parts)

    def _format_section(self, section: ContextSection, content: Any) -> str:
        """Format a single section for prompt injection."""
        if content is None:
            return ""

        # Section headers in English
        headers = {
            ContextSection.COMPANY_PROFILE: "## Company Profile",
            ContextSection.BRAND_VOICE: "## Brand Voice & Communication",
            ContextSection.CURRENT_MOMENT: "## Current Business Context",
            ContextSection.TEAM_STRUCTURE: "## Team & Operations",
            ContextSection.POLICIES: "## Policies & Boundaries",
            ContextSection.DATA_SCHEMA: "## Available Data",
            ContextSection.AVAILABLE_TOOLS: "## Tool Configuration",
        }

        header = headers.get(section, f"## {section.value}")

        # Convert to dict if Pydantic model
        if isinstance(content, BaseModel):
            content_dict = content.model_dump(exclude_none=True, exclude_defaults=True)
        else:
            content_dict = content

        if not content_dict:
            return ""

        # Special handling for DATA_SCHEMA with table_schemas
        if section == ContextSection.DATA_SCHEMA and "table_schemas" in content_dict:
            return self._format_data_schema_section(header, content_dict)

        lines = [header]
        self._format_dict_to_lines(content_dict, lines, indent=0)

        return "\n".join(lines) if len(lines) > 1 else ""

    def _format_data_schema_section(self, header: str, content_dict: dict) -> str:
        """
        Format DATA_SCHEMA section with detailed table schemas for SQL agents.

        Renders table_schemas in a SQL-friendly format that LLMs can use
        to understand available data and generate queries.
        """
        lines = [header]

        # Add general info if present
        if content_dict.get("data_freshness"):
            lines.append(f"**Data Freshness:** {content_dict['data_freshness']}")
        if content_dict.get("data_sources"):
            lines.append(f"**Data Sources:** {', '.join(content_dict['data_sources'])}")
        if content_dict.get("data_formats"):
            formats = content_dict["data_formats"]
            lines.append(f"**Data Formats:** {', '.join(f'{k}={v}' for k, v in formats.items())}")

        # Render table schemas
        table_schemas = content_dict.get("table_schemas", [])
        if table_schemas:
            lines.append("")
            lines.append("### Database Schema")
            lines.append("")

            # Sort: primary tables first, then by name
            sorted_schemas = sorted(
                table_schemas,
                key=lambda t: (not t.get("is_primary", False), t.get("table_name", ""))
            )

            for table in sorted_schemas:
                table_name = table.get("table_name", "unknown")
                display_name = table.get("display_name", "")
                description = table.get("description", "")
                is_primary = table.get("is_primary", False)

                # Table header
                primary_marker = " (PRIMARY)" if is_primary else ""
                if display_name:
                    lines.append(f"**{table_name}**{primary_marker} - {display_name}")
                else:
                    lines.append(f"**{table_name}**{primary_marker}")

                if description:
                    lines.append(f"  {description}")

                # Columns
                columns = table.get("columns", {})
                if columns:
                    lines.append("  Columns:")
                    for col_name, col_desc in columns.items():
                        lines.append(f"    - `{col_name}`: {col_desc}")

                # Enum values (critical for case-sensitive queries)
                enum_values = table.get("enum_values", {})
                if enum_values:
                    lines.append("  Valid Values (use EXACTLY as shown):")
                    for col_name, values in enum_values.items():
                        values_str = ", ".join(f"'{v}'" for v in values[:10])
                        if len(values) > 10:
                            values_str += f" ... (+{len(values) - 10} more)"
                        lines.append(f"    - `{col_name}`: {values_str}")

                # Join keys
                join_keys = table.get("join_keys", [])
                if join_keys:
                    lines.append(f"  Join Keys: {', '.join(f'`{k}`' for k in join_keys)}")

                # Example queries (max 2 per table)
                examples = table.get("example_queries", [])[:2]
                if examples:
                    lines.append("  Examples:")
                    for ex in examples:
                        q = ex.get("question", "")
                        sql = ex.get("sql", "")
                        if q and sql:
                            lines.append(f"    Q: {q}")
                            lines.append(f"    SQL: `{sql[:100]}{'...' if len(sql) > 100 else ''}`")

                lines.append("")  # Blank line between tables

        # Also include available_tables for backward compatibility
        available_tables = content_dict.get("available_tables", [])
        if available_tables and not table_schemas:
            lines.append(f"**Available Tables:** {', '.join(available_tables)}")

        return "\n".join(lines) if len(lines) > 1 else ""

    def _format_dict_to_lines(
        self, data: dict, lines: list[str], indent: int = 0
    ) -> None:
        """Recursively format a dict into readable lines."""
        prefix = "  " * indent

        for key, value in data.items():
            if value is None or value == [] or value == {}:
                continue

            # Format key nicely (snake_case → Title Case)
            key_formatted = key.replace("_", " ").title()

            if isinstance(value, list):
                if all(isinstance(item, str) for item in value):
                    # Simple string list - bullet points
                    lines.append(f"{prefix}**{key_formatted}:**")
                    for item in value:
                        lines.append(f"{prefix}  - {item}")
                elif all(isinstance(item, dict) for item in value):
                    # List of objects
                    lines.append(f"{prefix}**{key_formatted}:**")
                    for item in value:
                        # Get a summary for each item
                        summary = item.get("name") or item.get("role") or str(item)[:50]
                        lines.append(f"{prefix}  - {summary}")
                else:
                    lines.append(f"{prefix}**{key_formatted}:** {value}")
            elif isinstance(value, dict):
                lines.append(f"{prefix}**{key_formatted}:**")
                self._format_dict_to_lines(value, lines, indent + 1)
            else:
                lines.append(f"{prefix}**{key_formatted}:** {value}")


class InternalClientContext(BaseModel):
    """
    Contexto interno do cliente com dados sensíveis.

    Este modelo é usado APENAS para operações internas do servidor
    (autenticação, injeção de cliente_id em tools, etc.)

    NUNCA deve ser exposto à LLM ou incluído em prompts.
    """

    id: uuid.UUID
    safe_context: SafeClientContext

    @classmethod
    def from_vizu_client_context(
        cls,
        ctx: Any,
        sections: dict[ContextSection, dict] | None = None,
    ) -> "InternalClientContext":
        """
        Create from VizuClientContext with optional pre-loaded sections.

        Args:
            ctx: VizuClientContext from database
            sections: Pre-loaded section content {section_type: content}

        Returns:
            InternalClientContext with SafeClientContext populated
        """
        # Get enabled tools
        enabled_tools: list[str] = []
        if hasattr(ctx, "get_enabled_tools_list"):
            enabled_tools = ctx.get_enabled_tools_list()
        elif hasattr(ctx, "enabled_tools") and ctx.enabled_tools:
            enabled_tools = (
                list(ctx.enabled_tools)
                if isinstance(ctx.enabled_tools, list)
                else []
            )

        # Get tier value
        tier_value = "BASIC"
        if hasattr(ctx, "tier") and ctx.tier:
            tier_value = (
                ctx.tier.value if hasattr(ctx.tier, "value") else str(ctx.tier).upper()
            )

        # Build section kwargs from pre-loaded sections
        section_kwargs: dict[str, Any] = {}
        loaded_sections: list[ContextSection] = []

        if sections:
            for section_type, content in sections.items():
                if content is None:
                    continue

                # Map section type to field name
                field_name = section_type.value
                if section_type == ContextSection.AVAILABLE_TOOLS:
                    field_name = "available_tools_config"

                # Validate content against schema if available
                schema_class = SECTION_SCHEMAS.get(section_type.value)
                if schema_class:
                    try:
                        validated = schema_class.model_validate(content)
                        section_kwargs[field_name] = validated
                        loaded_sections.append(section_type)
                    except Exception:
                        # Store raw dict if validation fails
                        section_kwargs[field_name] = content
                        loaded_sections.append(section_type)
                else:
                    section_kwargs[field_name] = content
                    loaded_sections.append(section_type)

        safe = SafeClientContext(
            nome_empresa=ctx.nome_empresa,
            tier=tier_value,
            enabled_tools=enabled_tools,
            prompt_base=getattr(ctx, "prompt_base", None),
            horario_funcionamento=getattr(ctx, "horario_funcionamento", None),
            collection_rag=getattr(ctx, "collection_rag", None),
            loaded_sections=loaded_sections,
            **section_kwargs,
        )

        return cls(id=ctx.id, safe_context=safe)

    def get_safe_context(self) -> SafeClientContext:
        """Return the LLM-safe context."""
        return self.safe_context

    def get_client_id_for_tools(self) -> str:
        """Return client ID for internal tool injection."""
        return str(self.id)
