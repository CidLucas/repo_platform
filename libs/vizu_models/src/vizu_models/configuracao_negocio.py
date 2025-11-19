import uuid
from typing import Any, Optional, TYPE_CHECKING, Dict

from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import Column, JSON

if TYPE_CHECKING:
    from .cliente_vizu import ClienteVizu


class ConfiguracaoNegocioBase(SQLModel):
    prompt_base: Optional[str] = Field(None, description="O prompt principal que define a personalidade e as instruções do agente de IA.")
    horario_funcionamento: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description='Objeto JSON para armazenar os horários de operação.'
    )
    ferramenta_rag_habilitada: bool = Field(default=False)
    ferramenta_sql_habilitada: bool = Field(default=False)
    ferramenta_agendamento_habilitada: bool = Field(default=False)


class ConfiguracaoNegocio(ConfiguracaoNegocioBase, table=True):
    __tablename__ = "configuracao_negocio"

    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_vizu_id: uuid.UUID = Field(foreign_key="cliente_vizu.id", unique=True, index=True)
    cliente_vizu: "ClienteVizu" = Relationship(back_populates="configuracao")


class ConfiguracaoNegocioCreate(ConfiguracaoNegocioBase):
    cliente_vizu_id: uuid.UUID


class ConfiguracaoNegocioRead(ConfiguracaoNegocioBase):
    id: int
    cliente_vizu_id: uuid.UUID

class ConfiguracaoNegocioUpdate(SQLModel):
    prompt_base: Optional[str] = None
    horario_funcionamento: Optional[Dict[str, Any]] = None
    ferramenta_rag_habilitada: Optional[bool] = None
    ferramenta_sql_habilitada: Optional[bool] = None
    ferramenta_agendamento_habilitada: Optional[bool] = None


class ConfiguracaoNegocioInDB(ConfiguracaoNegocio):
    """
    Schema for representing the full database object, for internal use.
    """
    pass



