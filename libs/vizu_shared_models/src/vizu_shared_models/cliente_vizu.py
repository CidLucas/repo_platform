import uuid
from datetime import datetime
from enum import Enum
from pydantic import ConfigDict, Field
from vizu_shared_models.credencial_servico_externo import CredencialServicoExternoBase
from .core import BaseSchema
from typing import Any, Dict, List

class TipoCliente(str, Enum):
    EXTERNO = "externo"
    INTERNO = "interno"

class TierCliente(str, Enum):
    SME = "sme"
    ENTERPRISE = "enterprise"


class ClienteVizuBase(BaseSchema):
    nome_empresa: str = Field(..., max_length=255)
    tipo_cliente: TipoCliente = Field(..., description="Diferencia clientes ('externo') de projetos ('interno').")
    tier: TierCliente = Field(..., description="Nível do cliente para controle de recursos.")


class ClienteVizuCreate(ClienteVizuBase):
    pass

class ClienteVizuUpdate(ClienteVizuBase):

    # Em uma implementação real de PATCH, os campos seriam opcionais:
    nome_empresa: str | None = Field(None, max_length=255)
    tipo_cliente: TipoCliente | None = None
    tier: TierCliente | None = None

    pass

class ClienteVizuInDB(ClienteVizuBase):
    id: uuid.UUID
    api_key: str
    criado_em: datetime

class ClienteVizuRead(ClienteVizuBase):
    id: uuid.UUID
    criado_em: datetime

    # Esta linha permite que este modelo seja criado a partir do seu objeto do banco de dados.
    model_config = ConfigDict(from_attributes=True)


class VizuClientContext(BaseSchema):
    """
    Modelo Pydantic que agrega todas as informações de contexto necessárias
    para a operação do agente.
    """
    # Informações de Identificação do Cliente
    id: uuid.UUID
    api_key: str
    nome_empresa: str

    # Configurações de Negócio para o Agente
    prompt_base: str | None
    horario_funcionamento: Dict[str, Any] | None
    ferramenta_rag_habilitada: bool
    ferramenta_sql_habilitada: bool
    collection_rag: str | None

    # Lista de credenciais já decifradas
    # Usamos o modelo Pydantic 'CredencialServicoExternoBase' para a tipagem
    credenciais: List[CredencialServicoExternoBase] = []