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
    """

    FREE = "FREE"
    BASIC = "BASIC"
    PREMIUM = "PREMIUM"
    ENTERPRISE = "ENTERPRISE"
    SME = "SME"


class TipoFonte(str, Enum):
    """
    Enum para os tipos de fontes de dados.
    """

    URL = "URL"
    # Adicione outros tipos conforme necessário
