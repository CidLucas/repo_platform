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

    # Metadata
    cliente_id: str | None = None
    tier: str | None = None

    # Custom variables
    custom: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for template rendering."""
        result = {
            "nome_empresa": self.nome_empresa or "Vizu",
            "tools_description": self.tools_description or "",
            "enabled_tools": self.enabled_tools,
            "agent_personality": self.agent_personality or "",
            "agent_name": self.agent_name or "Assistente",
            "context_sections": self.context_sections or "",
            "cliente_id": self.cliente_id or "",
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
    - VizuClientContext
    - SafeClientContext
    - Raw dictionaries
    """

    @staticmethod
    def from_client_context(context: Any) -> PromptVariables:
        """
        Extract variables from a VizuClientContext.

        Args:
            context: VizuClientContext or similar object

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
            variables.cliente_id = str(context.id)

        return variables

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
            "cliente_id": "cliente_id",
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
    def _format_horarios(horarios: dict | None) -> str:
        """Format business hours for display."""
        if not horarios:
            return "Horário não configurado."

        linhas = []
        dias_ordem = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]

        for dia in dias_ordem:
            if dia in horarios:
                info = horarios[dia]
                if isinstance(info, dict):
                    abertura = info.get("abertura", "")
                    fechamento = info.get("fechamento", "")
                    if abertura and fechamento:
                        linhas.append(f"- {dia.capitalize()}: {abertura} às {fechamento}")
                    else:
                        linhas.append(f"- {dia.capitalize()}: Fechado")
                elif isinstance(info, str):
                    linhas.append(f"- {dia.capitalize()}: {info}")

        # Add days not in standard order
        for dia, info in horarios.items():
            if dia.lower() not in dias_ordem:
                linhas.append(f"- {dia.capitalize()}: {info}")

        return "\n".join(linhas) if linhas else "Horário não configurado."

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

    def with_prompt_base(self, prompt: str) -> "ContextVariableBuilder":
        """Set personalized prompt."""
        self._variables.prompt_personalizado = prompt
        return self

    def with_horarios(self, horarios: dict) -> "ContextVariableBuilder":
        """Set business hours."""
        self._variables.horario_formatado = VariableExtractor._format_horarios(horarios)
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

    def with_cliente_id(self, cliente_id: str) -> "ContextVariableBuilder":
        """Set client ID."""
        self._variables.cliente_id = cliente_id
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
