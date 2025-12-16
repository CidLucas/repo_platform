import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, Boolean, String, Text
from sqlalchemy import Enum as pgEnum
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlmodel import Column, Field, Relationship, SQLModel

# Importações de modelos locais com forward references resolvidas
from .cliente_final import ClienteFinal
from .credencial_servico_externo import CredencialServicoExterno
from .enums import TierCliente, TipoCliente
from .fonte_de_dados import FonteDeDados

if TYPE_CHECKING:
    from .configuracao_negocio import ConfiguracaoNegocio, ConfiguracaoNegocioRead


class ClienteVizuBase(SQLModel):
    nome_empresa: str = Field(max_length=255)
    tipo_cliente: TipoCliente = Field(
        sa_column=Column(
            pgEnum(TipoCliente, name="tipo_cliente_enum")
        )  # CORRIGIDO: Removido create_type=False
    )
    tier: TierCliente = Field(
        sa_column=Column(
            pgEnum(TierCliente, name="tier_cliente_enum")
        )  # CORRIGIDO: Removido create_type=False
    )


class ClienteVizu(ClienteVizuBase, table=True):
    __tablename__ = "cliente_vizu"

    id: uuid.UUID | None = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pgUUID(as_uuid=True), primary_key=True),
    )

    api_key: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(255), unique=True, index=True),
    )

    # --- Configuração embutida (migrada desde `configuracao_negocio`) ---
    horario_funcionamento: dict | None = Field(default=None, sa_column=Column(JSON))

    prompt_base: str | None = Field(default=None, sa_column=Column(Text))

    # PHASE 1: Dynamic Tool Allocation - NEW enabled_tools list
    # This replaces the 3 boolean flags below
    enabled_tools: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
        description="List of enabled tool names (e.g., ['executar_rag_cliente', 'executar_sql_agent'])"
    )



    collection_rag: str | None = Field(default=None, sa_column=Column(String))

    clientes_finais: list["ClienteFinal"] = Relationship(back_populates="cliente_vizu")
    fontes_de_dados: list["FonteDeDados"] = Relationship(back_populates="cliente_vizu")
    credenciais: list["CredencialServicoExterno"] = Relationship(
        back_populates="cliente_vizu"
    )
    # Legacy/compat relationship to the old ConfiguracaoNegocio table.
    # Kept as a Relationship so SQLAlchemy mappers remain consistent during
    # the migration rollout. This will be unused once the legacy table is
    # removed in a later migration.
    from typing import Optional as _Optional

    configuracao: _Optional["ConfiguracaoNegocio"] = Relationship(
        back_populates="cliente_vizu"
    )

    def get_enabled_tools_list(self) -> list[str]:
        """
        Returns enabled tools list, computing from legacy booleans if needed.

        This helper ensures backward compatibility during migration:
        - If enabled_tools is populated, use it
        - Otherwise, compute from legacy boolean flags
        """
        if self.enabled_tools:
            return self.enabled_tools

        # Fallback: compute from legacy booleans
        tools = []
        if self.ferramenta_rag_habilitada:
            tools.append("executar_rag_cliente")
        if self.ferramenta_sql_habilitada:
            tools.append("executar_sql_agent")
        if self.ferramenta_agendamento_habilitada:
            tools.append("agendar_consulta")
        return tools


class ClienteVizuCreate(ClienteVizuBase):
    # Optional config fields for creation
    horario_funcionamento: dict | None = None
    prompt_base: str | None = None
    # PHASE 1: New enabled_tools list
    enabled_tools: list[str] = []
    # Legacy boolean flags (deprecated)
    ferramenta_rag_habilitada: bool | None = False
    ferramenta_sql_habilitada: bool | None = False
    ferramenta_agendamento_habilitada: bool | None = False
    collection_rag: str | None = None


class ClienteVizuRead(ClienteVizuBase):
    id: uuid.UUID
    api_key: str
    horario_funcionamento: dict | None = None
    prompt_base: str | None = None
    # PHASE 1: New enabled_tools list
    enabled_tools: list[str] = []
    # Legacy boolean flags (deprecated, kept for backward compatibility)
    ferramenta_rag_habilitada: bool = False
    ferramenta_sql_habilitada: bool = False
    ferramenta_agendamento_habilitada: bool = False
    collection_rag: str | None = None


class ClienteVizuReadWithRelations(ClienteVizuRead):
    configuracao: Optional["ConfiguracaoNegocioRead"] = None


class ClienteVizuUpdate(SQLModel):
    """Schema for updating a client, all fields are optional."""

    nome_empresa: str | None = None
    tipo_cliente: TipoCliente | None = None
    tier: TierCliente | None = None
