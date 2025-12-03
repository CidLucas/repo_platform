# vizu_experiment_service/classifier.py
"""Response classifier - routes results to auto-approve or HITL queue."""

import logging
import random
from typing import Optional

from vizu_models import (
    ExperimentCase,
    ExperimentRun,
    CaseOutcome,
    ClassificationResult,
    ExperimentStatus,
    HitlRoutingConfig,
)
from .config import settings

logger = logging.getLogger(__name__)


class ResponseClassifier:
    """
    Classifies experiment case results for routing.

    Classification rules (from ClassificationResult enum):
    - HIGH_CONFIDENCE: Good response, can be auto-approved
    - MEDIUM_CONFIDENCE: Uncertain, may route to HITL
    - LOW_CONFIDENCE: Poor response, route to HITL
    - TOOL_USED: Tool was called, may need review
    - ELICITATION: Elicitation was triggered
    - ERROR: Error occurred

    Cases classified as LOW_CONFIDENCE, TOOL_USED (for sensitive tools),
    or ELICITATION are sent to HITL queue for human review.
    """

    def __init__(
        self,
        db_session,
        hitl_service=None,
        confidence_threshold: float = None,
        sample_rate: float = None,
    ):
        """
        Initialize the classifier.

        Args:
            db_session: SQLModel async session
            hitl_service: Optional HITL service for queue routing
            confidence_threshold: Min confidence for auto-approve
            sample_rate: % of auto-approved to sample for review
        """
        self.db = db_session
        self.hitl_service = hitl_service
        self.confidence_threshold = confidence_threshold or settings.DEFAULT_CONFIDENCE_THRESHOLD
        self.sample_rate = sample_rate or settings.DEFAULT_SAMPLE_RATE

    async def classify_case(
        self,
        case: ExperimentCase,
        hitl_config: Optional[HitlRoutingConfig] = None,
    ) -> ClassificationResult:
        """
        Classify a single experiment case.

        Args:
            case: The case to classify
            hitl_config: Optional HITL routing config

        Returns:
            ClassificationResult enum value
        """
        # Use provided config or defaults
        confidence_threshold = (
            hitl_config.confidence_threshold if hitl_config else self.confidence_threshold
        )

        confidence = case.confidence_score or 0.5

        # 1. Check for errors
        if case.outcome == CaseOutcome.ERROR:
            classification = ClassificationResult.ERROR

        # 2. Check for low confidence
        elif confidence < confidence_threshold * 0.5:
            classification = ClassificationResult.LOW_CONFIDENCE

        # 3. Check for medium confidence
        elif confidence < confidence_threshold:
            classification = ClassificationResult.MEDIUM_CONFIDENCE

        # 4. Check for tool usage requiring review
        elif (
            hitl_config
            and case.actual_tool_called
            and case.actual_tool_called in hitl_config.always_review_tools
        ):
            classification = ClassificationResult.TOOL_USED

        # 5. High confidence
        else:
            classification = ClassificationResult.HIGH_CONFIDENCE

        # Update case with classification
        case.classification = classification
        self.db.add(case)  # Mark for update, don't commit yet

        logger.debug(f"Case {case.id} classified as {classification.value}")

        return classification

    async def classify_run(
        self,
        run: ExperimentRun,
        route_to_hitl: bool = True,
    ) -> dict:
        """
        Classify all cases in an experiment run.

        Args:
            run: The experiment run to classify
            route_to_hitl: Whether to send to HITL queue

        Returns:
            Dict with classification counts
        """
        from sqlmodel import select

        # Store run_id before any async operations to avoid lazy loading issues
        run_id = run.id

        # Get HITL config from manifest
        manifest_data = run.manifest_json or {}
        hitl_data = manifest_data.get("hitl", {})
        hitl_config = HitlRoutingConfig(**hitl_data) if hitl_data else HitlRoutingConfig()

        # Get all cases for this run
        stmt = select(ExperimentCase).where(ExperimentCase.run_id == run.id)
        query_result = await self.db.exec(stmt)
        cases = query_result.all()

        # Classify each case
        counts = {
            "high_confidence": 0,
            "medium_confidence": 0,
            "low_confidence": 0,
            "tool_used": 0,
            "elicitation": 0,
            "error": 0,
            "total": 0,
        }

        hitl_items = []

        for case in cases:
            classification = await self.classify_case(case, hitl_config)
            counts["total"] += 1

            # Count by classification
            if classification == ClassificationResult.HIGH_CONFIDENCE:
                counts["high_confidence"] += 1
            elif classification == ClassificationResult.MEDIUM_CONFIDENCE:
                counts["medium_confidence"] += 1
                # Random sample from medium confidence
                if random.random() < self.sample_rate:
                    hitl_items.append(case)
            elif classification == ClassificationResult.LOW_CONFIDENCE:
                counts["low_confidence"] += 1
                hitl_items.append(case)
            elif classification == ClassificationResult.TOOL_USED:
                counts["tool_used"] += 1
                hitl_items.append(case)
            elif classification == ClassificationResult.ELICITATION:
                counts["elicitation"] += 1
                hitl_items.append(case)
            elif classification == ClassificationResult.ERROR:
                counts["error"] += 1

        # Route to HITL if configured
        if route_to_hitl and self.hitl_service and hitl_items:
            await self._route_to_hitl(hitl_items, run)
            run.hitl_routed_cases = len(hitl_items)

        await self.db.commit()

        logger.info(
            f"Classified run {run_id}: "
            f"{counts['high_confidence']} high confidence, "
            f"{len(hitl_items)} sent to HITL"
        )

        return counts

    async def _route_to_hitl(
        self,
        cases: list[ExperimentCase],
        run: ExperimentRun,
    ) -> None:
        """
        Send cases to HITL queue for human review.

        Args:
            cases: List of cases needing review
            run: The experiment run
        """
        if not self.hitl_service:
            logger.warning("HITL service not configured, skipping routing")
            return

        for case in cases:
            # Update case outcome to show it's pending review
            case.outcome = CaseOutcome.NEEDS_REVIEW.value
            case.hitl_routed_reason = (
                f"Classification: {case.classification.value if case.classification else 'unknown'}"
            )

            # Create HITL review item
            await self.hitl_service.add_to_queue(
                trace_id=case.langfuse_trace_id,
                metadata={
                    "experiment_run_id": str(run.id),
                    "experiment_case_id": str(case.id),
                    "client_id": str(case.cliente_id),
                    "client_name": case.cliente_name,
                    "input_message": case.input_message,
                    "response_text": case.actual_response,
                    "tools_called": case.tools_called,
                    "expected_tool": case.expected_tool,
                    "classification": case.classification.value if case.classification else None,
                    "confidence_score": case.confidence_score,
                },
                priority=self._get_priority(case),
            )

        await self.db.commit()

    def _get_priority(self, case: ExperimentCase) -> int:
        """
        Determine HITL review priority.

        Returns:
            Priority (1=highest, 3=lowest)
        """
        if case.classification == ClassificationResult.ERROR:
            return 1  # Highest - errors need immediate attention
        elif case.classification == ClassificationResult.LOW_CONFIDENCE:
            return 1  # Highest - low confidence needs review
        elif case.classification == ClassificationResult.TOOL_USED:
            return 2  # Medium - tool usage needs verification
        else:
            return 3  # Lowest - samples for QC


class BatchClassifier:
    """
    Batch processing for classifying multiple experiment runs.
    """

    def __init__(self, db_session, classifier: ResponseClassifier = None):
        self.db = db_session
        self.classifier = classifier or ResponseClassifier(db_session)

    async def classify_pending_runs(self) -> list[dict]:
        """
        Classify all runs in COMPLETED status that haven't been classified.

        Returns:
            List of classification results per run
        """
        from sqlmodel import select

        # Find runs that completed but haven't been fully classified
        stmt = select(ExperimentRun).where(
            ExperimentRun.status == ExperimentStatus.COMPLETED,
            ExperimentRun.hitl_routed_cases == 0,  # Not yet classified
        )
        result = await self.db.exec(stmt)
        runs = result.all()

        results = []
        for run in runs:
            counts = await self.classifier.classify_run(run)
            results.append(
                {
                    "run_id": str(run.id),
                    "manifest_name": run.manifest_name,
                    **counts,
                }
            )

        return results
