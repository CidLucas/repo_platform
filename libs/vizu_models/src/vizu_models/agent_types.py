# vizu_models/agent_types.py
"""
Tipos compartilhados para agentes LangGraph/MCP.

Este módulo contém modelos Pydantic usados por diferentes agentes e fluxos
do sistema Vizu. Ao centralizar aqui, garantimos:
- Consistência entre diferentes agentes (atendente, vendas, suporte, etc.)
- Reutilização de código
- Contratos claros entre serviços

Categorias:
1. Elicitation - Human-in-the-loop patterns
2. Tool Management - Tool info and permissions
3. Agent State - Shared state structures
4. Chat/Message - Request/response patterns
5. Structured Data - SQL query results display
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ============================================================================
# ELICITATION TYPES (Human-in-the-Loop)
# ============================================================================


class ElicitationType(Enum):
    """
    Tipos de elicitation suportados pelo sistema.

    Elicitation é o padrão que permite ao agente pausar e solicitar
    input do usuário antes de continuar uma operação.
    """

    CONFIRMATION = "confirmation"  # Sim/Não - binário
    SELECTION = "selection"  # Escolha entre opções predefinidas
    TEXT_INPUT = "text_input"  # Entrada de texto livre
    DATE_TIME = "date_time"  # Escolha de data/hora
    RATING = "rating"  # Avaliação (1-5 estrelas, NPS, etc.)
    FILE_UPLOAD = "file_upload"  # Upload de arquivo


class ElicitationOption(BaseModel):
    """
    Uma opção para elicitation do tipo SELECTION.

    Exemplo de uso:
    ```python
    options = [
        ElicitationOption(value="corte", label="Corte de Cabelo", description="30 min"),
        ElicitationOption(value="barba", label="Barba", description="20 min"),
        ElicitationOption(value="combo", label="Corte + Barba", description="45 min"),
    ]
    ```
    """

    value: str = Field(..., description="Valor interno usado pelo sistema")
    label: str = Field(..., description="Texto exibido ao usuário")
    description: str | None = Field(None, description="Descrição adicional")
    icon: str | None = Field(None, description="Ícone opcional (emoji ou nome)")
    disabled: bool = Field(False, description="Se a opção está desabilitada")

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "label": self.label,
            "description": self.description,
            "icon": self.icon,
            "disabled": self.disabled,
        }


class ElicitationRequest(BaseModel):
    """
    Pedido de elicitation retornado ao cliente quando o agente
    precisa de input do usuário para continuar.

    Este modelo é usado na resposta da API quando `elicitation_pending` != None.
    """

    elicitation_id: str = Field(..., description="ID único desta elicitation")
    type: ElicitationType = Field(..., description="Tipo de input necessário")
    message: str = Field(..., description="Mensagem/pergunta para o usuário")
    options: list[ElicitationOption] | None = Field(
        None, description="Opções disponíveis (para tipo SELECTION)"
    )
    metadata: dict[str, Any] | None = Field(
        None, description="Contexto adicional (tool name, params originais, etc.)"
    )
    timeout_seconds: int | None = Field(
        None, description="Tempo limite para resposta (None = sem limite)"
    )
    required: bool = Field(
        True, description="Se a resposta é obrigatória ou pode ser pulada"
    )


class ElicitationResponse(BaseModel):
    """
    Resposta do usuário a uma elicitation pendente.

    Enviado no body do request /chat para resumir um fluxo pausado.
    """

    elicitation_id: str = Field(..., description="ID da elicitation sendo respondida")
    response: Any = Field(
        ...,
        description="Resposta do usuário: bool (confirmation), str (selection/text), dict (date_time)",
    )
    skipped: bool = Field(
        False, description="Se o usuário pulou a elicitation (quando required=False)"
    )


# ============================================================================
# TOOL MANAGEMENT TYPES
# ============================================================================


class ToolInfo(BaseModel):
    """
    Informação sobre uma ferramenta disponível para o agente.

    Usado para listar tools disponíveis e seu status (habilitado/desabilitado).

    PHASE 1: Dynamic Tool Allocation
    - tier_required: Tier mínimo para acessar a ferramenta
    - docker_mcp_integration: Nome do servidor Docker MCP se aplicável
    """

    name: str = Field(..., description="Nome técnico da ferramenta")
    description: str | None = Field(None, description="Descrição da ferramenta")
    enabled: bool = Field(True, description="Se está habilitada para este cliente")
    category: str | None = Field(
        None, description="Categoria (rag, sql, scheduling, docker_mcp)"
    )
    requires_confirmation: bool = Field(
        False, description="Se requer confirmação do usuário antes de executar"
    )
    tier_required: str = Field(
        "BASIC", description="Tier mínimo requerido (BASIC, SME, ENTERPRISE)"
    )
    docker_mcp_integration: str | None = Field(
        None, description="Nome do servidor Docker MCP se aplicável (github, slack, etc.)"
    )


class ToolExecutionResult(BaseModel):
    """
    Resultado da execução de uma ferramenta.

    Usado para padronizar retornos de tools entre diferentes agentes.
    """

    success: bool = Field(..., description="Se a execução foi bem-sucedida")
    result: Any | None = Field(None, description="Resultado da execução")
    error: str | None = Field(None, description="Mensagem de erro se falhou")
    tool_name: str = Field(..., description="Nome da ferramenta executada")
    execution_time_ms: int | None = Field(
        None, description="Tempo de execução em ms"
    )
    metadata: dict[str, Any] | None = Field(None, description="Metadados adicionais")


# ============================================================================
# MODEL/LLM TYPES
# ============================================================================


class ModelInfo(BaseModel):
    """
    Informação sobre um modelo LLM disponível.
    """

    name: str = Field(..., description="Nome do modelo (ex: gpt-oss:20b)")
    provider: str = Field(..., description="Provider (ollama, ollama_cloud, openai)")
    tier: str = Field(..., description="Tier (fast, default, powerful)")
    description: str | None = Field(None, description="Descrição do modelo")
    max_tokens: int | None = Field(None, description="Máximo de tokens suportados")
    supports_tools: bool = Field(True, description="Se suporta function calling")


# ============================================================================
# CHAT/MESSAGE TYPES (Shared between agents)
# ============================================================================


class AgentChatRequest(BaseModel):
    """
    Request base para chat com qualquer agente do sistema.

    Cada agente pode estender este modelo adicionando campos específicos.
    """

    message: str = Field(..., description="Mensagem do usuário")
    session_id: str = Field(..., description="ID único da sessão")
    model: str | None = Field(
        None, description="Modelo LLM a usar (sobrescreve padrão)"
    )
    elicitation_response: ElicitationResponse | None = Field(
        None, description="Resposta a uma elicitation pendente"
    )
    metadata: dict[str, Any] | None = Field(
        None, description="Metadados extras (canal, device, etc.)"
    )


class AgentChatResponse(BaseModel):
    """
    Response base para chat com qualquer agente do sistema.
    """

    response: str = Field(..., description="Resposta do agente")
    session_id: str = Field(..., description="ID da sessão")
    model_used: str | None = Field(None, description="Modelo LLM utilizado")
    elicitation_pending: ElicitationRequest | None = Field(
        None, description="Se presente, agente precisa de input do usuário"
    )
    tools_called: list[str] | None = Field(
        None, description="Lista de tools chamadas nesta interação"
    )
    trace_id: str | None = Field(
        None, description="ID do trace para observabilidade (Langfuse)"
    )
    # Structured data for rich table display (from SQL queries)
    structured_data: "StructuredDataResponse | None" = Field(
        None,
        description="Structured tabular data for interactive display (sorting, filtering, export)",
    )


# ============================================================================
# CLIENT CONTEXT RESPONSE (for /context endpoints)
# ============================================================================


class ClientContextResponse(BaseModel):
    """
    Contexto do cliente autenticado retornado por endpoints /context.

    Contém apenas dados seguros - nunca IDs internos, API keys, etc.

    PHASE 1: Dynamic Tool Allocation
    - enabled_tools: Lista de nomes de ferramentas habilitadas (source of truth)
    - tier: Tier do cliente determina acesso baseline a ferramentas
    - docker_mcp_enabled: Se integrações Docker MCP estão disponíveis
    """

    nome_empresa: str = Field(..., description="Nome da empresa")
    tier: str = Field("BASIC", description="Tier do cliente (BASIC, SME, ENTERPRISE)")

    # PHASE 1: Dynamic tool list - single source of truth
    enabled_tools: list[str] = Field(
        default_factory=list,
        description="Lista de nomes de ferramentas habilitadas (ex: ['executar_rag_cliente', 'executar_sql_agent'])"
    )

    available_tools: list[ToolInfo] = Field(
        default_factory=list, description="Ferramentas disponíveis e seus status"
    )

    # Context 2.0: Structured configuration
    has_custom_prompt: bool = Field(False, description="Se tem prompt customizado no Langfuse ou available_tools")
    has_business_hours: bool = Field(False, description="Se tem horário de funcionamento configurado")
    has_rag_collection: bool = Field(False, description="Se tem coleção RAG configurada")

    # PHASE 1: Docker MCP integration flag
    docker_mcp_enabled: bool = Field(
        False, description="Se integrações Docker MCP estão disponíveis"
    )


# Resolve forward reference for StructuredDataResponse
# Import at end to avoid circular imports
from .structured_data import StructuredDataResponse  # noqa: E402

AgentChatResponse.model_rebuild()
