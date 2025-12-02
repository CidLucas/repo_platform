# libs/vizu_hitl_service/src/vizu_hitl_service/service.py
"""
HITL Service - Avalia critérios e decide roteamento para revisão humana.
"""

import logging
import random
import re
from typing import Optional, List, Dict, Any
from uuid import UUID

from vizu_models import (
    HitlConfig,
    HitlCriterion,
    HitlCriteriaType,
    HitlDecision,
    HitlReviewCreate,
    HitlReview,
)
from .queue import HitlQueue

logger = logging.getLogger(__name__)


class HitlService:
    """
    Serviço de Human-in-the-Loop.

    Responsável por:
    1. Avaliar se uma interação deve ir para revisão humana
    2. Aplicar os critérios configurados
    3. Enfileirar interações para revisão
    """

    def __init__(self, queue: HitlQueue, config: Optional[HitlConfig] = None):
        """
        Args:
            queue: Instância do HitlQueue para gerenciar fila
            config: Configuração global (pode ser overriden por cliente)
        """
        self.queue = queue
        self.default_config = config or HitlConfig.default_config()

        # Cache de configs por cliente
        self._client_configs: Dict[UUID, HitlConfig] = {}

    def get_config(self, cliente_vizu_id: Optional[UUID] = None) -> HitlConfig:
        """Retorna configuração para um cliente (ou default)."""
        if cliente_vizu_id and cliente_vizu_id in self._client_configs:
            return self._client_configs[cliente_vizu_id]
        return self.default_config

    def set_client_config(self, cliente_vizu_id: UUID, config: HitlConfig):
        """Define configuração específica para um cliente."""
        self._client_configs[cliente_vizu_id] = config
        logger.info(f"HITL config set for client {cliente_vizu_id}")

    # ========================================================================
    # EVALUATION
    # ========================================================================

    def evaluate(
        self,
        user_message: str,
        agent_response: str,
        cliente_vizu_id: UUID,
        confidence_score: Optional[float] = None,
        tools_called: Optional[List[str]] = None,
        tool_errors: Optional[List[str]] = None,
        elicitation_pending: bool = False,
        message_count: int = 0,
        response_time_seconds: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HitlDecision:
        """
        Avalia se uma interação deve ir para revisão humana.

        Args:
            user_message: Mensagem do usuário
            agent_response: Resposta do agente
            cliente_vizu_id: ID do cliente Vizu
            confidence_score: Score de confiança da LLM (0-1)
            tools_called: Lista de ferramentas chamadas
            tool_errors: Lista de erros de ferramentas
            elicitation_pending: Se há elicitation pendente
            message_count: Número de mensagens na sessão
            response_time_seconds: Tempo de resposta
            metadata: Dados adicionais

        Returns:
            HitlDecision indicando se deve revisar e por qual critério
        """
        config = self.get_config(cliente_vizu_id)

        if not config.enabled:
            return HitlDecision(should_review=False)

        # Ordena critérios por prioridade (maior primeiro)
        sorted_criteria = sorted(
            [c for c in config.criteria if c.enabled],
            key=lambda x: x.priority,
            reverse=True
        )

        for criterion in sorted_criteria:
            triggered, details = self._evaluate_criterion(
                criterion=criterion,
                user_message=user_message,
                agent_response=agent_response,
                confidence_score=confidence_score,
                tools_called=tools_called or [],
                tool_errors=tool_errors or [],
                elicitation_pending=elicitation_pending,
                message_count=message_count,
                response_time_seconds=response_time_seconds,
                metadata=metadata or {},
            )

            if triggered:
                logger.info(
                    f"HITL criterion {criterion.type} triggered for client {cliente_vizu_id}"
                )
                return HitlDecision(
                    should_review=True,
                    criteria_triggered=criterion.type,
                    confidence_score=confidence_score,
                    details=details,
                )

        return HitlDecision(should_review=False, confidence_score=confidence_score)

    def _evaluate_criterion(
        self,
        criterion: HitlCriterion,
        user_message: str,
        agent_response: str,
        confidence_score: Optional[float],
        tools_called: List[str],
        tool_errors: List[str],
        elicitation_pending: bool,
        message_count: int,
        response_time_seconds: Optional[float],
        metadata: Dict[str, Any],
    ) -> tuple[bool, Dict[str, Any]]:
        """Avalia um critério específico."""

        ctype = criterion.type
        params = criterion.params

        if ctype == HitlCriteriaType.LOW_CONFIDENCE:
            threshold = params.get("threshold", 0.7)
            if confidence_score is not None and confidence_score < threshold:
                return True, {"threshold": threshold, "actual": confidence_score}

        elif ctype == HitlCriteriaType.ELICITATION_PENDING:
            if elicitation_pending:
                return True, {"reason": "elicitation_in_progress"}

        elif ctype == HitlCriteriaType.TOOL_CALL_FAILED:
            if tool_errors:
                return True, {"errors": tool_errors}

        elif ctype == HitlCriteriaType.KEYWORD_TRIGGER:
            keywords = params.get("keywords", [])
            text = f"{user_message} {agent_response}".lower()
            for keyword in keywords:
                if keyword.lower() in text:
                    return True, {"keyword": keyword}

        elif ctype == HitlCriteriaType.FIRST_N_MESSAGES:
            n = params.get("n", 3)
            if message_count <= n:
                return True, {"n": n, "current": message_count}

        elif ctype == HitlCriteriaType.RANDOM_SAMPLE:
            rate = params.get("rate", 0.05)
            if random.random() < rate:
                return True, {"rate": rate}

        elif ctype == HitlCriteriaType.MANUAL_FLAG:
            if metadata.get("manual_hitl_flag"):
                return True, {"flagged_by": metadata.get("flagged_by")}

        elif ctype == HitlCriteriaType.SENTIMENT_NEGATIVE:
            # Simples: detecta palavras negativas
            # Em produção, usar um modelo de sentiment
            negative_patterns = params.get("patterns", [
                r"frustrad[oa]",
                r"irritad[oa]",
                r"não funciona",
                r"péssim[oa]",
                r"horrível",
                r"vergonha",
            ])
            text = user_message.lower()
            for pattern in negative_patterns:
                if re.search(pattern, text):
                    return True, {"pattern": pattern}

        elif ctype == HitlCriteriaType.LONG_RESPONSE_TIME:
            threshold_seconds = params.get("threshold_seconds", 30)
            if response_time_seconds and response_time_seconds > threshold_seconds:
                return True, {
                    "threshold": threshold_seconds,
                    "actual": response_time_seconds
                }

        return False, {}

    # ========================================================================
    # QUEUE OPERATIONS
    # ========================================================================

    def submit_for_review(
        self,
        decision: HitlDecision,
        user_message: str,
        agent_response: str,
        cliente_vizu_id: UUID,
        session_id: str,
        cliente_final_id: Optional[UUID] = None,
        trace_id: Optional[str] = None,
        tools_called: Optional[List[str]] = None,
        model_used: Optional[str] = None,
        conversation_context: Optional[List[Dict[str, Any]]] = None,
    ) -> HitlReview:
        """
        Submete uma interação para revisão humana.

        Args:
            decision: Decisão do evaluate()
            ... demais dados da interação

        Returns:
            HitlReview criado
        """
        config = self.get_config(cliente_vizu_id)

        review = HitlReviewCreate(
            session_id=session_id,
            cliente_vizu_id=cliente_vizu_id,
            cliente_final_id=cliente_final_id,
            user_message=user_message,
            agent_response=agent_response,
            criteria_triggered=decision.criteria_triggered.value if decision.criteria_triggered else "manual",
            confidence_score=decision.confidence_score,
            criteria_details=decision.details,
            trace_id=trace_id,
            tools_called=tools_called or [],
            model_used=model_used,
            conversation_context=conversation_context or [],
        )

        # Determina prioridade baseado no critério
        priority = self._get_priority_for_criteria(decision.criteria_triggered)

        return self.queue.enqueue(
            review=review,
            cliente_vizu_id=cliente_vizu_id,
            priority=priority,
            ttl_hours=config.queue_ttl_hours,
        )

    def _get_priority_for_criteria(self, criteria: Optional[HitlCriteriaType]) -> int:
        """Retorna prioridade baseado no critério."""
        if criteria is None:
            return 1

        priority_map = {
            HitlCriteriaType.TOOL_CALL_FAILED: 10,
            HitlCriteriaType.SENTIMENT_NEGATIVE: 9,
            HitlCriteriaType.MANUAL_FLAG: 8,
            HitlCriteriaType.LOW_CONFIDENCE: 7,
            HitlCriteriaType.ELICITATION_PENDING: 6,
            HitlCriteriaType.KEYWORD_TRIGGER: 5,
            HitlCriteriaType.LONG_RESPONSE_TIME: 4,
            HitlCriteriaType.FIRST_N_MESSAGES: 3,
            HitlCriteriaType.RANDOM_SAMPLE: 1,
        }

        return priority_map.get(criteria, 1)
