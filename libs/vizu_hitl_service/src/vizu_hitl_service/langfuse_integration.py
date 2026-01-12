# libs/vizu_hitl_service/src/vizu_hitl_service/langfuse_integration.py
"""
Langfuse Dataset Integration for HITL.

Langfuse-First Architecture:
- When a review is approved/corrected, add to Langfuse dataset
- Add scores to original traces for quality tracking
- Sync approved items for fine-tuning and evaluation

This is the bridge between local HITL and Langfuse platform.
"""

import logging
import os
from datetime import datetime
from typing import Any

from vizu_models import HitlReviewRead, HitlReviewStatus

logger = logging.getLogger(__name__)


class LangfuseDatasetManager:
    """
    Gerencia a integração de revisões HITL com datasets do Langfuse.

    Responsabilidades:
    1. Criar/gerenciar datasets no Langfuse
    2. Adicionar revisões aprovadas como dataset items
    3. Adicionar scores aos traces originais
    4. Criar training datasets para fine-tuning
    """

    def __init__(
        self,
        public_key: str | None = None,
        secret_key: str | None = None,
        host: str | None = None,
    ):
        self._client = None
        self._public_key = public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
        self._secret_key = secret_key or os.getenv("LANGFUSE_SECRET_KEY")
        self._host = host or os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        self._enabled = bool(self._public_key and self._secret_key)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _get_client(self):
        """Lazy load do cliente Langfuse."""
        if self._client is None and self._enabled:
            try:
                from langfuse import Langfuse

                self._client = Langfuse(
                    public_key=self._public_key,
                    secret_key=self._secret_key,
                    host=self._host,
                )
                logger.info(f"Langfuse client initialized: {self._host}")
            except ImportError:
                logger.warning("langfuse not installed, dataset integration disabled")
                self._enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize Langfuse: {e}")
                self._enabled = False

        return self._client

    # =========================================================================
    # DATASET MANAGEMENT
    # =========================================================================

    def get_or_create_dataset(
        self,
        name: str,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Busca ou cria um dataset no Langfuse."""
        client = self._get_client()
        if not client:
            return None

        try:
            return client.create_dataset(
                name=name,
                description=description or f"HITL Dataset: {name}",
                metadata=metadata or {},
            )
        except Exception:
            # If already exists, just get it
            try:
                return client.get_dataset(name)
            except Exception as e2:
                logger.error(f"Failed to get/create dataset {name}: {e2}")
                return None

    def add_review_to_dataset(
        self,
        review: HitlReviewRead,
        dataset_name: str | None = None,
        also_score_trace: bool = True,
    ) -> str | None:
        """
        Adiciona uma revisão aprovada/corrigida ao dataset.

        Args:
            review: Revisão HITL completa
            dataset_name: Nome do dataset (default: 'hitl-training')
            also_score_trace: Se deve adicionar score ao trace original

        Returns:
            ID do item criado ou None se falhar
        """
        if not self._enabled:
            return None

        # Só adiciona revisões aprovadas ou corrigidas
        valid_statuses = [
            HitlReviewStatus.APPROVED.value,
            HitlReviewStatus.CORRECTED.value,
            "approved",
            "corrected",
        ]
        if review.status not in valid_statuses:
            logger.debug(f"Skipping review {review.id} - status {review.status}")
            return None

        client = self._get_client()
        if not client:
            return None

        try:
            # Determina o nome do dataset
            if not dataset_name:
                dataset_name = "hitl-training"

            # Cria/busca dataset
            self.get_or_create_dataset(
                name=dataset_name,
                description="Training data from HITL-approved interactions",
                metadata={"source": "vizu_hitl_service", "type": "training"},
            )

            # Prepara os dados do item
            input_data = {
                "message": review.user_message,
                "client_id": str(review.client_id),
                "session_id": review.session_id,
            }

            # Usa resposta corrigida se disponível, senão a original
            expected_output = {
                "response": review.corrected_response or review.agent_response,
                "tools_called": review.tools_called or [],
            }

            metadata = {
                "hitl_review_id": str(review.id),
                "criteria_triggered": review.criteria_triggered,
                "original_response": review.agent_response,
                "was_corrected": review.corrected_response is not None,
                "feedback_type": review.feedback_type,
                "feedback_tags": review.feedback_tags or [],
                "reviewer_id": review.reviewer_id,
                "model_used": review.model_used,
                "reviewed_at": datetime.utcnow().isoformat(),
            }

            if review.confidence_score is not None:
                metadata["original_confidence"] = review.confidence_score

            # Cria o item no dataset
            client.create_dataset_item(
                dataset_name=dataset_name,
                input=input_data,
                expected_output=expected_output,
                metadata=metadata,
                source_trace_id=review.trace_id,  # Link to original trace
            )

            logger.info(f"Added review {review.id} to dataset {dataset_name}")

            # Also add score to original trace
            if also_score_trace and review.trace_id:
                self.score_trace(
                    trace_id=review.trace_id,
                    review=review,
                )

            client.flush()
            return str(review.id)

        except Exception as e:
            logger.error(f"Failed to add review to dataset: {e}")
            return None

    # =========================================================================
    # TRACE SCORING
    # =========================================================================

    def score_trace(
        self,
        trace_id: str,
        review: HitlReviewRead,
    ) -> bool:
        """
        Add scores to the original trace based on HITL review.

        This creates a feedback loop in Langfuse showing:
        - Human approval/rejection
        - Corrections made
        - Quality signals

        Args:
            trace_id: Langfuse trace ID
            review: The HITL review with feedback

        Returns:
            True if successful
        """
        client = self._get_client()
        if not client:
            return False

        try:
            # Score: hitl_approved (0 = rejected, 1 = approved)
            approved = review.status in [
                HitlReviewStatus.APPROVED.value,
                "approved",
            ]
            corrected = review.status in [
                HitlReviewStatus.CORRECTED.value,
                "corrected",
            ]

            client.score(
                trace_id=trace_id,
                name="hitl_approved",
                value=1.0 if approved or corrected else 0.0,
                comment=f"HITL: {review.status} by {review.reviewer_id or 'unknown'}",
            )

            # Score: hitl_corrected (was correction needed?)
            client.score(
                trace_id=trace_id,
                name="hitl_corrected",
                value=1.0 if corrected else 0.0,
                comment="Response was corrected by human"
                if corrected
                else "Original response approved",
            )

            # Score: hitl_feedback_type
            if review.feedback_type:
                feedback_scores = {
                    "good": 1.0,
                    "acceptable": 0.7,
                    "needs_improvement": 0.3,
                    "bad": 0.0,
                }
                score_value = feedback_scores.get(review.feedback_type, 0.5)
                client.score(
                    trace_id=trace_id,
                    name="hitl_quality",
                    value=score_value,
                    comment=f"Feedback: {review.feedback_type}",
                )

            # Add tags as categorical scores
            if review.feedback_tags:
                for tag in review.feedback_tags:
                    client.score(
                        trace_id=trace_id,
                        name=f"hitl_tag_{tag}",
                        value=1.0,
                        comment=f"Tagged: {tag}",
                    )

            client.flush()
            logger.info(f"Added scores to trace {trace_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to score trace {trace_id}: {e}")
            return False

    # =========================================================================
    # BATCH OPERATIONS
    # =========================================================================

    def batch_add_reviews(
        self,
        reviews: list[HitlReviewRead],
        dataset_name: str,
    ) -> dict[str, int]:
        """
        Adiciona múltiplas revisões ao dataset.

        Returns:
            Dict com contagem de sucesso/falha
        """
        results = {"success": 0, "failed": 0, "skipped": 0}

        for review in reviews:
            valid_statuses = [
                HitlReviewStatus.APPROVED.value,
                HitlReviewStatus.CORRECTED.value,
                "approved",
                "corrected",
            ]
            if review.status not in valid_statuses:
                results["skipped"] += 1
                continue

            item_id = self.add_review_to_dataset(review, dataset_name)
            if item_id:
                results["success"] += 1
            else:
                results["failed"] += 1

        logger.info(f"Batch add to {dataset_name}: {results}")
        return results

    def sync_pending_to_langfuse(
        self,
        reviews: list[HitlReviewRead],
        dataset_name: str = "hitl-training",
    ) -> dict[str, Any]:
        """
        Sync all approved/corrected reviews to Langfuse.

        This should be called periodically to ensure all HITL
        results are reflected in Langfuse datasets and scores.

        Args:
            reviews: List of reviews to sync
            dataset_name: Target dataset name

        Returns:
            Sync statistics
        """
        stats = {
            "total": len(reviews),
            "synced": 0,
            "scored": 0,
            "skipped": 0,
            "errors": [],
        }

        for review in reviews:
            try:
                # Add to dataset
                result = self.add_review_to_dataset(
                    review=review,
                    dataset_name=dataset_name,
                    also_score_trace=True,
                )

                if result:
                    stats["synced"] += 1
                    stats["scored"] += 1
                else:
                    stats["skipped"] += 1

            except Exception as e:
                stats["errors"].append(
                    {
                        "review_id": str(review.id),
                        "error": str(e),
                    }
                )

        # Final flush
        client = self._get_client()
        if client:
            client.flush()

        logger.info(f"Sync complete: {stats['synced']}/{stats['total']} synced")
        return stats

    # =========================================================================
    # EXPERIMENT HELPERS
    # =========================================================================

    def create_evaluation_dataset(
        self,
        source_dataset: str = "hitl-training",
        target_dataset: str = "hitl-evaluation",
        sample_size: int | None = None,
    ) -> dict[str, Any]:
        """
        Create an evaluation dataset from training data.

        Takes a random sample of HITL-approved items to create
        a held-out evaluation set.

        Args:
            source_dataset: Source dataset name
            target_dataset: Target evaluation dataset name
            sample_size: Number of items to sample (default: 10%)

        Returns:
            Creation statistics
        """
        client = self._get_client()
        if not client:
            return {"error": "Langfuse not configured"}

        try:
            # Get source dataset
            source = client.get_dataset(source_dataset)
            if not source:
                return {"error": f"Source dataset {source_dataset} not found"}

            # Get items
            items = list(source.items)
            if not items:
                return {"error": "No items in source dataset"}

            # Sample
            import random

            if sample_size is None:
                sample_size = max(1, len(items) // 10)

            sample_size = min(sample_size, len(items))
            sampled = random.sample(items, sample_size)

            # Create target dataset
            self.get_or_create_dataset(
                name=target_dataset,
                description=f"Evaluation set sampled from {source_dataset}",
                metadata={
                    "source": source_dataset,
                    "sample_size": sample_size,
                    "created_at": datetime.utcnow().isoformat(),
                },
            )

            # Copy items
            for item in sampled:
                client.create_dataset_item(
                    dataset_name=target_dataset,
                    input=item.input,
                    expected_output=item.expected_output,
                    metadata={
                        **item.metadata,
                        "source_item_id": item.id,
                    },
                )

            client.flush()

            return {
                "source": source_dataset,
                "target": target_dataset,
                "items_copied": len(sampled),
                "total_in_source": len(items),
            }

        except Exception as e:
            logger.error(f"Failed to create evaluation dataset: {e}")
            return {"error": str(e)}
