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
"""

from enum import Enum
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field


# ============================================================================
# ELICITATION TYPES (Human-in-the-Loop)
# ============================================================================

class ElicitationType(str, Enum):
    """
    Tipos de elicitation suportados pelo sistema.

    Elicitation é o padrão que permite ao agente pausar e solicitar
    input do usuário antes de continuar uma operação.
    """
    CONFIRMATION = "confirmation"      # Sim/Não - binário
    SELECTION = "selection"            # Escolha entre opções predefinidas
    TEXT_INPUT = "text_input"          # Entrada de texto livre
    DATE_TIME = "date_time"            # Escolha de data/hora
    RATING = "rating"                  # Avaliação (1-5 estrelas, NPS, etc.)
    FILE_UPLOAD = "file_upload"        # Upload de arquivo


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
    description: Optional[str] = Field(None, description="Descrição adicional")
    icon: Optional[str] = Field(None, description="Ícone opcional (emoji ou nome)")
    disabled: bool = Field(False, description="Se a opção está desabilitada")

    def to_dict(self) -> Dict[str, Any]:
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
    options: Optional[List[ElicitationOption]] = Field(
        None,
        description="Opções disponíveis (para tipo SELECTION)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Contexto adicional (tool name, params originais, etc.)"
    )
    timeout_seconds: Optional[int] = Field(
        None,
        description="Tempo limite para resposta (None = sem limite)"
    )
    required: bool = Field(
        True,
        description="Se a resposta é obrigatória ou pode ser pulada"
    )


class ElicitationResponse(BaseModel):
    """
    Resposta do usuário a uma elicitation pendente.

    Enviado no body do request /chat para resumir um fluxo pausado.
    """
    elicitation_id: str = Field(..., description="ID da elicitation sendo respondida")
    response: Any = Field(
        ...,
        description="Resposta do usuário: bool (confirmation), str (selection/text), dict (date_time)"
    )
    skipped: bool = Field(
        False,
        description="Se o usuário pulou a elicitation (quando required=False)"
    )


# ============================================================================
# TOOL MANAGEMENT TYPES
# ============================================================================

class ToolInfo(BaseModel):
    """
    Informação sobre uma ferramenta disponível para o agente.

    Usado para listar tools disponíveis e seu status (habilitado/desabilitado).
    """
    name: str = Field(..., description="Nome técnico da ferramenta")
    description: Optional[str] = Field(None, description="Descrição da ferramenta")
    enabled: bool = Field(True, description="Se está habilitada para este cliente")
    category: Optional[str] = Field(None, description="Categoria (rag, sql, scheduling, etc.)")
    requires_confirmation: bool = Field(
        False,
        description="Se requer confirmação do usuário antes de executar"
    )


class ToolExecutionResult(BaseModel):
    """
    Resultado da execução de uma ferramenta.

    Usado para padronizar retornos de tools entre diferentes agentes.
    """
    success: bool = Field(..., description="Se a execução foi bem-sucedida")
    result: Optional[Any] = Field(None, description="Resultado da execução")
    error: Optional[str] = Field(None, description="Mensagem de erro se falhou")
    tool_name: str = Field(..., description="Nome da ferramenta executada")
    execution_time_ms: Optional[int] = Field(None, description="Tempo de execução em ms")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadados adicionais")


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
    description: Optional[str] = Field(None, description="Descrição do modelo")
    max_tokens: Optional[int] = Field(None, description="Máximo de tokens suportados")
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
    model: Optional[str] = Field(
        None,
        description="Modelo LLM a usar (sobrescreve padrão)"
    )
    elicitation_response: Optional[ElicitationResponse] = Field(
        None,
        description="Resposta a uma elicitation pendente"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Metadados extras (canal, device, etc.)"
    )


class AgentChatResponse(BaseModel):
    """
    Response base para chat com qualquer agente do sistema.
    """
    response: str = Field(..., description="Resposta do agente")
    session_id: str = Field(..., description="ID da sessão")
    model_used: Optional[str] = Field(None, description="Modelo LLM utilizado")
    elicitation_pending: Optional[ElicitationRequest] = Field(
        None,
        description="Se presente, agente precisa de input do usuário"
    )
    tools_called: Optional[List[str]] = Field(
        None,
        description="Lista de tools chamadas nesta interação"
    )
    trace_id: Optional[str] = Field(
        None,
        description="ID do trace para observabilidade (Langfuse)"
    )


# ============================================================================
# CLIENT CONTEXT RESPONSE (for /context endpoints)
# ============================================================================

class ClientContextResponse(BaseModel):
    """
    Contexto do cliente autenticado retornado por endpoints /context.

    Contém apenas dados seguros - nunca IDs internos, API keys, etc.
    """
    nome_empresa: str = Field(..., description="Nome da empresa")
    ferramenta_rag_habilitada: bool = Field(..., description="Se RAG está habilitado")
    ferramenta_sql_habilitada: bool = Field(..., description="Se SQL Agent está habilitado")
    collection_rag: Optional[str] = Field(None, description="Nome da collection RAG")
    available_tools: List[ToolInfo] = Field(..., description="Ferramentas e seus status")
    horario_funcionamento: Optional[Dict[str, Any]] = Field(
        None,
        description="Horário de funcionamento configurado"
    )
    has_custom_prompt: bool = Field(False, description="Se tem prompt customizado")
    tier: Optional[str] = Field(None, description="Tier do cliente (starter, pro, enterprise)")
