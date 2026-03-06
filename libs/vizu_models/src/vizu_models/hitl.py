# vizu_models/hitl.py
"""
Human-in-the-Loop (HITL) Models and Configuration

Este módulo define:
1. HitlReview - Registro de cada interação enviada para revisão humana
2. HitlConfig - Configuração dos critérios de roteamento para HITL
3. HitlCriteria - Enum dos critérios disponíveis para roteamento
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlmodel import JSON, Column, SQLModel
from sqlmodel import Field as SQLField

# ============================================================================
# ENUMS
# ============================================================================


class HitlCriteriaType(Enum):
    """Tipos de critérios para roteamento HITL."""

    LOW_CONFIDENCE = "low_confidence"  # Confiança da LLM baixa
    ELICITATION_PENDING = "elicitation_pending"  # Elicitation em aberto
    TOOL_CALL_FAILED = "tool_call_failed"  # Ferramenta falhou
    KEYWORD_TRIGGER = "keyword_trigger"  # Palavras-chave detectadas
    FIRST_N_MESSAGES = "first_n_messages"  # Primeiras N mensagens de cliente novo
    RANDOM_SAMPLE = "random_sample"  # Amostragem aleatória
    MANUAL_FLAG = "manual_flag"  # Marcação manual
    SENTIMENT_NEGATIVE = "sentiment_negative"  # Sentimento negativo detectado
    LONG_RESPONSE_TIME = "long_response_time"  # Resposta demorou muito


class HitlReviewStatus(Enum):
    """Status de uma review HITL."""

    PENDING = "pending"  # Aguardando revisão
    APPROVED = "approved"  # Resposta aprovada como está
    CORRECTED = "corrected"  # Resposta corrigida pelo revisor
    REJECTED = "rejected"  # Resposta rejeitada/inválida
    ESCALATED = "escalated"  # Escalado para nível superior
    EXPIRED = "expired"  # Expirou sem revisão


class HitlFeedbackType(Enum):
    """Tipos de feedback do revisor."""

    CORRECT = "correct"  # Resposta correta
    PARTIALLY_CORRECT = "partially_correct"  # Parcialmente correta
    INCORRECT = "incorrect"  # Resposta incorreta
    HARMFUL = "harmful"  # Resposta potencialmente prejudicial
    OFF_TOPIC = "off_topic"  # Fora do escopo


# ============================================================================
# CONFIGURATION MODELS (Pydantic - not stored in DB directly)
# ============================================================================


class HitlCriterion(BaseModel):
    """Um critério individual de roteamento HITL."""

    type: HitlCriteriaType
    enabled: bool = True
    priority: int = 1  # Maior = mais prioritário
    params: dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True

    # Params examples:
    # - low_confidence: {"threshold": 0.7}
    # - keyword_trigger: {"keywords": ["não sei", "não tenho certeza"]}
    # - first_n_messages: {"n": 3}
    # - random_sample: {"rate": 0.05}  # 5% das mensagens


class HitlConfig(BaseModel):
    """
    Configuração completa do sistema HITL para um cliente.

    Pode ser armazenada como JSON em clientes_vizu.available_tools ou tabela dedicada.
    """

    enabled: bool = False
    criteria: list[HitlCriterion] = Field(default_factory=list)

    # Queue settings
    queue_ttl_hours: int = 24  # Tempo máximo na fila antes de expirar
    max_pending_per_client: int = 100  # Limite de pendências por cliente

    # Notification settings
    notify_on_pending: bool = False
    notify_email: str | None = None
    notify_webhook_url: str | None = None

    # Dataset settings (Langfuse integration)
    auto_add_to_dataset: bool = True
    dataset_name: str | None = None  # Nome do dataset no Langfuse

    class Config:
        use_enum_values = True

    @classmethod
    def default_config(cls) -> "HitlConfig":
        """Configuração padrão com critério de baixa confiança."""
        return cls(
            enabled=True,
            criteria=[
                HitlCriterion(
                    type=HitlCriteriaType.LOW_CONFIDENCE,
                    enabled=True,
                    priority=10,
                    params={"threshold": 0.7},
                ),
            ],
            auto_add_to_dataset=True,
        )


# ============================================================================
# DATABASE MODELS (SQLModel)
# ============================================================================


class HitlReviewBase(SQLModel):
    """Campos base para HitlReview."""

    # Identificadores
    session_id: str = SQLField(index=True)
    client_id: UUID = SQLField(index=True)
    cliente_final_id: int | None = SQLField(default=None, index=True)

    # Conteúdo da interação
    user_message: str
    agent_response: str

    # Metadata do roteamento
    criteria_triggered: str  # HitlCriteriaType value
    confidence_score: float | None = None
    criteria_details: dict[str, Any] = SQLField(
        default_factory=dict, sa_column=Column(JSON)
    )

    # Metadata adicional (tools chamadas, trace_id, etc.)
    trace_id: str | None = None
    tools_called: list[str] = SQLField(default_factory=list, sa_column=Column(JSON))
    model_used: str | None = None

    # Contexto (para reproduzir a situação)
    conversation_context: list[dict[str, Any]] = SQLField(
        default_factory=list, sa_column=Column(JSON)
    )


class HitlReview(HitlReviewBase, table=True):
    """
    Registro de uma interação enviada para revisão humana.

    Table: hitl_review
    """

    __tablename__ = "hitl_review"

    id: UUID = SQLField(default_factory=uuid4, primary_key=True)

    # Status e timestamps
    status: str = SQLField(default=HitlReviewStatus.PENDING.value, index=True)
    created_at: datetime = SQLField(default_factory=datetime.utcnow)
    reviewed_at: datetime | None = None
    expires_at: datetime | None = None

    # Review data (preenchido pelo revisor)
    reviewer_id: str | None = None  # Email ou ID do revisor
    corrected_response: str | None = None
    feedback_type: str | None = None  # HitlFeedbackType value
    feedback_notes: str | None = None
    feedback_tags: list[str] = SQLField(default_factory=list, sa_column=Column(JSON))

    # Langfuse integration
    langfuse_dataset_item_id: str | None = None


# ============================================================================
# API SCHEMAS (Pydantic)
# ============================================================================


class HitlReviewCreate(HitlReviewBase):
    """Schema para criar um novo HitlReview."""

    pass


class HitlReviewRead(HitlReviewBase):
    """Schema para leitura de HitlReview."""

    id: UUID
    status: str
    created_at: datetime
    reviewed_at: datetime | None
    expires_at: datetime | None
    reviewer_id: str | None
    corrected_response: str | None
    feedback_type: str | None
    feedback_notes: str | None
    feedback_tags: list[str]


class HitlReviewUpdate(BaseModel):
    """Schema para atualizar um HitlReview (ação do revisor)."""

    status: HitlReviewStatus
    corrected_response: str | None = None
    feedback_type: HitlFeedbackType | None = None
    feedback_notes: str | None = None
    feedback_tags: list[str] = Field(default_factory=list)


class HitlQueueStats(BaseModel):
    """Estatísticas da fila HITL."""

    total_pending: int
    total_today: int
    by_criteria: dict[str, int]
    by_client: dict[str, int]
    avg_review_time_minutes: float | None
    oldest_pending_hours: float | None


class HitlDecision(BaseModel):
    """
    Resultado da avaliação de critérios HITL.

    Retornado pelo HitlService.evaluate() para indicar se uma
    interação deve ir para revisão.
    """

    should_review: bool
    criteria_triggered: HitlCriteriaType | None = None
    confidence_score: float | None = None
    details: dict[str, Any] = Field(default_factory=dict)
