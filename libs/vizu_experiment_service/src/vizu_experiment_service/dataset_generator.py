# vizu_experiment_service/dataset_generator.py
"""Training dataset generator - creates datasets from reviewed experiment cases."""

import logging
from typing import Optional
from uuid import UUID

from vizu_models import (
    CaseOutcome,
    ClassificationResult,
    ExperimentCase,
)

logger = logging.getLogger(__name__)


class TrainingDatasetGenerator:
    """
    Generates training datasets from experiment cases.

    Sources:
    - HIGH_CONFIDENCE cases (auto-approved)
    - REVIEWED cases from HITL (human-corrected)

    Integrates with Langfuse for dataset management.
    """

    def __init__(
        self,
        db_session,
        langfuse_client=None,
    ):
        """
        Initialize the dataset generator.

        Args:
            db_session: SQLModel async session
            langfuse_client: Optional Langfuse client for sync
        """
        self.db = db_session
        self.langfuse = langfuse_client

    async def create_langfuse_dataset(
        self,
        name: str,
        description: str | None = None,
        run_id: UUID | None = None,
    ) -> str:
        """
        Create a new Langfuse dataset.

        Args:
            name: Dataset name
            description: Optional description
            run_id: Optional link to source experiment run

        Returns:
            Langfuse dataset name/ID
        """
        if not self.langfuse:
            raise ValueError("Langfuse client not configured")

        try:
            self.langfuse.create_dataset(
                name=name,
                description=description,
                metadata={"experiment_run_id": str(run_id) if run_id else None},
            )
            logger.info(f"Created Langfuse dataset: {name}")
            return name
        except Exception as e:
            logger.error(f"Failed to create Langfuse dataset: {e}")
            raise

    async def add_cases_from_run(
        self,
        dataset_name: str,
        run_id: UUID,
        include_high_confidence: bool = True,
        include_reviewed: bool = True,
    ) -> int:
        """
        Add cases from an experiment run to a Langfuse dataset.

        Args:
            dataset_name: Target Langfuse dataset name
            run_id: Source experiment run ID
            include_high_confidence: Include HIGH_CONFIDENCE cases
            include_reviewed: Include REVIEWED cases

        Returns:
            Number of items added
        """
        from sqlmodel import select

        # Build query for eligible cases
        conditions = [ExperimentCase.run_id == run_id]

        outcomes = []
        if include_high_confidence:
            outcomes.append(CaseOutcome.SUCCESS)
        if include_reviewed:
            outcomes.append(CaseOutcome.REVIEWED)

        if outcomes:
            conditions.append(ExperimentCase.outcome.in_(outcomes))

        stmt = select(ExperimentCase).where(*conditions)
        result = await self.db.exec(stmt)
        cases = result.all()

        items_added = 0

        for case in cases:
            success = await self._add_case_to_langfuse(dataset_name, case)
            if success:
                items_added += 1

        logger.info(f"Added {items_added} cases from run {run_id} to dataset {dataset_name}")

        return items_added

    async def add_from_hitl_review(
        self,
        dataset_name: str,
        hitl_review: dict,
    ) -> bool:
        """
        Add a single item from HITL review to Langfuse dataset.

        Args:
            dataset_name: Target Langfuse dataset name
            hitl_review: HITL review data with corrections

        Returns:
            True if added successfully
        """
        if not self.langfuse:
            logger.warning("Langfuse client not configured")
            return False

        # Extract data from HITL review
        input_text = hitl_review.get("input_message", "")
        output_text = hitl_review.get("corrected_response") or hitl_review.get("response_text", "")

        if not input_text or not output_text:
            logger.warning("HITL review missing required fields, skipping")
            return False

        try:
            self.langfuse.create_dataset_item(
                dataset_name=dataset_name,
                input={"message": input_text},
                expected_output=output_text,
                metadata={
                    "source": "hitl_review",
                    "trace_id": hitl_review.get("trace_id"),
                    "client_id": hitl_review.get("client_id"),
                    "reviewer_notes": hitl_review.get("notes"),
                    "original_classification": hitl_review.get("classification"),
                },
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add HITL review to Langfuse: {e}")
            return False

    async def _add_case_to_langfuse(
        self,
        dataset_name: str,
        case: ExperimentCase,
    ) -> bool:
        """
        Add an experiment case to Langfuse dataset.
        """
        if not self.langfuse:
            return False

        if not case.actual_response:
            return False

        try:
            self.langfuse.create_dataset_item(
                dataset_name=dataset_name,
                input={"message": case.input_message},
                expected_output=case.actual_response,
                metadata={
                    "source": "experiment",
                    "trace_id": case.langfuse_trace_id,
                    "client_id": str(case.cliente_id),
                    "client_name": case.cliente_name,
                    "tools_called": case.tools_called,
                    "expected_tool": case.expected_tool,
                    "classification": case.classification.value if case.classification else None,
                    "confidence_score": case.confidence_score,
                    "outcome": case.outcome.value if case.outcome else None,
                },
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to add case to Langfuse: {e}")
            return False

    async def export_run_to_jsonl(
        self,
        run_id: UUID,
        include_high_confidence: bool = True,
        include_reviewed: bool = True,
    ) -> str:
        """
        Export experiment run cases to JSONL format.

        Args:
            run_id: Experiment run to export
            include_high_confidence: Include HIGH_CONFIDENCE cases
            include_reviewed: Include REVIEWED cases

        Returns:
            JSONL string
        """
        import json

        from sqlmodel import select

        # Build query
        conditions = [ExperimentCase.run_id == run_id]

        outcomes = []
        if include_high_confidence:
            outcomes.append(CaseOutcome.SUCCESS)
        if include_reviewed:
            outcomes.append(CaseOutcome.REVIEWED)

        if outcomes:
            conditions.append(ExperimentCase.outcome.in_(outcomes))

        stmt = select(ExperimentCase).where(*conditions)
        result = await self.db.exec(stmt)
        cases = result.all()

        lines = []
        for case in cases:
            if not case.actual_response:
                continue

            lines.append(
                json.dumps(
                    {
                        "input": case.input_message,
                        "output": case.actual_response,
                        "metadata": {
                            "client_id": str(case.cliente_id),
                            "client_name": case.cliente_name,
                            "tools_called": case.tools_called,
                            "classification": case.classification.value
                            if case.classification
                            else None,
                        },
                    }
                )
            )

        return "\n".join(lines)

    async def get_run_dataset_stats(self, run_id: UUID) -> dict:
        """
        Get statistics for potential training data from a run.

        Returns:
            Dict with case counts by outcome/classification
        """
        from sqlmodel import func, select

        # Total eligible (SUCCESS or REVIEWED)
        eligible_stmt = select(func.count()).where(
            ExperimentCase.run_id == run_id,
            ExperimentCase.outcome.in_([CaseOutcome.SUCCESS, CaseOutcome.REVIEWED]),
        )
        eligible = (await self.db.exec(eligible_stmt)).first() or 0

        # By classification
        by_classification = {}
        for cls in ClassificationResult:
            stmt = select(func.count()).where(
                ExperimentCase.run_id == run_id,
                ExperimentCase.classification == cls,
            )
            count = (await self.db.exec(stmt)).first() or 0
            by_classification[cls.value] = count

        # By outcome
        by_outcome = {}
        for outcome in CaseOutcome:
            stmt = select(func.count()).where(
                ExperimentCase.run_id == run_id,
                ExperimentCase.outcome == outcome,
            )
            count = (await self.db.exec(stmt)).first() or 0
            by_outcome[outcome.value] = count

        return {
            "eligible_for_training": eligible,
            "by_classification": by_classification,
            "by_outcome": by_outcome,
            "auto_approved": by_classification.get("high_confidence", 0),
            "hitl_reviewed": by_outcome.get("reviewed", 0),
        }
