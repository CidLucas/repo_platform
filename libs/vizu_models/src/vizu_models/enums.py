# libs/vizu_models/src/vizu_models/enums.py
from enum import Enum


class TipoCliente(Enum):
    """
    Enum para os tipos de cliente Vizu.
    """

    B2B = "B2B"
    B2C = "B2C"
    EXTERNO = "EXTERNO"
    # Adicione outros tipos conforme necessário


class TierCliente(Enum):
    """
    Enum para os tiers de serviço do cliente.

    Tiers controlam acesso a ferramentas e limites de uso:
    - BASIC: Ferramentas básicas (RAG)
    - SME: Ferramentas intermediárias (RAG + SQL + Scheduling)
    - ENTERPRISE: Todas ferramentas + Docker MCP integrations
    """

    FREE = "FREE"
    BASIC = "BASIC"
    SME = "SME"
    PREMIUM = "PREMIUM"
    ENTERPRISE = "ENTERPRISE"

    def __lt__(self, other: "TierCliente") -> bool:
        """Permite comparação entre tiers."""
        order = {"FREE": 0, "BASIC": 1, "SME": 2, "PREMIUM": 3, "ENTERPRISE": 4}
        return order.get(self.value, 0) < order.get(other.value, 0)

    def __le__(self, other: "TierCliente") -> bool:
        """Permite comparação <= entre tiers."""
        order = {"FREE": 0, "BASIC": 1, "SME": 2, "PREMIUM": 3, "ENTERPRISE": 4}
        return order.get(self.value, 0) <= order.get(other.value, 0)

    def __gt__(self, other: "TierCliente") -> bool:
        """Permite comparação > entre tiers."""
        return not self.__le__(other)

    def __ge__(self, other: "TierCliente") -> bool:
        """Permite comparação >= entre tiers."""
        return not self.__lt__(other)


class ToolCategory(Enum):
    """
    Categorias de ferramentas disponíveis no sistema.
    """

    RAG = "rag"
    SQL = "sql"
    SCHEDULING = "scheduling"
    DOCKER_MCP = "docker_mcp"
    PUBLIC = "public"


class TipoFonte(Enum):
    """
    Enum para os tipos de fontes de dados.
    """

    URL = "URL"
    UPLOAD = "UPLOAD"
    # Adicione outros tipos conforme necessário


class ContextSection(Enum):
    """
    Sections of the modular client context (Context 2.0).

    Each section can be injected independently into agent nodes,
    enabling selective context injection based on node requirements.

    Sections used for prompt injection:
    - COMPANY_PROFILE: Company identity
    - BRAND_VOICE: Communication style
    - CURRENT_MOMENT: Weekly priorities/challenges
    - TEAM_STRUCTURE: Contacts and business hours
    - POLICIES: Business rules and guardrails
    - DATA_SCHEMA: Available data for SQL agent
    - AVAILABLE_TOOLS: Tool configuration
    """

    # Core Identity
    COMPANY_PROFILE = "company_profile"  # Mission, vision, values, archetype
    BRAND_VOICE = "brand_voice"  # Tone, style, phrases to use/avoid

    # Operations
    CURRENT_MOMENT = "current_moment"  # Priorities, challenges, wins, metrics
    TEAM_STRUCTURE = "team_structure"  # Key contacts, escalation paths
    POLICIES = "policies"  # Rules, limits, approval flows, guardrails

    # Technical
    DATA_SCHEMA = "data_schema"  # Available tables, formats, key fields
    AVAILABLE_TOOLS = "available_tools"  # Tool descriptions, limits
