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
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from sqlmodel import SQLModel, Field as SQLField, Column, JSON


# ============================================================================
# ENUMS
# ============================================================================

class HitlCriteriaType(str, Enum):
    """Tipos de critérios para roteamento HITL."""
    LOW_CONFIDENCE = "low_confidence"           # Confiança da LLM baixa
    ELICITATION_PENDING = "elicitation_pending"  # Elicitation em aberto
    TOOL_CALL_FAILED = "tool_call_failed"       # Ferramenta falhou
    KEYWORD_TRIGGER = "keyword_trigger"         # Palavras-chave detectadas
    FIRST_N_MESSAGES = "first_n_messages"       # Primeiras N mensagens de cliente novo
    RANDOM_SAMPLE = "random_sample"             # Amostragem aleatória
    MANUAL_FLAG = "manual_flag"                 # Marcação manual
    SENTIMENT_NEGATIVE = "sentiment_negative"   # Sentimento negativo detectado
    LONG_RESPONSE_TIME = "long_response_time"   # Resposta demorou muito


class HitlReviewStatus(str, Enum):
    """Status de uma review HITL."""
    PENDING = "pending"           # Aguardando revisão
    APPROVED = "approved"         # Resposta aprovada como está
    CORRECTED = "corrected"       # Resposta corrigida pelo revisor
    REJECTED = "rejected"         # Resposta rejeitada/inválida
    ESCALATED = "escalated"       # Escalado para nível superior
    EXPIRED = "expired"           # Expirou sem revisão


class HitlFeedbackType(str, Enum):
    """Tipos de feedback do revisor."""
    CORRECT = "correct"           # Resposta correta
    PARTIALLY_CORRECT = "partially_correct"  # Parcialmente correta
    INCORRECT = "incorrect"       # Resposta incorreta
    HARMFUL = "harmful"           # Resposta potencialmente prejudicial
    OFF_TOPIC = "off_topic"       # Fora do escopo


# ============================================================================
# CONFIGURATION MODELS (Pydantic - not stored in DB directly)
# ============================================================================

class HitlCriterion(BaseModel):
    """Um critério individual de roteamento HITL."""
    type: HitlCriteriaType
    enabled: bool = True
    priority: int = 1  # Maior = mais prioritário
    params: Dict[str, Any] = Field(default_factory=dict)

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

    Pode ser armazenada como JSON em ConfiguracaoNegocio ou tabela dedicada.
    """
    enabled: bool = False
    criteria: List[HitlCriterion] = Field(default_factory=list)

    # Queue settings
    queue_ttl_hours: int = 24  # Tempo máximo na fila antes de expirar
    max_pending_per_client: int = 100  # Limite de pendências por cliente

    # Notification settings
    notify_on_pending: bool = False
    notify_email: Optional[str] = None
    notify_webhook_url: Optional[str] = None

    # Dataset settings (Langfuse integration)
    auto_add_to_dataset: bool = True
    dataset_name: Optional[str] = None  # Nome do dataset no Langfuse

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
                    params={"threshold": 0.7}
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
    cliente_vizu_id: UUID = SQLField(index=True)
    cliente_final_id: Optional[int] = SQLField(default=None, index=True)

    # Conteúdo da interação
    user_message: str
    agent_response: str

    # Metadata do roteamento
    criteria_triggered: str  # HitlCriteriaType value
    confidence_score: Optional[float] = None
    criteria_details: Dict[str, Any] = SQLField(default_factory=dict, sa_column=Column(JSON))

    # Metadata adicional (tools chamadas, trace_id, etc.)
    trace_id: Optional[str] = None
    tools_called: List[str] = SQLField(default_factory=list, sa_column=Column(JSON))
    model_used: Optional[str] = None

    # Contexto (para reproduzir a situação)
    conversation_context: List[Dict[str, Any]] = SQLField(default_factory=list, sa_column=Column(JSON))


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
    reviewed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    # Review data (preenchido pelo revisor)
    reviewer_id: Optional[str] = None  # Email ou ID do revisor
    corrected_response: Optional[str] = None
    feedback_type: Optional[str] = None  # HitlFeedbackType value
    feedback_notes: Optional[str] = None
    feedback_tags: List[str] = SQLField(default_factory=list, sa_column=Column(JSON))

    # Langfuse integration
    langfuse_dataset_item_id: Optional[str] = None


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
    reviewed_at: Optional[datetime]
    expires_at: Optional[datetime]
    reviewer_id: Optional[str]
    corrected_response: Optional[str]
    feedback_type: Optional[str]
    feedback_notes: Optional[str]
    feedback_tags: List[str]


class HitlReviewUpdate(BaseModel):
    """Schema para atualizar um HitlReview (ação do revisor)."""
    status: HitlReviewStatus
    corrected_response: Optional[str] = None
    feedback_type: Optional[HitlFeedbackType] = None
    feedback_notes: Optional[str] = None
    feedback_tags: List[str] = Field(default_factory=list)


class HitlQueueStats(BaseModel):
    """Estatísticas da fila HITL."""
    total_pending: int
    total_today: int
    by_criteria: Dict[str, int]
    by_client: Dict[str, int]
    avg_review_time_minutes: Optional[float]
    oldest_pending_hours: Optional[float]


class HitlDecision(BaseModel):
    """
    Resultado da avaliação de critérios HITL.

    Retornado pelo HitlService.evaluate() para indicar se uma
    interação deve ir para revisão.
    """
    should_review: bool
    criteria_triggered: Optional[HitlCriteriaType] = None
    confidence_score: Optional[float] = None
    details: Dict[str, Any] = Field(default_factory=dict)
