# vizu_models/__init__.py (Versão Corrigida para Exportação)

from sqlmodel import SQLModel

# Agent Types (shared across all agents/LangGraph flows)
from .agent_types import (
    # Chat/Message
    AgentChatRequest,
    AgentChatResponse,
    # Client Context
    ClientContextResponse,
    ElicitationOption,
    ElicitationRequest,
    ElicitationResponse,
    # Elicitation
    ElicitationType,
    # Model/LLM
    ModelInfo,
    ToolExecutionResult,
    # Tool Management
    ToolInfo,
)
from .cliente_final import (
    ClienteFinal,
    ClienteFinalCreate,
    ClienteFinalRead,
    ClienteFinalUpdate,
)
from .cliente_vizu import (
    ClienteVizu,
    ClienteVizuCreate,
    ClienteVizuRead,
    ClienteVizuReadWithRelations,
    ClienteVizuUpdate,
)

from .conversa import (
    Conversa,
    ConversaBase,
    ConversaCreate,
    ConversaInDB,
    Mensagem,
    MensagemBase,
    MensagemCreate,
    MensagemInDB,
    Remetente,
)
from .credencial_servico_externo import (
    CredencialServicoExterno,
    CredencialServicoExternoBase,
    CredencialServicoExternoCreate,
    CredencialServicoExternoInDB,
)
from .enums import ContextSection, TierCliente, TipoCliente, TipoFonte, ToolCategory

# Context 2.0 - Modular Client Context
from .context_schemas import (
    AvailableTools,
    BrandVoice,
    CompanyProfile,
    CurrentMoment,
    DataSchema,
    Policies,
    SECTION_SCHEMAS,
    TeamMember,
    TeamStructure,
    get_section_schema,
    validate_section_content,
)
from .client_context_section import (
    BulkSectionResponse,
    BulkSectionUpsert,
    ClientContextSection,
    ClientContextSectionBase,
    ClientContextSectionCreate,
    ClientContextSectionRead,
    ClientContextSectionSummary,
    ClientContextSectionUpdate,
)

# Experiment Suite (Dataset Generation)
from .experiment import (
    CaseOutcome,
    ClassificationResult,
    ClientVariant,
    ExperimentCase,
    ExperimentManifest,
    ExperimentProgress,
    ExperimentRun,
    ExperimentRunSummary,
    ExperimentStatus,
    HitlRoutingConfig,
    LangfuseConfig,
    TestCaseDefinition,
)
from .fonte_de_dados import FonteDeDados

# HITL (Human-in-the-Loop) support
from .hitl import (
    HitlConfig,
    HitlCriteriaType,
    HitlCriterion,
    HitlDecision,
    HitlFeedbackType,
    HitlQueueStats,
    HitlReview,
    HitlReviewCreate,
    HitlReviewRead,
    HitlReviewStatus,
    HitlReviewUpdate,
)

# Integration models
from .integration import (
    IntegrationConfig,
    IntegrationProvider,
    IntegrationTokens,
    OAuthTokenResponse,
)
from .knowledge_base_config import (
    KnowledgeBaseConfig,
    KnowledgeBaseConfigCreate,
    KnowledgeBaseConfigRead,
    KnowledgeBaseConfigUpdate,
    RagSearchConfig,
)

# MCP Resources & Prompts support
from .prompt_template import (
    PromptTemplate,
    PromptTemplateCreate,
    PromptTemplateRead,
    PromptTemplateUpdate,
)
from .safe_client_context import InternalClientContext, SafeClientContext
from .seed_clients import SEED_CLIENTS, get_all_rag_collections, get_client_by_name

# Standalone Agent models
from .standalone_agent import (
    AgentCatalog,
    AgentCatalogBase,
    AgentCatalogRead,
    StandaloneAgentSession,
    StandaloneAgentSessionBase,
    StandaloneAgentSessionCreate,
    StandaloneAgentSessionRead,
)
from .sql_schema_config import (
    SqlTableConfig,
    SqlTableConfigCreate,
    SqlTableConfigRead,
    SqlTableConfigUpdate,
)

# Structured Data (for SQL query results display)
from .structured_data import (
    ColumnType,
    StructuredDataColumn,
    StructuredDataResponse,
)
from .vizu_client_context import VizuClientContext


class Base(SQLModel):
    """
    Classe base que herda de SQLModel. Usada pelo Alembic como target_metadata.
    """

    pass


__all__ = [
    "Base",
    "ClienteVizu",
    "ClienteVizuCreate",
    "ClienteVizuRead",
    "ClienteVizuReadWithRelations",
    "ClienteVizuUpdate",  # Deve ser a classe única ClienteVizuUpdate
    "CredencialServicoExterno",
    "CredencialServicoExternoBase",
    "CredencialServicoExternoCreate",
    "CredencialServicoExternoInDB",
    "FonteDeDados",
    "ClienteFinal",
    "ClienteFinalCreate",
    "ClienteFinalRead",
    "ClienteFinalUpdate",
    "Conversa",
    "ConversaBase",
    "ConversaCreate",
    "ConversaInDB",
    "Mensagem",
    "MensagemBase",
    "MensagemCreate",
    "MensagemInDB",
    "Remetente",
    "VizuClientContext",
    "SafeClientContext",
    "InternalClientContext",
    "SEED_CLIENTS",
    "get_client_by_name",
    "get_all_rag_collections",
    "TipoCliente",
    "TierCliente",
    "TipoFonte",
    "ToolCategory",
    "ContextSection",
    # Context 2.0 - Modular Context Schemas
    "CompanyProfile",
    "BrandVoice",
    "CurrentMoment",
    "TeamStructure",
    "TeamMember",
    "Policies",
    "DataSchema",
    "AvailableTools",
    "SECTION_SCHEMAS",
    "get_section_schema",
    "validate_section_content",
    # Context 2.0 - Section Storage
    "ClientContextSection",
    "ClientContextSectionBase",
    "ClientContextSectionCreate",
    "ClientContextSectionRead",
    "ClientContextSectionUpdate",
    "ClientContextSectionSummary",
    "BulkSectionUpsert",
    "BulkSectionResponse",
    # MCP Resources & Prompts support
    "PromptTemplate",
    "PromptTemplateCreate",
    "PromptTemplateRead",
    "PromptTemplateUpdate",
    "KnowledgeBaseConfig",
    "KnowledgeBaseConfigCreate",
    "KnowledgeBaseConfigRead",
    "KnowledgeBaseConfigUpdate",
    # SQL Schema Config (Text-to-SQL semantic context)
    "SqlTableConfig",
    "SqlTableConfigCreate",
    "SqlTableConfigRead",
    "SqlTableConfigUpdate",
    # Agent Types (shared across all agents)
    "ElicitationType",
    "ElicitationOption",
    "ElicitationRequest",
    "ElicitationResponse",
    "ToolInfo",
    "ToolExecutionResult",
    "ModelInfo",
    "AgentChatRequest",
    "AgentChatResponse",
    "ClientContextResponse",
    # HITL (Human-in-the-Loop)
    "HitlCriteriaType",
    "HitlReviewStatus",
    "HitlFeedbackType",
    "HitlCriterion",
    "HitlConfig",
    "HitlReview",
    "HitlReviewCreate",
    "HitlReviewRead",
    "HitlReviewUpdate",
    "HitlQueueStats",
    "HitlDecision",
    # Experiment Suite
    "ExperimentStatus",
    "CaseOutcome",
    "ClassificationResult",
    "TestCaseDefinition",
    "ClientVariant",
    "HitlRoutingConfig",
    "LangfuseConfig",
    "ExperimentManifest",
    "ExperimentRunSummary",
    "ExperimentProgress",
    "ExperimentRun",
    "ExperimentCase",
    # Integrations
    "IntegrationConfig",
    "IntegrationTokens",
    "OAuthTokenResponse",
    "IntegrationProvider",
    # Structured Data (SQL results display)
    "ColumnType",
    "StructuredDataColumn",
    "StructuredDataResponse",
]
