import uuid
from typing import Dict, Any
from pydantic import Field

# Importa a base do nosso modelo compartilhado
from vizu_models import ClienteFinalBase


# Omitimos o 'cliente_vizu_id' pois ele virá da autenticação (API Key),
# não do corpo da requisição.
class ClienteFinalCreate(ClienteFinalBase):
    """Schema para a criação de um novo cliente final via API."""

    pass


class ClienteFinalUpdate(ClienteFinalBase):
    """
    Schema para atualização. Todos os campos são opcionais, permitindo
    atualizações parciais (PATCH).
    """

    id_externo: str | None = Field(
        None,
        description="O identificador principal do cliente final. Ex: número de telefone.",
    )
    nome: str | None = Field(None, max_length=255)
    metadados: Dict[str, Any] | None = Field(
        None, description="Campo flexível para dados não estruturados."
    )


class ClienteFinalPublic(ClienteFinalBase):
    """
    Schema para a resposta da API. Inclui os campos do banco de dados
    que são seguros para serem expostos publicamente.
    """

    id: int
    cliente_vizu_id: uuid.UUID
