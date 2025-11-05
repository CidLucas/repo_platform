import uuid
from typing import Dict, Any
from pydantic import Field

from .core import BaseSchema

class ConfiguracaoNegocioBase(BaseSchema):
    prompt_base: str | None = Field(None, description="O prompt principal que define a personalidade e as instruções do agente de IA.")
    horario_funcionamento: Dict[str, Any] | None = Field(None, description='Objeto JSON para armazenar os horários de operação. Ex: {"seg-sex": "09:00-18:00"}')
    ferramenta_rag_habilitada: bool = Field(default=False)
    # Adicionar outras flags de ferramentas conforme necessário
    ferramenta_sql_habilitada: bool = Field(default=False)
    ferramenta_agendamento_habilitada: bool = Field(default=False)


class ConfiguracaoNegocioCreate(ConfiguracaoNegocioBase):
    cliente_vizu_id: uuid.UUID


class ConfiguracaoNegocioInDB(ConfiguracaoNegocioBase):
    id: int
    cliente_vizu_id: uuid.UUID


class ConfiguracaoNegocioUpdate(ConfiguracaoNegocioBase):

    # Em uma implementação real de PATCH, os campos seriam opcionais:
    prompt_base: str | None = Field(None, description="O prompt principal que define a personalidade e as instruções do agente de IA.")
    horario_funcionamento: Dict[str, Any] | None = Field(None, description='Objeto JSON para armazenar os horários de operação. Ex: {"seg-sex": "09:00-18:00"}')
    ferramenta_rag_habilitada: bool = Field(default=False)
    pass