# vizu_models/safe_client_context.py
"""
SafeClientContext - Modular context safe for LLM exposure (Context 2.0).

Este modelo contém APENAS os dados que são seguros para serem
expostos à LLM. Nenhuma informação sensível (API keys, IDs internos,
credenciais) deve estar aqui.

IMPORTANTE: Qualquer dado neste modelo pode potencialmente ser
incluído em prompts ou respostas da LLM.

Context 2.0 Features:
- Modular sections that can be loaded/injected independently
- Selective injection based on node requirements
- Immutable to prevent accidental modifications
- Backward compatible with legacy prompt_base field
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
    MarketContext,
    Policies,
    ProductCatalog,
    TargetAudience,
    TeamStructure,
    SECTION_SCHEMAS,
)


class SafeClientContext(BaseModel):
    """
    Modular client context safe for LLM exposure (Context 2.0).

    Supports both legacy single-field context (prompt_base) and
    new modular sections. Sections can be loaded independently
    and compiled into prompt text selectively.

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

    # ===== LEGACY FIELDS (backward compatibility) =====
    prompt_base: str | None = None
    horario_funcionamento: dict[str, Any] | None = None
    collection_rag: str | None = None

    # ===== MODULAR SECTIONS (Context 2.0) =====
    # Core Identity
    company_profile: CompanyProfile | None = None
    brand_voice: BrandVoice | None = None

    # Business
    product_catalog: ProductCatalog | None = None
    target_audience: TargetAudience | None = None
    market_context: MarketContext | None = None

    # Operations
    current_moment: CurrentMoment | None = None
    team_structure: TeamStructure | None = None
    policies: Policies | None = None

    # Technical
    data_schema: DataSchema | None = None
    available_tools_config: AvailableTools | None = None

    # Custom
    client_custom: dict[str, Any] | None = None

    # ===== METADATA =====
    loaded_sections: list[ContextSection] = Field(default_factory=list)

    def get_section(self, section: ContextSection) -> BaseModel | dict | None:
        """Get a specific section by type."""
        section_map = {
            ContextSection.COMPANY_PROFILE: self.company_profile,
            ContextSection.BRAND_VOICE: self.brand_voice,
            ContextSection.PRODUCT_CATALOG: self.product_catalog,
            ContextSection.TARGET_AUDIENCE: self.target_audience,
            ContextSection.MARKET_CONTEXT: self.market_context,
            ContextSection.CURRENT_MOMENT: self.current_moment,
            ContextSection.TEAM_STRUCTURE: self.team_structure,
            ContextSection.POLICIES: self.policies,
            ContextSection.DATA_SCHEMA: self.data_schema,
            ContextSection.AVAILABLE_TOOLS: self.available_tools_config,
            ContextSection.CLIENT_CUSTOM: self.client_custom,
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
            parts.append(f"# Contexto: {self.nome_empresa}")
            parts.append(f"**Tier:** {self.tier}")

        # Compile each requested section
        for section in sections:
            content = self.get_section(section)
            if content is None:
                continue

            section_text = self._format_section(section, content)
            if section_text:
                parts.append(section_text)

        # Legacy fallback: include prompt_base if no sections loaded
        if not sections and self.prompt_base:
            parts.append(f"\n## Instruções\n{self.prompt_base}")

        return "\n\n".join(parts)

    def _format_section(self, section: ContextSection, content: Any) -> str:
        """Format a single section for prompt injection."""
        if content is None:
            return ""

        # Section headers in Portuguese
        headers = {
            ContextSection.COMPANY_PROFILE: "## Perfil da Empresa",
            ContextSection.BRAND_VOICE: "## Voz da Marca",
            ContextSection.PRODUCT_CATALOG: "## Produtos e Serviços",
            ContextSection.TARGET_AUDIENCE: "## Público-Alvo",
            ContextSection.MARKET_CONTEXT: "## Contexto de Mercado",
            ContextSection.CURRENT_MOMENT: "## Momento Atual",
            ContextSection.TEAM_STRUCTURE: "## Estrutura da Equipe",
            ContextSection.POLICIES: "## Políticas e Limites",
            ContextSection.DATA_SCHEMA: "## Dados Disponíveis",
            ContextSection.AVAILABLE_TOOLS: "## Ferramentas Disponíveis",
            ContextSection.CLIENT_CUSTOM: "## Contexto Personalizado",
        }

        header = headers.get(section, f"## {section.value}")

        # Convert to dict if Pydantic model
        if isinstance(content, BaseModel):
            content_dict = content.model_dump(exclude_none=True, exclude_defaults=True)
        else:
            content_dict = content

        if not content_dict:
            return ""

        lines = [header]
        self._format_dict_to_lines(content_dict, lines, indent=0)

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
