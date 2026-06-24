# blu_models/__init__.py (Versão Corrigida para Exportação)
from __future__ import annotations

from sqlmodel import SQLModel

# Agent Types (shared across all agents/LangGraph flows)
from blu_models.agent_types import (
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
from blu_models.cliente_final import (
    ClienteFinal,
    ClienteFinalCreate,
    ClienteFinalRead,
    ClienteFinalUpdate,
)
from blu_models.cliente_blu import (
    ClienteBlu,
    ClienteBluCreate,
    ClienteBluRead,
    ClienteBluReadWithRelations,
    ClienteBluUpdate,
)

from blu_models.conversa import (
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
from blu_models.credencial_servico_externo import (
    CredencialServicoExterno,
    CredencialServicoExternoBase,
    CredencialServicoExternoCreate,
    CredencialServicoExternoInDB,
)
from blu_models.enums import ContextSection, TierCliente, TipoCliente, TipoFonte, ToolCategory

# Context 2.0 - Modular Client Context
from blu_models.context_schemas import (
    AvailableTools,
    BrandVoice,
    CompanyProfile,
    DataSchema,
    MetaEntityType,
    EntitySummary,
    KnowledgeGraphSummary,
    Policies,
    SECTION_SCHEMAS,
    SharedMemoryMetaEntry,
    SharedMemoryMetaQuery,
    SharedMemoryMetaUpsertPayload,
    TeamMember,
    TeamStructure,
    get_section_schema,
    validate_meta_entity_type,
    validate_section_content,
)
from blu_models.client_context_section import (
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
from blu_models.experiment import (
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
from blu_models.fonte_de_dados import FonteDeDados

# HITL (Human-in-the-Loop) support
from blu_models.hitl import (
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
from blu_models.integration import (
    IntegrationConfig,
    IntegrationProvider,
    IntegrationTokens,
    OAuthTokenResponse,
)
from blu_models.knowledge_base_config import (
    KnowledgeBaseConfig,
    KnowledgeBaseConfigCreate,
    KnowledgeBaseConfigRead,
    KnowledgeBaseConfigUpdate,
    RagSearchConfig,
)

# MCP Resources & Prompts support
from blu_models.prompt_template import (
    PromptTemplate,
    PromptTemplateCreate,
    PromptTemplateRead,
    PromptTemplateUpdate,
)
from blu_models.safe_client_context import InternalClientContext, SafeClientContext
from blu_models.seed_clients import SEED_CLIENTS, get_all_rag_collections, get_client_by_name

# Standalone Agent models
from blu_models.standalone_agent import (
    AgentCatalog,
    AgentCatalogBase,
    AgentCatalogRead,
    StandaloneAgentSession,
    StandaloneAgentSessionBase,
    StandaloneAgentSessionCreate,
    StandaloneAgentSessionRead,
)
from blu_models.sql_schema_config import (
    SqlTableConfig,
    SqlTableConfigCreate,
    SqlTableConfigRead,
    SqlTableConfigUpdate,
)

# Structured Data (for SQL query results display)
from blu_models.structured_data import (
    ColumnType,
    StructuredDataColumn,
    StructuredDataResponse,
)
from blu_models.blu_client_context import BluClientContext


class Base(SQLModel):
    """
    Classe base que herda de SQLModel. Usada pelo Alembic como target_metadata.
    """

    pass


__all__ = [
    "Base",
    "ClienteBlu",
    "ClienteBluCreate",
    "ClienteBluRead",
    "ClienteBluReadWithRelations",
    "ClienteBluUpdate",  # Deve ser a classe única ClienteBluUpdate
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
    "BluClientContext",
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
    "TeamStructure",
    "TeamMember",
    "Policies",
    "DataSchema",
    "AvailableTools",
    "EntitySummary",
    "KnowledgeGraphSummary",
    "SECTION_SCHEMAS",
    "get_section_schema",
    "validate_section_content",
    # Shared Business Memory Meta (Fase 4)
    "MetaEntityType",
    "SharedMemoryMetaEntry",
    "SharedMemoryMetaUpsertPayload",
    "SharedMemoryMetaQuery",
    "validate_meta_entity_type",
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
