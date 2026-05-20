"""
Variable extraction and preparation for prompt templates.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PromptVariables:
    """Container for prompt template variables."""

    # Core variables
    nome_empresa: str | None = None

    # Tool-related
    tools_description: str | None = None
    enabled_tools: list[str] = field(default_factory=list)

    # Agent personality (for multi-agent)
    agent_personality: str | None = None
    agent_name: str | None = None

    # Context 2.0: compiled sections
    context_sections: str | None = None

    # Schema / KB context injection
    sql_schema_context: str | None = None  # Rendered client DB schema for SQL agents
    kb_context: str | None = None          # Rendered KB metadata for RAG agents

    # Metadata
    client_id: str | None = None
    tier: str | None = None

    # Custom variables
    custom: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for template rendering."""
        result = {
            "nome_empresa": self.nome_empresa or "Blu",
            "tools_description": self.tools_description or "",
            "enabled_tools": self.enabled_tools,
            "agent_personality": self.agent_personality or "",
            "agent_name": self.agent_name or "Assistente",
            "context_sections": self.context_sections or "",
            "sql_schema_context": self.sql_schema_context or "",
            "kb_context": self.kb_context or "",
            "client_id": self.client_id or "",
            "tier": self.tier or "",
        }

        # Add custom variables
        result.update(self.custom)

        return result

    def set(self, key: str, value: Any) -> "PromptVariables":
        """Set a custom variable (fluent interface)."""
        self.custom[key] = value
        return self


class VariableExtractor:
    """
    Extract variables from various sources for prompt rendering.

    Supports extraction from:
    - BluClientContext
    - SafeClientContext
    - Raw dictionaries
    """

    @staticmethod
    def from_client_context(context: Any) -> PromptVariables:
        """
        Extract variables from a BluClientContext.

        Args:
            context: BluClientContext or similar object

        Returns:
            PromptVariables with extracted data
        """
        variables = PromptVariables()

        # Core info
        if hasattr(context, "nome_empresa"):
            variables.nome_empresa = context.nome_empresa
        elif hasattr(context, "nome_cliente"):
            variables.nome_empresa = context.nome_cliente

        # Tools
        if hasattr(context, "get_enabled_tools_list"):
            variables.enabled_tools = context.get_enabled_tools_list()

        # Tier
        if hasattr(context, "tier"):
            tier = context.tier
            variables.tier = tier.value if hasattr(tier, "value") else str(tier)

        # Client ID
        if hasattr(context, "id"):
            variables.client_id = str(context.id)

        # SQL schema context — rendered from per-client sql_table_config rows
        data_schema = getattr(context, "data_schema", None)
        variables.sql_schema_context = VariableExtractor.render_sql_schema(data_schema)

        # KB / knowledge base context
        variables.kb_context = VariableExtractor.render_kb_context(context)

        return variables

    @staticmethod
    def render_sql_schema(data_schema: Any) -> str:
        """
        Render DataSchema.table_schemas into a markdown string for SQL prompt injection.

        Returns empty string when no per-client table configs exist (the prompt
        template's own hardcoded fallback schema will be used in that case).
        """
        if not data_schema:
            return ""

        table_schemas = getattr(data_schema, "table_schemas", [])
        if not table_schemas:
            return ""

        lines: list[str] = [
            "# DATABASE SCHEMA\n",
            "Security filtering by `client_id` is applied automatically"
            " — NEVER include it in queries.\n",
        ]

        for table in table_schemas:
            label = "PRIMARY" if getattr(table, "is_primary", False) else "Dim"
            display = getattr(table, "display_name", None)
            header = f"## {label}: `{table.table_name}`"
            if display:
                header += f" ({display})"
            lines.append(header)

            description = getattr(table, "description", None)
            if description:
                lines.append(description)

            columns: dict = getattr(table, "columns", {}) or {}
            if columns:
                lines.append("\n| Column | Description |")
                lines.append("|--------|-------------|")
                for col, desc in columns.items():
                    # Skip PK/FK ID columns — join mechanics belong in JOIN REFERENCE,
                    # not the business-facing column listing.
                    if col == "id" or col.endswith("_id"):
                        continue
                    lines.append(f"| `{col}` | {desc} |")

            enum_values: dict = getattr(table, "enum_values", {}) or {}
            if enum_values:
                lines.append("\n**Valid values:**")
                for col, vals in enum_values.items():
                    formatted = ", ".join(f"`{v}`" for v in vals)
                    lines.append(f"- `{col}`: {formatted}")

            join_keys: list = getattr(table, "join_keys", []) or []
            if join_keys:
                lines.append("\n**Joins:**")
                for jk in join_keys:
                    from_ = getattr(jk, "from_", None) or getattr(jk, "from", "")
                    to = getattr(jk, "to", "")
                    lines.append(f"- `{from_}` → `{to}`")

            example_queries: list = getattr(table, "example_queries", []) or []
            for ex in example_queries[:2]:
                question = ex.get("question", "")
                sql = ex.get("sql", "")
                if question and sql:
                    lines.append(f"\n*{question}*")
                    lines.append(f"```sql\n{sql}\n```")

            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def render_kb_context(context: Any) -> str:
        """
        Render knowledge base metadata from BluClientContext for RAG prompt injection.

        Returns empty string when no relevant metadata is available.
        """
        if not context:
            return ""

        lines: list[str] = []

        # Data freshness and sources from data_schema
        data_schema = getattr(context, "data_schema", None)
        if data_schema:
            freshness = getattr(data_schema, "data_freshness", None)
            if freshness:
                lines.append(f"- Atualização dos dados: {freshness}")
            sources: list = getattr(data_schema, "data_sources", []) or []
            if sources:
                lines.append(f"- Fontes de dados: {', '.join(sources)}")

        # Policy topics available in KB
        policies = getattr(context, "policies", None)
        if policies and isinstance(policies, dict):
            topics = [k for k in policies if policies[k]]
            if topics:
                lines.append(f"- Tópicos na base de conhecimento: {', '.join(topics)}")

        # Company profile signals for domain-aware RAG
        company_profile = getattr(context, "company_profile", None)
        if company_profile and isinstance(company_profile, dict):
            sector = company_profile.get("sector") or company_profile.get("setor")
            if sector:
                lines.append(f"- Setor do cliente: {sector}")

        if not lines:
            return ""

        return "# BASE DE CONHECIMENTO\n" + "\n".join(lines)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> PromptVariables:
        """
        Extract variables from a dictionary.

        Args:
            data: Dictionary with variable data

        Returns:
            PromptVariables
        """
        variables = PromptVariables()

        # Map known keys (Context 2.0 - no legacy fields)
        key_mapping = {
            "nome_empresa": "nome_empresa",
            "nome_cliente": "nome_empresa",
            "tools_description": "tools_description",
            "enabled_tools": "enabled_tools",
            "agent_personality": "agent_personality",
            "agent_name": "agent_name",
            "client_id": "client_id",
            "tier": "tier",
            "context_sections": "context_sections",
        }

        for src_key, dest_key in key_mapping.items():
            if src_key in data and dest_key:
                setattr(variables, dest_key, data[src_key])

        # Copy remaining keys to custom
        known_keys = set(key_mapping.keys())
        for key, value in data.items():
            if key not in known_keys:
                variables.custom[key] = value

        return variables

    @staticmethod
    def build_tools_description(
        tools: list,
        tool_registry: Any | None = None,
    ) -> str:
        """
        Build a description of available tools.

        Args:
            tools: List of tool names (str) OR tool objects (with .name attribute)
            tool_registry: Optional ToolRegistry for metadata

        Returns:
            Formatted tool descriptions
        """
        if not tools:
            return ""

        lines = []

        for tool in tools:
            # Handle both string names and tool objects
            if isinstance(tool, str):
                tool_name = tool
                tool_desc = None
            else:
                tool_name = getattr(tool, "name", str(tool))
                tool_desc = getattr(tool, "description", None)

            # Try to get description from registry if not already present
            description = tool_desc
            if not description and tool_registry:
                try:
                    meta = tool_registry.get_tool(tool_name)
                    if meta and hasattr(meta, "description"):
                        description = meta.description
                except Exception:
                    pass

            if not description:
                description = "Sem descrição"

            lines.append(f"- **{tool_name}**: {description}")

        return "\n".join(lines)


class ContextVariableBuilder:
    """
    Builder for constructing PromptVariables with fluent interface.
    """

    def __init__(self):
        self._variables = PromptVariables()

    def with_empresa(self, nome: str) -> "ContextVariableBuilder":
        """Set company name."""
        self._variables.nome_empresa = nome
        return self

    def with_tools(
        self,
        tools: list[str],
        registry: Any | None = None,
    ) -> "ContextVariableBuilder":
        """Set available tools."""
        self._variables.enabled_tools = tools
        self._variables.tools_description = VariableExtractor.build_tools_description(
            tools, registry
        )
        return self

    def with_agent(
        self,
        name: str,
        personality: str | None = None,
    ) -> "ContextVariableBuilder":
        """Set agent info."""
        self._variables.agent_name = name
        if personality:
            self._variables.agent_personality = personality
        return self

    def with_tier(self, tier: str) -> "ContextVariableBuilder":
        """Set client tier."""
        self._variables.tier = tier
        return self

    def with_client_id(self, client_id: str) -> "ContextVariableBuilder":
        """Set client ID."""
        self._variables.client_id = client_id
        return self

    def with_custom(self, key: str, value: Any) -> "ContextVariableBuilder":
        """Add custom variable."""
        self._variables.custom[key] = value
        return self

    def from_context(self, context: Any) -> "ContextVariableBuilder":
        """Initialize from client context."""
        self._variables = VariableExtractor.from_client_context(context)
        return self

    def build(self) -> PromptVariables:
        """Build and return the PromptVariables."""
        return self._variables

    def build_dict(self) -> dict[str, Any]:
        """Build and return as dictionary."""
        return self._variables.to_dict()
