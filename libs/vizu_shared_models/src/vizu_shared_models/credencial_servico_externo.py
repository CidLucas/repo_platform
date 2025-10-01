import uuid
from pydantic import Field

from .core import BaseSchema

class CredencialServicoExternoBase(BaseSchema):
    nome_servico: str = Field(..., description="Nome do serviço. Ex: 'google_calendar', 'database_cliente_acme'.")

# Modelo para a criação. Recebe as credenciais em formato de dicionário.
# A camada de serviço será responsável por converter para JSON e criptografar.
class CredencialServicoExternoCreate(CredencialServicoExternoBase):
    cliente_vizu_id: uuid.UUID
    credenciais: dict # Campo para receber os dados antes de cifrar

# Modelo de resposta. Note que NUNCA expomos as credenciais.
class CredencialServicoExternoInDB(CredencialServicoExternoBase):
    id: int
    cliente_vizu_id: uuid.UUID