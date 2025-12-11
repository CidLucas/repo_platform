# services/atendente_core/src/atendente_core/core/hitl_integration.py
"""
HITL Integration for Atendente Core.

Integra o serviço HITL com o fluxo do agente, avaliando
automaticamente cada interação e enviando para revisão
quando necessário.
"""

import logging
import os
from typing import Optional, List, Dict, Any
from uuid import UUID

from vizu_models import (
    HitlConfig,
    HitlCriterion,
    HitlCriteriaType,
)

logger = logging.getLogger(__name__)


class HitlIntegration:
    """
    Integração HITL para o Atendente Core.

    Gerencia a avaliação de critérios e submissão para revisão.
    Configurável via variáveis de ambiente ou banco de dados.
    """

    def __init__(self):
        self._service = None
        self._queue = None
        self._enabled = os.getenv("HITL_ENABLED", "false").lower() == "true"
        self._default_config = self._load_default_config()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _load_default_config(self) -> HitlConfig:
        """Carrega configuração padrão do ambiente."""
        threshold = float(os.getenv("HITL_CONFIDENCE_THRESHOLD", "0.7"))
        sample_rate = float(os.getenv("HITL_SAMPLE_RATE", "0"))

        criteria = []

        # Low confidence (principal critério por enquanto)
        criteria.append(
            HitlCriterion(
                type=HitlCriteriaType.LOW_CONFIDENCE,
                enabled=True,
                priority=10,
                params={"threshold": threshold},
            )
        )

        # Random sampling (se configurado)
        if sample_rate > 0:
            criteria.append(
                HitlCriterion(
                    type=HitlCriteriaType.RANDOM_SAMPLE,
                    enabled=True,
                    priority=1,
                    params={"rate": sample_rate},
                )
            )

        # Tool errors (sempre ativo)
        criteria.append(
            HitlCriterion(
                type=HitlCriteriaType.TOOL_CALL_FAILED,
                enabled=True,
                priority=9,
                params={},
            )
        )

        return HitlConfig(
            enabled=self._enabled,
            criteria=criteria,
            queue_ttl_hours=int(os.getenv("HITL_TTL_HOURS", "24")),
            auto_add_to_dataset=True,
        )

    def _get_service(self):
        """Lazy load do serviço HITL."""
        if self._service is None and self._enabled:
            try:
                from vizu_hitl_service import HitlService, HitlQueue

                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
                self._queue = HitlQueue.from_url(redis_url)
                self._service = HitlService(self._queue, self._default_config)
                logger.info("HITL Service initialized")
            except ImportError:
                logger.warning("vizu_hitl_service not installed, HITL disabled")
                self._enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize HITL: {e}")
                self._enabled = False

        return self._service

    async def evaluate_and_submit(
        self,
        user_message: str,
        agent_response: str,
        cliente_vizu_id: UUID,
        session_id: str,
        trace_id: Optional[str] = None,
        tools_called: Optional[List[str]] = None,
        tool_errors: Optional[List[str]] = None,
        confidence_score: Optional[float] = None,
        elicitation_pending: bool = False,
        response_time_seconds: Optional[float] = None,
        model_used: Optional[str] = None,
        conversation_context: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Avalia uma interação e submete para HITL se necessário.

        Esta função é não-bloqueante e falhas não afetam o fluxo principal.
        """
        if not self._enabled:
            return

        service = self._get_service()
        if not service:
            return

        try:
            # Avalia critérios
            decision = service.evaluate(
                user_message=user_message,
                agent_response=agent_response,
                cliente_vizu_id=cliente_vizu_id,
                confidence_score=confidence_score,
                tools_called=tools_called,
                tool_errors=tool_errors,
                elicitation_pending=elicitation_pending,
                response_time_seconds=response_time_seconds,
            )

            if decision.should_review:
                # Submete para revisão
                review = service.submit_for_review(
                    decision=decision,
                    user_message=user_message,
                    agent_response=agent_response,
                    cliente_vizu_id=cliente_vizu_id,
                    session_id=session_id,
                    trace_id=trace_id,
                    tools_called=tools_called,
                    model_used=model_used,
                    conversation_context=conversation_context,
                )

                logger.info(
                    f"HITL: Submitted review {review.id} "
                    f"(criteria: {decision.criteria_triggered})"
                )

        except Exception as e:
            # Erros de HITL não devem afetar o fluxo principal
            logger.warning(f"HITL evaluation failed (non-blocking): {e}")

    def get_stats(self, cliente_vizu_id: Optional[UUID] = None):
        """Retorna estatísticas da fila HITL."""
        if not self._enabled or not self._queue:
            return None

        try:
            return self._queue.get_stats(cliente_vizu_id)
        except Exception as e:
            logger.warning(f"Failed to get HITL stats: {e}")
            return None
