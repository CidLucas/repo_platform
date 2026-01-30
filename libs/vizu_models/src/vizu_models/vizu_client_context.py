import uuid
from typing import Any

from vizu_models.credencial_servico_externo import CredencialServicoExternoBase

from .cliente_vizu import ClienteVizuBase


class VizuClientContext(ClienteVizuBase):
    """
    Runtime context model aggregating all client information for agent operation.

    Context 2.0: Includes embedded context sections from clientes_vizu table.

    This model is used by ContextService to provide full client context
    to agents, including all modular sections.
    """

    # ===== IDENTIFICATION =====
    id: uuid.UUID
    nome_empresa: str
    cpf_cnpj: str | None = None

    # ===== CONTEXT SECTIONS (Context 2.0) =====
    # Core Identity
    company_profile: dict[str, Any] | None = None
    brand_voice: dict[str, Any] | None = None

    # Business
    product_catalog: dict[str, Any] | None = None
    target_audience: dict[str, Any] | None = None
    market_context: dict[str, Any] | None = None

    # Operations
    current_moment: dict[str, Any] | None = None
    team_structure: dict[str, Any] | None = None
    policies: dict[str, Any] | None = None

    # Technical
    data_schema: dict[str, Any] | None = None
    available_tools: dict[str, Any] | None = None

    # Custom
    client_custom: dict[str, Any] | None = None

    # ===== LEGACY FIELDS (backward compatibility) =====
    enabled_tools: list[str] = []
    prompt_base: str | None = None
    horario_funcionamento: dict[str, Any] | None = None
    collection_rag: str | None = None

    # Decrypted credentials (internal use)
    credenciais: list[CredencialServicoExternoBase] = []

    # ===== HELPER METHODS =====

    def get_enabled_tools_list(self) -> list[str]:
        """
        Get list of enabled tools (Context 2.0 compatible).

        Prefers available_tools section, falls back to legacy enabled_tools.
        """
        if self.available_tools and self.available_tools.get("enabled_tool_names"):
            return self.available_tools["enabled_tool_names"]
        return list(self.enabled_tools or [])

    def get_default_prompt(self) -> str | None:
        """
        Get default system prompt (Context 2.0 compatible).

        Prefers available_tools section, falls back to legacy prompt_base.
        """
        if self.available_tools and self.available_tools.get("default_system_prompt"):
            return self.available_tools["default_system_prompt"]
        return self.prompt_base

    def get_business_hours(self) -> str | None:
        """
        Get business hours string (Context 2.0 compatible).

        Prefers team_structure section, falls back to legacy horario_funcionamento.
        """
        if self.team_structure and self.team_structure.get("business_hours"):
            return self.team_structure["business_hours"]
        if self.horario_funcionamento:
            # Try to extract from legacy format
            return self.horario_funcionamento.get("horario")
        return None

    def get_section(self, section_name: str) -> dict[str, Any] | None:
        """Get a context section by name."""
        section_map = {
            "company_profile": self.company_profile,
            "brand_voice": self.brand_voice,
            "product_catalog": self.product_catalog,
            "target_audience": self.target_audience,
            "market_context": self.market_context,
            "current_moment": self.current_moment,
            "team_structure": self.team_structure,
            "policies": self.policies,
            "data_schema": self.data_schema,
            "available_tools": self.available_tools,
            "client_custom": self.client_custom,
        }
        return section_map.get(section_name)

    def get_loaded_sections(self) -> list[str]:
        """Get list of sections that have data."""
        sections = []
        for name in [
            "company_profile", "brand_voice", "product_catalog",
            "target_audience", "market_context", "current_moment",
            "team_structure", "policies", "data_schema",
            "available_tools", "client_custom"
        ]:
            if self.get_section(name):
                sections.append(name)
        return sections

    def to_safe_context(self) -> "SafeClientContext":
        """
        Convert to SafeClientContext for LLM-safe exposure.

        This creates an immutable, LLM-safe view of the client context
        that can be used in prompts. All modular sections are validated
        against their Pydantic schemas.

        Returns:
            SafeClientContext with all loaded sections
        """
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
        )
        from .enums import ContextSection
        from .safe_client_context import SafeClientContext

        # Build loaded_sections list
        loaded_sections = []
        section_mapping = {
            "company_profile": ContextSection.COMPANY_PROFILE,
            "brand_voice": ContextSection.BRAND_VOICE,
            "product_catalog": ContextSection.PRODUCT_CATALOG,
            "target_audience": ContextSection.TARGET_AUDIENCE,
            "market_context": ContextSection.MARKET_CONTEXT,
            "current_moment": ContextSection.CURRENT_MOMENT,
            "team_structure": ContextSection.TEAM_STRUCTURE,
            "policies": ContextSection.POLICIES,
            "data_schema": ContextSection.DATA_SCHEMA,
            "available_tools": ContextSection.AVAILABLE_TOOLS,
            "client_custom": ContextSection.CLIENT_CUSTOM,
        }

        for name, section_enum in section_mapping.items():
            if self.get_section(name):
                loaded_sections.append(section_enum)

        # Validate sections against schemas (best effort)
        def _safe_validate(data, schema_cls):
            if not data:
                return None
            try:
                return schema_cls.model_validate(data)
            except Exception:
                # Return raw dict if validation fails
                return None

        return SafeClientContext(
            # Basic identity
            nome_empresa=self.nome_empresa,
            tier=self.tier or "BASIC",
            enabled_tools=self.get_enabled_tools_list(),

            # Legacy
            prompt_base=self.prompt_base,
            horario_funcionamento=self.horario_funcionamento,
            collection_rag=self.collection_rag,

            # Context 2.0 sections (validated)
            company_profile=_safe_validate(self.company_profile, CompanyProfile),
            brand_voice=_safe_validate(self.brand_voice, BrandVoice),
            product_catalog=_safe_validate(self.product_catalog, ProductCatalog),
            target_audience=_safe_validate(self.target_audience, TargetAudience),
            market_context=_safe_validate(self.market_context, MarketContext),
            current_moment=_safe_validate(self.current_moment, CurrentMoment),
            team_structure=_safe_validate(self.team_structure, TeamStructure),
            policies=_safe_validate(self.policies, Policies),
            data_schema=_safe_validate(self.data_schema, DataSchema),
            available_tools_config=_safe_validate(self.available_tools, AvailableTools),
            client_custom=self.client_custom,

            # Metadata
            loaded_sections=loaded_sections,
        )
