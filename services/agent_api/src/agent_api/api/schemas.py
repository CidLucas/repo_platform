"""Request/response schemas for agent_api."""

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------


class ElicitationType(str, Enum):
    confirmation = "confirmation"
    selection = "selection"
    text_input = "text_input"
    date_time = "date_time"


class ElicitationOption(BaseModel):
    value: str
    label: str
    description: str | None = None


class ElicitationRequest(BaseModel):
    elicitation_id: str
    type: ElicitationType
    message: str
    options: list[ElicitationOption] | None = None
    metadata: dict[str, Any] | None = None


class ElicitationResponseBody(BaseModel):
    elicitation_id: str
    response: Any


# ---------------------------------------------------------------------------
# Supervisor chat
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str
    session_id: str
    model: str | None = None
    elicitation_response: ElicitationResponseBody | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    model_used: str | None = None
    elicitation_pending: ElicitationRequest | None = None
    structured_data: dict[str, Any] | None = None
    structured_data_list: list[dict[str, Any]] | None = None


# ---------------------------------------------------------------------------
# Standalone agent catalog + sessions
# ---------------------------------------------------------------------------


class AgentInfo(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None = None
    category: str | None = None
    icon: str | None = None
    tier_required: str = "BASIC"


class AgentDetailsResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None = None
    agent_config: dict
    prompt_name: str
    required_context: list | None = None
    required_files: dict | None = None
    requires_google: bool = False


class CreateSessionRequest(BaseModel):
    agent_catalog_id: UUID


class AgentChatRequest(BaseModel):
    message: str
    stream: bool = True


# ---------------------------------------------------------------------------
# Admin catalog management
# ---------------------------------------------------------------------------


class CatalogAgentCreateRequest(BaseModel):
    name: str
    description: str | None = None
    category: str | None = None
    icon: str | None = None
    agent_config: dict[str, Any] = Field(...)
    prompt_name: str
    required_context: list[dict[str, Any]] = Field(default_factory=list)
    required_files: dict[str, Any] = Field(default_factory=dict)
    requires_google: bool = False
    tier_required: str = "BASIC"
    is_active: bool = True
    workflow_graph: dict[str, Any] | None = None


class CatalogAgentUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    icon: str | None = None
    agent_config: dict[str, Any] | None = None
    prompt_name: str | None = None
    required_context: list[dict[str, Any]] | None = None
    required_files: dict[str, Any] | None = None
    requires_google: bool | None = None
    tier_required: str | None = None
    is_active: bool | None = None
    workflow_graph: dict[str, Any] | None = None


class CatalogAgentResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None = None
    category: str | None = None
    icon: str | None = None
    agent_config: dict[str, Any]
    prompt_name: str
    required_context: list[dict[str, Any]] = []
    required_files: dict[str, Any] = {}
    requires_google: bool = False
    tier_required: str = "BASIC"
    is_active: bool = True
    workflow_graph: dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ValidateToolsRequest(BaseModel):
    enabled_tools: list[str]
    tier: str = "BASIC"


class ValidateToolsResponse(BaseModel):
    valid: bool
    errors: list[str] = []
    warnings: list[str] = []


class PromptInfo(BaseModel):
    name: str
    source: str
    category: str | None = None
    description: str | None = None


class PromptDetailResponse(BaseModel):
    name: str
    content: str
    version: int
    variables: list[str] = []
    source: str


class PromptUpdateRequest(BaseModel):
    content: str


class PromptVersionInfo(BaseModel):
    version: int
    created_at: str | None = None
    labels: list[str] = []


class PromptVersionsResponse(BaseModel):
    name: str
    versions: list[PromptVersionInfo] = []


class ConfigFieldUpdate(BaseModel):
    value: str | bool


# ---------------------------------------------------------------------------
# Document upload
# ---------------------------------------------------------------------------


class DocumentUploadResponse(BaseModel):
    document_id: str
    file_name: str
    status: str
    size_bytes: int


class LinkDocumentRequest(BaseModel):
    document_id: str
