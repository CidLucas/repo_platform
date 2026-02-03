import uuid
from typing import Any

from vizu_models.credencial_servico_externo import CredencialServicoExternoBase

from .cliente_vizu import ClienteVizuBase


class VizuClientContext(ClienteVizuBase):
    """
    Runtime context model aggregating all client information for agent operation.

    Context 2.0: Includes embedded context sections from clientes_vizu table.
    These sections are injected into prompts via ContextService.
    """

    # ===== IDENTIFICATION =====
    id: uuid.UUID
    nome_empresa: str
    cpf_cnpj: str | None = None

    # ===== CONTEXT SECTIONS (for prompt injection) =====
    company_profile: dict[str, Any] | None = None
    brand_voice: dict[str, Any] | None = None
    current_moment: dict[str, Any] | None = None
    team_structure: dict[str, Any] | None = None
    policies: dict[str, Any] | None = None
    data_schema: dict[str, Any] | None = None
    available_tools: dict[str, Any] | None = None

    # ===== TOOL CONFIGURATION =====
    enabled_tools: list[str] = []

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
        """Get default system prompt from available_tools section."""
        if self.available_tools and self.available_tools.get("default_system_prompt"):
            return self.available_tools["default_system_prompt"]
        return None

    def get_business_hours(self) -> str | None:
        """Get business hours from team_structure section."""
        if self.team_structure and self.team_structure.get("business_hours"):
            return self.team_structure["business_hours"]
        return None

    def get_section(self, section_name: str) -> dict[str, Any] | None:
        """Get a context section by name."""
        section_map = {
            "company_profile": self.company_profile,
            "brand_voice": self.brand_voice,
            "current_moment": self.current_moment,
            "team_structure": self.team_structure,
            "policies": self.policies,
            "data_schema": self.data_schema,
            "available_tools": self.available_tools,
        }
        return section_map.get(section_name)

    def get_loaded_sections(self) -> list[str]:
        """Get list of sections that have data."""
        sections = []
        for name in [
            "company_profile", "brand_voice", "current_moment",
            "team_structure", "policies", "data_schema", "available_tools"
        ]:
            if self.get_section(name):
                sections.append(name)
        return sections

    def to_safe_context(self) -> "SafeClientContext":
        """
        Convert to SafeClientContext for LLM-safe exposure.

        Creates an immutable, LLM-safe view of the client context
        that can be used in prompts.

        Returns:
            SafeClientContext with all loaded sections
        """
        from .context_schemas import (
            AvailableTools,
            BrandVoice,
            CompanyProfile,
            CurrentMoment,
            DataSchema,
            Policies,
            TeamStructure,
        )
        from .enums import ContextSection
        from .safe_client_context import SafeClientContext

        # Build loaded_sections list
        loaded_sections = []
        section_mapping = {
            "company_profile": ContextSection.COMPANY_PROFILE,
            "brand_voice": ContextSection.BRAND_VOICE,
            "current_moment": ContextSection.CURRENT_MOMENT,
            "team_structure": ContextSection.TEAM_STRUCTURE,
            "policies": ContextSection.POLICIES,
            "data_schema": ContextSection.DATA_SCHEMA,
            "available_tools": ContextSection.AVAILABLE_TOOLS,
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
                return None

        return SafeClientContext(
            # Basic identity
            nome_empresa=self.nome_empresa,
            tier=self.tier or "BASIC",
            enabled_tools=self.get_enabled_tools_list(),

            # Context sections (validated)
            company_profile=_safe_validate(self.company_profile, CompanyProfile),
            brand_voice=_safe_validate(self.brand_voice, BrandVoice),
            current_moment=_safe_validate(self.current_moment, CurrentMoment),
            team_structure=_safe_validate(self.team_structure, TeamStructure),
            policies=_safe_validate(self.policies, Policies),
            data_schema=_safe_validate(self.data_schema, DataSchema),
            available_tools_config=_safe_validate(self.available_tools, AvailableTools),

            # Metadata
            loaded_sections=loaded_sections,
        )
