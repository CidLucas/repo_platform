import uuid
from datetime import datetime
from typing import Dict, Any
from pydantic import Field

from .core import BaseSchema

# Replicamos os Enums aqui para que a biblioteca de validação
# não dependa da biblioteca de banco de dados.
from enum import Enum
class TipoFonte(str, Enum):
    PDF = "pdf"
    URL = "url"
    TXT = "txt"
    JSON = "json"

class StatusIndexacao(str, Enum):
    PENDENTE = "pendente"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDO = "concluido"
    FALHA = "falha"


class FonteDeDadosBase(BaseSchema):
    tipo_fonte: TipoFonte
    caminho: str = Field(..., description="URL, caminho para o arquivo no GCS, etc.")
    status_indexacao: StatusIndexacao = Field(default=StatusIndexacao.PENDENTE)
    hash_conteudo: str | None = Field(None, max_length=64)
    metadados_indexacao: Dict[str, Any] | None = None


class FonteDeDadosCreate(FonteDeDadosBase):
    cliente_vizu_id: uuid.UUID


class FonteDeDadosInDB(FonteDeDadosBase):
    id: int
    cliente_vizu_id: uuid.UUID
    criado_em: datetime
    atualizado_em: datetime