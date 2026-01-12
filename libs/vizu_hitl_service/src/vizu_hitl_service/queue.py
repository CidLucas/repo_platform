# libs/vizu_hitl_service/src/vizu_hitl_service/queue.py
"""
Redis-based HITL Queue Manager.

Gerencia a fila de interações pendentes de revisão humana.
"""

import json
import logging
from datetime import datetime, timedelta
from uuid import UUID

import redis

from vizu_models import (
    HitlQueueStats,
    HitlReview,
    HitlReviewCreate,
    HitlReviewRead,
    HitlReviewStatus,
)

logger = logging.getLogger(__name__)


class HitlQueue:
    """
    Gerenciador de fila HITL usando Redis.

    Usa sorted sets para ordenar por prioridade/timestamp e
    hashes para armazenar os dados completos.

    Keys:
    - hitl:pending:{client_id} - Sorted set de IDs pendentes
    - hitl:review:{review_id} - Hash com dados completos
    - hitl:stats - Estatísticas globais
    """

    PENDING_KEY_PREFIX = "hitl:pending:"
    REVIEW_KEY_PREFIX = "hitl:review:"
    STATS_KEY = "hitl:stats"

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    @classmethod
    def from_url(cls, redis_url: str) -> "HitlQueue":
        """Cria instância a partir de URL Redis."""
        client = redis.from_url(redis_url, decode_responses=True)
        return cls(client)

    # ========================================================================
    # QUEUE OPERATIONS
    # ========================================================================

    def enqueue(
        self,
        review: HitlReviewCreate,
        client_id: UUID,
        priority: int = 1,
        ttl_hours: int = 24,
    ) -> HitlReview:
        """
        Adiciona uma interação à fila de revisão.

        Args:
            review: Dados da revisão
            client_id: ID do cliente Vizu
            priority: Prioridade (maior = mais urgente)
            ttl_hours: Tempo de vida na fila

        Returns:
            HitlReview criado com ID
        """
        from uuid import uuid4

        review_id = uuid4()
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=ttl_hours)

        # Cria o registro completo
        full_review = HitlReview(
            id=review_id,
            **review.model_dump(),
            status=HitlReviewStatus.PENDING.value,
            created_at=now,
            expires_at=expires_at,
        )

        # Score = priority * 1000000 + timestamp inverso (maior priority primeiro)
        score = priority * 1_000_000 + (10_000_000_000 - int(now.timestamp()))

        # Armazena no Redis
        pipe = self.redis.pipeline()

        # Hash com dados completos
        review_key = f"{self.REVIEW_KEY_PREFIX}{review_id}"
        review_data = full_review.model_dump(mode="json")
        # Convert UUIDs e datetimes para string
        for key, value in review_data.items():
            if isinstance(value, UUID | datetime):
                review_data[key] = str(value)
            elif isinstance(value, dict | list):
                review_data[key] = json.dumps(value)

        pipe.hset(review_key, mapping=review_data)
        pipe.expire(review_key, ttl_hours * 3600)

        # Sorted set para ordem de prioridade
        pending_key = f"{self.PENDING_KEY_PREFIX}{client_id}"
        pipe.zadd(pending_key, {str(review_id): score})

        # Stats
        pipe.hincrby(self.STATS_KEY, "total_enqueued", 1)
        pipe.hincrby(self.STATS_KEY, f"by_criteria:{review.criteria_triggered}", 1)

        pipe.execute()

        logger.info(f"HITL Review {review_id} enqueued for client {client_id}")
        return full_review

    def dequeue(
        self, client_id: UUID | None = None
    ) -> HitlReviewRead | None:
        """
        Remove e retorna a próxima revisão da fila.

        Args:
            client_id: Se fornecido, busca apenas deste cliente

        Returns:
            Próxima revisão ou None se fila vazia
        """
        if client_id:
            pending_key = f"{self.PENDING_KEY_PREFIX}{client_id}"
            result = self.redis.zpopmax(pending_key, count=1)
        else:
            # Busca de qualquer cliente (scan por pattern)
            for key in self.redis.scan_iter(match=f"{self.PENDING_KEY_PREFIX}*"):
                result = self.redis.zpopmax(key, count=1)
                if result:
                    break
            else:
                return None

        if not result:
            return None

        review_id = result[0][0]
        review_data = self._get_review_data(review_id)

        if review_data:
            # Marca como em processamento
            review_key = f"{self.REVIEW_KEY_PREFIX}{review_id}"
            self.redis.hset(review_key, "status", HitlReviewStatus.PENDING.value)

        return review_data

    def get_pending(
        self,
        client_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[HitlReviewRead]:
        """
        Lista revisões pendentes.

        Args:
            client_id: Filtrar por cliente
            limit: Máximo de resultados
            offset: Pular N resultados

        Returns:
            Lista de revisões pendentes
        """
        reviews = []

        if client_id:
            pending_key = f"{self.PENDING_KEY_PREFIX}{client_id}"
            review_ids = self.redis.zrevrange(pending_key, offset, offset + limit - 1)
        else:
            # Aggregate from all clients
            review_ids = []
            for key in self.redis.scan_iter(match=f"{self.PENDING_KEY_PREFIX}*"):
                ids = self.redis.zrevrange(key, 0, limit - 1)
                review_ids.extend(ids)
            review_ids = review_ids[offset : offset + limit]

        for review_id in review_ids:
            review_data = self._get_review_data(review_id)
            if review_data:
                reviews.append(review_data)

        return reviews

    def get_review(self, review_id: UUID) -> HitlReviewRead | None:
        """Busca uma revisão específica."""
        return self._get_review_data(str(review_id))

    def update_review(
        self,
        review_id: UUID,
        status: HitlReviewStatus,
        reviewer_id: str,
        corrected_response: str | None = None,
        feedback_type: str | None = None,
        feedback_notes: str | None = None,
        feedback_tags: list[str] | None = None,
    ) -> HitlReviewRead | None:
        """
        Atualiza uma revisão com o feedback do revisor.

        Args:
            review_id: ID da revisão
            status: Novo status
            reviewer_id: ID/email do revisor
            corrected_response: Resposta corrigida (se aplicável)
            feedback_type: Tipo de feedback
            feedback_notes: Notas adicionais
            feedback_tags: Tags de categorização

        Returns:
            Revisão atualizada ou None se não encontrada
        """
        review_key = f"{self.REVIEW_KEY_PREFIX}{review_id}"

        if not self.redis.exists(review_key):
            return None

        updates = {
            "status": status.value,
            "reviewer_id": reviewer_id,
            "reviewed_at": datetime.utcnow().isoformat(),
        }

        if corrected_response:
            updates["corrected_response"] = corrected_response
        if feedback_type:
            updates["feedback_type"] = feedback_type
        if feedback_notes:
            updates["feedback_notes"] = feedback_notes
        if feedback_tags:
            updates["feedback_tags"] = json.dumps(feedback_tags)

        self.redis.hset(review_key, mapping=updates)

        # Remove da fila de pendentes
        client_id = self.redis.hget(review_key, "client_id")
        if client_id:
            pending_key = f"{self.PENDING_KEY_PREFIX}{client_id}"
            self.redis.zrem(pending_key, str(review_id))

        # Stats
        self.redis.hincrby(self.STATS_KEY, f"by_status:{status.value}", 1)

        logger.info(
            f"HITL Review {review_id} updated to {status.value} by {reviewer_id}"
        )
        return self._get_review_data(str(review_id))

    def get_stats(self, client_id: UUID | None = None) -> HitlQueueStats:
        """Retorna estatísticas da fila."""
        if client_id:
            pending_key = f"{self.PENDING_KEY_PREFIX}{client_id}"
            total_pending = self.redis.zcard(pending_key)
            by_client = {str(client_id): total_pending}
        else:
            total_pending = 0
            by_client = {}
            for key in self.redis.scan_iter(match=f"{self.PENDING_KEY_PREFIX}*"):
                client_id = key.replace(self.PENDING_KEY_PREFIX, "")
                count = self.redis.zcard(key)
                total_pending += count
                by_client[client_id] = count

        # Estatísticas do hash global
        stats_data = self.redis.hgetall(self.STATS_KEY) or {}

        by_criteria = {}
        for key, value in stats_data.items():
            if key.startswith("by_criteria:"):
                criteria = key.replace("by_criteria:", "")
                by_criteria[criteria] = int(value)

        return HitlQueueStats(
            total_pending=total_pending,
            total_today=int(stats_data.get("total_enqueued", 0)),
            by_criteria=by_criteria,
            by_client=by_client,
            avg_review_time_minutes=None,  # TODO: Calcular
            oldest_pending_hours=None,  # TODO: Calcular
        )

    def expire_old_reviews(self, max_age_hours: int = 24) -> int:
        """
        Marca revisões antigas como expiradas.

        Returns:
            Número de revisões expiradas
        """
        expired_count = 0
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)

        for key in self.redis.scan_iter(match=f"{self.REVIEW_KEY_PREFIX}*"):
            created_at_str = self.redis.hget(key, "created_at")
            if created_at_str:
                created_at = datetime.fromisoformat(created_at_str)
                if created_at < cutoff:
                    status = self.redis.hget(key, "status")
                    if status == HitlReviewStatus.PENDING.value:
                        self.redis.hset(key, "status", HitlReviewStatus.EXPIRED.value)
                        expired_count += 1

        if expired_count:
            logger.info(f"Expired {expired_count} old HITL reviews")

        return expired_count

    # ========================================================================
    # PRIVATE METHODS
    # ========================================================================

    def _get_review_data(self, review_id: str) -> HitlReviewRead | None:
        """Busca dados completos de uma revisão."""
        review_key = f"{self.REVIEW_KEY_PREFIX}{review_id}"
        data = self.redis.hgetall(review_key)

        if not data:
            return None

        # Parse JSON fields
        for field in [
            "criteria_details",
            "tools_called",
            "conversation_context",
            "feedback_tags",
        ]:
            if field in data and isinstance(data[field], str):
                try:
                    data[field] = json.loads(data[field])
                except json.JSONDecodeError:
                    data[field] = [] if field.endswith("s") else {}

        # Parse UUID fields
        for field in ["id", "client_id", "cliente_final_id"]:
            if field in data and data[field]:
                try:
                    data[field] = UUID(data[field])
                except ValueError:
                    pass

        # Parse datetime fields
        for field in ["created_at", "reviewed_at", "expires_at"]:
            if field in data and data[field]:
                try:
                    data[field] = datetime.fromisoformat(data[field])
                except ValueError:
                    data[field] = None

        # Parse float fields
        if "confidence_score" in data and data["confidence_score"]:
            try:
                data["confidence_score"] = float(data["confidence_score"])
            except ValueError:
                data["confidence_score"] = None

        return HitlReviewRead(**data)
