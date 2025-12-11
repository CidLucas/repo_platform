"""
Schemas da API do Atendente Core.

Este módulo contém apenas schemas específicos da API HTTP deste serviço.
Tipos compartilhados entre agentes (Elicitation, ToolInfo, etc.) estão em vizu_models.agent_types.

Hierarquia:
- vizu_models.agent_types: Tipos base reutilizáveis
- Este arquivo: Extensões específicas do atendente
"""

from pydantic import BaseModel, Field
from typing import List

# Importa tipos compartilhados de vizu_models
from vizu_models import (
    ElicitationType,
    ElicitationOption,
    ElicitationRequest,
    ElicitationResponse,
    ToolInfo,
    ModelInfo,
    AgentChatRequest,
    AgentChatResponse,
    ClientContextResponse,
)

# Re-exporta para compatibilidade com imports existentes
__all__ = [
    # De vizu_models (re-export)
    "ElicitationType",
    "ElicitationOption",
    "ElicitationRequest",
    "ElicitationResponse",
    "ToolInfo",
    "ModelInfo",
    "ClientContextResponse",
    # Específicos do atendente
    "ChatRequest",
    "ChatResponse",
    "ModelsResponse",
]


# ============================================================================
# ATENDENTE-SPECIFIC SCHEMAS
# ============================================================================


class ChatRequest(AgentChatRequest):
    """
    Request para o endpoint /chat do atendente.

    Estende AgentChatRequest com campos específicos do atendente.
    """

    # Herda: message, session_id, model, elicitation_response, metadata
    # Campos específicos do atendente podem ser adicionados aqui
    pass


class ChatResponse(AgentChatResponse):
    """
    Response do endpoint /chat do atendente.

    Estende AgentChatResponse - campos adicionais podem ser incluídos.
    """

    # Herda: response, session_id, model_used, elicitation_pending, tools_called, trace_id
    # Campos específicos do atendente podem ser adicionados aqui
    pass


class ModelsResponse(BaseModel):
    """
    Resposta do endpoint /models listando modelos disponíveis.

    Específico para o atendente pois inclui informações do provider atual.
    """

    models: List[ModelInfo] = Field(..., description="Lista de modelos disponíveis")
    current_provider: str = Field(..., description="Provider atualmente configurado")
    default_model: str = Field(..., description="Modelo padrão em uso")
