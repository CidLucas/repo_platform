import uuid
from typing import List, Optional, TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel, Column
from sqlalchemy import String, Enum as pgEnum
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlalchemy import Text, Boolean, JSON

from .enums import TipoCliente, TierCliente

# Importações de modelos locais com forward references resolvidas
from .cliente_final import ClienteFinal
from .fonte_de_dados import FonteDeDados
from .credencial_servico_externo import CredencialServicoExterno

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

    id: Optional[uuid.UUID] = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pgUUID(as_uuid=True), primary_key=True),
    )

    api_key: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(255), unique=True, index=True),
    )

    # --- Configuração embutida (migrada desde `configuracao_negocio`) ---
    horario_funcionamento: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    prompt_base: Optional[str] = Field(default=None, sa_column=Column(Text))

    # PHASE 1: Dynamic Tool Allocation - NEW enabled_tools list
    # This replaces the 3 boolean flags below
    enabled_tools: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
        description="List of enabled tool names (e.g., ['executar_rag_cliente', 'executar_sql_agent'])"
    )

    # LEGACY: Boolean flags (deprecated, kept for backward compatibility)
    # Will be removed in v1.1 after migration is complete
    ferramenta_rag_habilitada: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default="false"),
        description="DEPRECATED: Use enabled_tools instead"
    )

    ferramenta_sql_habilitada: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default="false"),
        description="DEPRECATED: Use enabled_tools instead"
    )

    ferramenta_agendamento_habilitada: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default="false"),
        description="DEPRECATED: Use enabled_tools instead"
    )

    collection_rag: Optional[str] = Field(default=None, sa_column=Column(String))

    clientes_finais: List["ClienteFinal"] = Relationship(back_populates="cliente_vizu")
    fontes_de_dados: List["FonteDeDados"] = Relationship(back_populates="cliente_vizu")
    credenciais: List["CredencialServicoExterno"] = Relationship(
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

    def get_enabled_tools_list(self) -> List[str]:
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
    horario_funcionamento: Optional[dict] = None
    prompt_base: Optional[str] = None
    # PHASE 1: New enabled_tools list
    enabled_tools: List[str] = []
    # Legacy boolean flags (deprecated)
    ferramenta_rag_habilitada: Optional[bool] = False
    ferramenta_sql_habilitada: Optional[bool] = False
    ferramenta_agendamento_habilitada: Optional[bool] = False
    collection_rag: Optional[str] = None


class ClienteVizuRead(ClienteVizuBase):
    id: uuid.UUID
    api_key: str
    horario_funcionamento: Optional[dict] = None
    prompt_base: Optional[str] = None
    # PHASE 1: New enabled_tools list
    enabled_tools: List[str] = []
    # Legacy boolean flags (deprecated, kept for backward compatibility)
    ferramenta_rag_habilitada: bool = False
    ferramenta_sql_habilitada: bool = False
    ferramenta_agendamento_habilitada: bool = False
    collection_rag: Optional[str] = None


class ClienteVizuReadWithRelations(ClienteVizuRead):
    configuracao: Optional["ConfiguracaoNegocioRead"] = None


class ClienteVizuUpdate(SQLModel):
    """Schema for updating a client, all fields are optional."""

    nome_empresa: Optional[str] = None
    tipo_cliente: Optional[TipoCliente] = None
    tier: Optional[TierCliente] = None
