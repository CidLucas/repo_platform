import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSON  # Importação mais específica

# Importação explícita de JSON para colunas
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    # Resolvendo forward reference (correto)
    from .cliente_vizu import ClienteVizu


class ConfiguracaoNegocioBase(SQLModel):
    # CORREÇÃO AQUI: Deixamos o tipo como Any para evitar conflito de tipagem
    # com o JSON do SQLAlchemy, já que a coluna SQL é definida explicitamente.
    horario_funcionamento: Any | None = Field(
        default=None,
        sa_column=Column(JSON),  # Use o tipo JSON do SQLAlchemy
        description="Objeto JSON para armazenar os horários de operação.",
    )

    prompt_base: str | None = Field(
        None,
        description="O prompt principal que define a personalidade e as instruções do agente de IA.",
    )

    ferramenta_rag_habilitada: bool = Field(default=False)
    collection_rag: str | None = Field(
        None, description="O nome da collection que o RAG usa no QDRANT."
    )
    ferramenta_sql_habilitada: bool = Field(default=False)
    ferramenta_agendamento_habilitada: bool = Field(default=False)


class ConfiguracaoNegocio(ConfiguracaoNegocioBase, table=True):
    __tablename__ = "configuracao_negocio"

    id: int | None = Field(default=None, primary_key=True)
    cliente_vizu_id: uuid.UUID = Field(
        foreign_key="cliente_vizu.id", unique=True, index=True
    )
    cliente_vizu: "ClienteVizu" = Relationship(back_populates="configuracao")


class ConfiguracaoNegocioCreate(ConfiguracaoNegocioBase):
    cliente_vizu_id: uuid.UUID


class ConfiguracaoNegocioRead(ConfiguracaoNegocioBase):
    id: int
    cliente_vizu_id: uuid.UUID


class ConfiguracaoNegocioUpdate(SQLModel):
    prompt_base: str | None = None
    horario_funcionamento: dict[str, Any] | None = None
    ferramenta_rag_habilitada: bool | None = None
    collection_rag: str | None = None
    ferramenta_sql_habilitada: bool | None = None
    ferramenta_agendamento_habilitada: bool | None = None
