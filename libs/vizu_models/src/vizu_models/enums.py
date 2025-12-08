# libs/vizu_models/src/vizu_models/enums.py
from enum import Enum


class TipoCliente(str, Enum):
    """
    Enum para os tipos de cliente Vizu.
    """

    B2B = "B2B"
    B2C = "B2C"
    EXTERNO = "EXTERNO"
    # Adicione outros tipos conforme necessário


class TierCliente(str, Enum):
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


class ToolCategory(str, Enum):
    """
    Categorias de ferramentas disponíveis no sistema.
    """

    RAG = "rag"
    SQL = "sql"
    SCHEDULING = "scheduling"
    DOCKER_MCP = "docker_mcp"
    PUBLIC = "public"


class TipoFonte(str, Enum):
    """
    Enum para os tipos de fontes de dados.
    """

    URL = "URL"
    # Adicione outros tipos conforme necessário
