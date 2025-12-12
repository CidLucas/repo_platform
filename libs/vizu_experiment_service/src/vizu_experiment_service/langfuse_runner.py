# vizu_experiment_service/langfuse_runner.py
"""
Langfuse-Native Experiment Runner.

This module uses the Langfuse SDK's native `run_experiment()` function
as the experiment execution engine, while keeping our orchestration layer
for manifest loading, HITL routing, and CLI integration.

Architecture:
┌─────────────────────────────────────────────────────────────┐
│           vizu_experiment_service (ORCHESTRATOR)            │
│                                                              │
│  ┌──────────────────┐    ┌──────────────────────────────┐   │
│  │ ManifestLoader   │───▶│ Langfuse Dataset Sync        │   │
│  │ (YAML → Langfuse)│    │ create_dataset_item()        │   │
│  └──────────────────┘    └──────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            langfuse.run_experiment()                  │   │
│  │  - task: calls atendente_core /chat                  │   │
│  │  - evaluators: confidence, tool_usage, semantic      │   │
│  │  - max_concurrency: from manifest                    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────┐    ┌──────────────────────────────┐   │
│  │ ResultProcessor  │───▶│ Route to HITL or Auto-approve│   │
│  └──────────────────┘    └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from vizu_models import (
    CaseOutcome,
    ExperimentCase,
    ExperimentManifest,
    ExperimentRun,
    ExperimentStatus,
)

from .config import settings
from .manifest import ManifestLoader

logger = logging.getLogger(__name__)


class LangfuseExperimentRunner:
    """
    Experiment runner that uses Langfuse SDK's native experiment capabilities.

    This class orchestrates:
    1. Loading manifest and syncing to Langfuse Dataset
    2. Running experiments via langfuse.run_experiment()
    3. Collecting results and routing to HITL
    4. Storing results in local DB for tracking
    """

    def __init__(
        self,
        db_session=None,
        atendente_url: str | None = None,
        langfuse_client=None,
    ):
        """
        Initialize the runner.

        Args:
            db_session: SQLModel async session (optional, for local tracking)
            atendente_url: URL of atendente API
            langfuse_client: Optional pre-configured Langfuse client
        """
        self.db = db_session
        self.atendente_url = atendente_url or settings.ATENDENTE_API_URL
        self._langfuse = langfuse_client

    @property
    def langfuse(self):
        """Lazy initialization of Langfuse client."""
        if self._langfuse is None:
            try:
                from langfuse import Langfuse

                self._langfuse = Langfuse(
                    public_key=settings.LANGFUSE_PUBLIC_KEY,
                    secret_key=settings.LANGFUSE_SECRET_KEY,
                    host=settings.LANGFUSE_HOST,
                )
                logger.info("Langfuse client initialized for experiments")
            except Exception as e:
                logger.error(f"Failed to initialize Langfuse: {e}")
                raise

        return self._langfuse

    async def sync_manifest_to_dataset(
        self,
        manifest: ExperimentManifest,
    ) -> str:
        """
        Sync manifest test cases to a Langfuse Dataset.

        Creates or updates a dataset with all test cases from the manifest.

        Args:
            manifest: The experiment manifest

        Returns:
            Dataset name
        """
        dataset_name = f"experiment/{manifest.name}"

        try:
            # Create or get dataset
            self.langfuse.create_dataset(
                name=dataset_name,
                description=manifest.description or f"Experiment dataset for {manifest.name}",
                metadata={
                    "manifest_version": manifest.version,
                    "created_from": "vizu_experiment_service",
                    "created_at": datetime.utcnow().isoformat(),
                },
            )
            logger.info(f"Created/updated dataset: {dataset_name}")

            # Build all test case items
            for client in manifest.clients:
                # Generic cases
                for case in manifest.cases:
                    if case.cliente_id and case.cliente_id != client.cliente_id:
                        continue

                    item_id = f"{client.cliente_id}:{case.id}"
                    self.langfuse.create_dataset_item(
                        dataset_name=dataset_name,
                        id=item_id,
                        input={
                            "message": case.message,
                            "client_id": client.cliente_id,
                            "client_name": client.name,
                        },
                        expected_output={
                            "expected_tool": case.expected_tool,
                            "expected_contains": case.expected_contains,
                            "expected_not_contains": case.expected_not_contains,
                        },
                        metadata={
                            "case_id": case.id,
                            "description": case.description,
                            "tags": case.tags,
                        },
                    )

                # Client-specific cases
                if manifest.client_specific_cases:
                    for case in manifest.client_specific_cases.get(client.cliente_id, []):
                        item_id = f"{client.cliente_id}:{case.id}"
                        self.langfuse.create_dataset_item(
                            dataset_name=dataset_name,
                            id=item_id,
                            input={
                                "message": case.message,
                                "client_id": client.cliente_id,
                                "client_name": client.name,
                            },
                            expected_output={
                                "expected_tool": case.expected_tool,
                                "expected_contains": case.expected_contains,
                            },
                            metadata={
                                "case_id": case.id,
                                "description": case.description,
                            },
                        )

            self.langfuse.flush()
            logger.info(f"Synced {len(manifest.cases)} cases to dataset {dataset_name}")

            return dataset_name

        except Exception as e:
            logger.error(f"Failed to sync manifest to dataset: {e}")
            raise

    async def run_from_manifest_file(
        self,
        manifest_path: str,
        run_name: str | None = None,
        created_by: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute an experiment from a YAML manifest file.

        Args:
            manifest_path: Path to the manifest YAML
            run_name: Optional name for this run
            created_by: Optional user who initiated the run

        Returns:
            Experiment results dict
        """
        manifest = ManifestLoader.load_from_file(manifest_path)
        return await self.run_from_manifest(manifest, run_name, created_by)

    async def run_from_manifest(
        self,
        manifest: ExperimentManifest,
        run_name: str | None = None,
        created_by: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute an experiment from a manifest using Langfuse SDK.

        Args:
            manifest: The experiment manifest
            run_name: Optional name for this run
            created_by: Optional user who initiated the run

        Returns:
            Dict with experiment results and statistics
        """
        # 1. Sync manifest to Langfuse Dataset
        dataset_name = await self.sync_manifest_to_dataset(manifest)

        # 2. Create local ExperimentRun record (for our tracking)
        local_run = None
        if self.db:
            local_run = ExperimentRun(
                manifest_name=manifest.name,
                manifest_version=manifest.version,
                manifest_json=manifest.model_dump(mode="json"),
                status=ExperimentStatus.RUNNING,
                started_at=datetime.utcnow(),
                created_by=created_by,
            )
            self.db.add(local_run)
            await self.db.commit()
            await self.db.refresh(local_run)

        # 3. Define task function for Langfuse
        api_url = manifest.api_url or self.atendente_url
        timeout = manifest.timeout_seconds

        async def atendente_task(*, item, **kwargs):
            """Task function that calls atendente API."""
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{api_url}/chat",
                    json={
                        "message": item.input["message"],
                        "client_id": item.input["client_id"],
                        "conversation_id": str(uuid.uuid4()),
                    },
                    headers={
                        "X-Experiment-Run-Id": str(local_run.id) if local_run else "unknown",
                    },
                )
                response.raise_for_status()
                data = response.json()

                return {
                    "response": data.get("response", ""),
                    "tools_called": data.get("tools_called", []),
                    "confidence": data.get("confidence"),
                    "model": data.get("model"),
                    "trace_id": data.get("trace_id"),
                }

        # 4. Define evaluators
        def tool_evaluator(*, input, output, expected_output, **kwargs):
            """Check if expected tool was called."""
            from langfuse import Evaluation

            expected_tool = expected_output.get("expected_tool")
            if not expected_tool:
                return None  # No assertion

            tools_called = output.get("tools_called", [])
            passed = expected_tool in tools_called

            return Evaluation(
                name="tool_assertion",
                value=1.0 if passed else 0.0,
                comment=f"Expected {expected_tool}, got {tools_called}",
            )

        def contains_evaluator(*, input, output, expected_output, **kwargs):
            """Check if response contains expected strings."""
            from langfuse import Evaluation

            expected = expected_output.get("expected_contains", [])
            not_expected = expected_output.get("expected_not_contains", [])

            if not expected and not not_expected:
                return None

            response = output.get("response", "").lower()
            passed = True
            reasons = []

            for s in expected or []:
                if s.lower() not in response:
                    passed = False
                    reasons.append(f"Missing: {s}")

            for s in not_expected or []:
                if s.lower() in response:
                    passed = False
                    reasons.append(f"Found forbidden: {s}")

            return Evaluation(
                name="contains_assertion",
                value=1.0 if passed else 0.0,
                comment="; ".join(reasons) if reasons else "OK",
            )

        def confidence_evaluator(*, output, **kwargs):
            """Track confidence score."""
            from langfuse import Evaluation

            confidence = output.get("confidence", 0.5)
            return Evaluation(
                name="confidence",
                value=confidence,
                comment=f"Model confidence: {confidence:.2f}",
            )

        # 5. Define run-level evaluator
        def aggregate_evaluator(*, item_results, **kwargs):
            """Calculate aggregate metrics."""
            from langfuse import Evaluation

            # Count assertions
            tool_passed = sum(
                1
                for r in item_results
                for e in r.evaluations
                if e.name == "tool_assertion" and e.value == 1.0
            )
            tool_total = sum(
                1 for r in item_results for e in r.evaluations if e.name == "tool_assertion"
            )

            contains_passed = sum(
                1
                for r in item_results
                for e in r.evaluations
                if e.name == "contains_assertion" and e.value == 1.0
            )
            contains_total = sum(
                1 for r in item_results for e in r.evaluations if e.name == "contains_assertion"
            )

            # Calculate rates
            tool_rate = tool_passed / tool_total if tool_total > 0 else 1.0
            contains_rate = contains_passed / contains_total if contains_total > 0 else 1.0

            return [
                Evaluation(
                    name="tool_assertion_rate",
                    value=tool_rate,
                    comment=f"{tool_passed}/{tool_total} passed",
                ),
                Evaluation(
                    name="contains_assertion_rate",
                    value=contains_rate,
                    comment=f"{contains_passed}/{contains_total} passed",
                ),
            ]

        # 6. Run experiment via Langfuse SDK
        try:
            run_name = run_name or f"{manifest.name}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

            # Get dataset
            dataset = self.langfuse.get_dataset(dataset_name)

            # Run experiment
            # Note: Langfuse SDK handles concurrency internally
            result = await asyncio.to_thread(
                dataset.run_experiment,
                name=run_name,
                description=f"Experiment from {manifest.name} v{manifest.version}",
                task=atendente_task,
                evaluators=[tool_evaluator, contains_evaluator, confidence_evaluator],
                run_evaluators=[aggregate_evaluator],
                metadata={
                    "manifest_name": manifest.name,
                    "manifest_version": manifest.version,
                    "created_by": created_by,
                    "local_run_id": str(local_run.id) if local_run else None,
                },
            )

            self.langfuse.flush()

            # 7. Process results and update local DB
            if local_run:
                await self._process_results(local_run, result, manifest)

            logger.info(f"Experiment completed: {run_name}")

            return {
                "run_name": run_name,
                "dataset_name": dataset_name,
                "local_run_id": str(local_run.id) if local_run else None,
                "total_items": len(result.results) if hasattr(result, "results") else 0,
                "success": True,
            }

        except Exception as e:
            logger.error(f"Experiment failed: {e}")

            if local_run:
                local_run.status = ExperimentStatus.FAILED
                local_run.notes = str(e)
                local_run.completed_at = datetime.utcnow()
                await self.db.commit()

            raise

    async def _process_results(
        self,
        local_run: ExperimentRun,
        langfuse_result,
        manifest: ExperimentManifest,
    ):
        """
        Process Langfuse experiment results and update local DB.

        Also routes items to HITL queue based on classification.
        """
        try:
            results = langfuse_result.results if hasattr(langfuse_result, "results") else []

            success_count = 0
            failure_count = 0
            hitl_count = 0

            for item_result in results:
                # Get evaluations
                evals = {e.name: e.value for e in item_result.evaluations}

                # Determine outcome
                tool_ok = evals.get("tool_assertion", 1.0) == 1.0
                contains_ok = evals.get("contains_assertion", 1.0) == 1.0
                confidence = evals.get("confidence", 0.5)

                # Classify
                if tool_ok and contains_ok and confidence >= manifest.hitl.confidence_threshold:
                    outcome = CaseOutcome.SUCCESS
                    success_count += 1
                elif confidence < manifest.hitl.confidence_threshold:
                    outcome = CaseOutcome.NEEDS_REVIEW
                    hitl_count += 1
                else:
                    outcome = CaseOutcome.FAILURE
                    failure_count += 1

                # Create local case record
                if self.db:
                    case = ExperimentCase(
                        run_id=local_run.id,
                        case_id=item_result.id if hasattr(item_result, "id") else str(uuid.uuid4()),
                        input_message=item_result.input.get("message", "")
                        if hasattr(item_result, "input")
                        else "",
                        actual_response=item_result.output.get("response", "")
                        if hasattr(item_result, "output")
                        else "",
                        tools_called=item_result.output.get("tools_called", [])
                        if hasattr(item_result, "output")
                        else [],
                        confidence_score=confidence,
                        outcome=outcome,
                        tool_assertion_passed=tool_ok,
                        contains_assertion_passed=contains_ok,
                    )
                    self.db.add(case)

            # Update run stats
            local_run.status = ExperimentStatus.COMPLETED
            local_run.completed_at = datetime.utcnow()
            local_run.total_cases = len(results)
            local_run.completed_cases = len(results)
            local_run.success_cases = success_count
            local_run.failure_cases = failure_count
            local_run.hitl_routed_cases = hitl_count

            await self.db.commit()

        except Exception as e:
            logger.error(f"Error processing results: {e}")

    async def create_training_dataset_from_approved(
        self,
        run_id: str,
        dataset_name: str = "training/approved",
    ) -> int:
        """
        Create a Langfuse training dataset from HITL-approved cases.

        Args:
            run_id: ID of the experiment run
            dataset_name: Name for the training dataset

        Returns:
            Number of items added
        """
        if not self.db:
            raise ValueError("Database session required")

        from sqlmodel import select

        # Get approved cases
        stmt = select(ExperimentCase).where(
            ExperimentCase.run_id == uuid.UUID(run_id),
            ExperimentCase.outcome == CaseOutcome.SUCCESS,
        )
        result = await self.db.exec(stmt)
        cases = result.all()

        # Create/update dataset
        self.langfuse.create_dataset(
            name=dataset_name,
            description="Training data from approved experiment cases",
        )

        count = 0
        for case in cases:
            self.langfuse.create_dataset_item(
                dataset_name=dataset_name,
                input={"message": case.input_message},
                expected_output={"response": case.actual_response},
                metadata={
                    "source_run_id": str(case.run_id),
                    "source_case_id": case.case_id,
                    "approved_at": datetime.utcnow().isoformat(),
                },
            )
            count += 1

        self.langfuse.flush()
        logger.info(f"Added {count} items to training dataset {dataset_name}")

        return count
