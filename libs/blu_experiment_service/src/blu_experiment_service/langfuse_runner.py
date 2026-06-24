# blu_experiment_service/langfuse_runner.py
"""
Langfuse-Native Experiment Runner.

This module uses the Langfuse SDK's native `run_experiment()` function
as the experiment execution engine, while keeping our orchestration layer
for manifest loading, HITL routing, and CLI integration.

Architecture:
┌─────────────────────────────────────────────────────────────┐
│           blu_experiment_service (ORCHESTRATOR)            │
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
from typing import Any

import httpx
from blu_models import (
    CaseOutcome,
    ExperimentCase,
    ExperimentManifest,
    ExperimentRun,
    ExperimentStatus,
    ModelOverride,
    PromptVariant,
)

from blu_experiment_service.config import settings
from blu_experiment_service.manifest import ManifestLoader

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
                    "created_from": "blu_experiment_service",
                    "created_at": datetime.utcnow().isoformat(),
                },
            )
            logger.info(f"Created/updated dataset: {dataset_name}")

            # Build all test case items
            for client in manifest.clients:
                # Generic cases
                for case in manifest.cases:
                    if case.client_id and case.client_id != client.client_id:
                        continue

                    item_id = f"{client.client_id}:{case.id}"
                    self.langfuse.create_dataset_item(
                        dataset_name=dataset_name,
                        id=item_id,
                        input={
                            "message": case.message,
                            "client_id": client.client_id,
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
                    for case in manifest.client_specific_cases.get(client.client_id, []):
                        item_id = f"{client.client_id}:{case.id}"
                        self.langfuse.create_dataset_item(
                            dataset_name=dataset_name,
                            id=item_id,
                            input={
                                "message": case.message,
                                "client_id": client.client_id,
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

        If manifest.configs is provided with multiple variants, runs ONE
        experiment per variant for direct comparison. Each variant creates
        a separate Langfuse experiment run under the same dataset.

        Args:
            manifest: The experiment manifest
            run_name: Optional name for this run
            created_by: Optional user who initiated the run

        Returns:
            Dict with experiment results and statistics
        """
        # 1. Sync manifest to Langfuse Dataset (test cases only, not configs)
        dataset_name = await self.sync_manifest_to_dataset(manifest)

        # 2. Determine configs to run
        configs_to_run = manifest.configs or []
        if not configs_to_run:
            # Backwards compatible: single run with no config override
            configs_to_run = [PromptVariant(
                id="default",
                name="Default configuration",
                system_prompt=None,
                skill_config=None,
                model_override=None,
            )]

        # 3. Create local ExperimentRun record (parent)
        parent_run = None
        if self.db:
            parent_run = ExperimentRun(
                manifest_name=manifest.name,
                manifest_version=manifest.version,
                manifest_json=manifest.model_dump(mode="json"),
                status=ExperimentStatus.RUNNING,
                started_at=datetime.utcnow(),
                created_by=created_by,
                notes=f"{len(configs_to_run)} config(s)",
            )
            self.db.add(parent_run)
            await self.db.commit()
            await self.db.refresh(parent_run)

        # 4. Run one experiment per config
        config_results = []
        timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')

        for config in configs_to_run:
            config_result = await self._run_experiment_for_config(
                manifest=manifest,
                config=config,
                dataset_name=dataset_name,
                parent_run_id=str(parent_run.id) if parent_run else None,
                run_suffix=f"{config.id}-{timestamp}",
                created_by=created_by,
                api_url=manifest.api_url or self.atendente_url,
            )
            config_results.append({
                "config_id": config.id,
                "config_name": config.name,
                **config_result,
            })

        # 5. Process aggregate results
        if parent_run:
            parent_run.status = ExperimentStatus.COMPLETED
            parent_run.completed_at = datetime.utcnow()
            parent_run.total_cases = len(manifest.cases) * len(configs_to_run)
            await self.db.commit()

        logger.info(f"Experiment completed: {manifest.name} ({len(config_results)} configs)")

        return {
            "manifest_name": manifest.name,
            "dataset_name": dataset_name,
            "parent_run_id": str(parent_run.id) if parent_run else None,
            "config_count": len(config_results),
            "configs": config_results,
            "success": True,
        }

    async def _run_experiment_for_config(
        self,
        manifest: ExperimentManifest,
        config: PromptVariant,
        dataset_name: str,
        parent_run_id: str | None,
        run_suffix: str,
        created_by: str | None,
        api_url: str,
    ) -> dict[str, Any]:
        """
        Run a single experiment for one prompt/skill variant.

        Args:
            manifest: The experiment manifest
            config: The prompt variant to test
            dataset_name: Langfuse dataset name
            parent_run_id: Local parent run ID for tracking
            run_suffix: Unique suffix for experiment name
            created_by: Who created this run
            api_url: Target API URL

        Returns:
            Dict with experiment run results
        """
        timeout = manifest.timeout_seconds
        run_name = f"{manifest.name}-{config.id}-{run_suffix.split('-', 1)[1] if '-' in run_suffix else run_suffix}"

        # Build metadata with config info
        metadata = {
            "manifest_name": manifest.name,
            "manifest_version": manifest.version,
            "config_id": config.id,
            "config_name": config.name,
            "parent_run_id": parent_run_id,
            "created_by": created_by,
            "has_system_prompt": config.system_prompt is not None,
            "has_skill_config": config.skill_config is not None,
            "has_model_override": config.model_override is not None,
        }
        if config.model_override:
            metadata["model_provider"] = config.model_override.provider
            metadata["model_name"] = config.model_override.model

        async def atendente_task(*, item, **kwargs):
            """Task function that calls atendente API with config overrides."""
            request_body = {
                "message": item.input["message"],
                "client_id": item.input["client_id"],
                "conversation_id": str(uuid.uuid4()),
            }

            # Add config overrides to request
            if config.system_prompt:
                request_body["system_prompt"] = config.system_prompt
            if config.skill_config:
                request_body["skill_config"] = config.skill_config
            if config.model_override:
                request_body["model_provider"] = config.model_override.provider
                request_body["model"] = config.model_override.model
            if config.langfuse_prompt_label:
                request_body["langfuse_prompt_label"] = config.langfuse_prompt_label

            headers = {
                "X-Experiment-Config-Id": config.id,
                "X-Experiment-Parent-Run-Id": parent_run_id or "unknown",
            }

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{api_url}/v1/chat",
                    json=request_body,
                    headers=headers,
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

        # Define evaluators (same as before)
        def tool_evaluator(*, input, output, expected_output, **kwargs):
            from langfuse import Evaluation
            expected_tool = expected_output.get("expected_tool")
            if not expected_tool:
                return None
            tools_called = output.get("tools_called", [])
            passed = expected_tool in tools_called
            return Evaluation(
                name="tool_assertion",
                value=1.0 if passed else 0.0,
                comment=f"Expected {expected_tool}, got {tools_called}",
            )

        def contains_evaluator(*, input, output, expected_output, **kwargs):
            from langfuse import Evaluation
            expected = expected_output.get("expected_contains", [])
            not_expected = expected_output.get("expected_not_contains", [])
            if not expected and not not_expected:
                return None
            resp_text = output.get("response", "").lower()
            passed = True
            reasons = []
            for s in expected or []:
                if s.lower() not in resp_text:
                    passed = False
                    reasons.append(f"Missing: {s}")
            for s in not_expected or []:
                if s.lower() in resp_text:
                    passed = False
                    reasons.append(f"Found forbidden: {s}")
            return Evaluation(
                name="contains_assertion",
                value=1.0 if passed else 0.0,
                comment="; ".join(reasons) if reasons else "OK",
            )

        def confidence_evaluator(*, output, **kwargs):
            from langfuse import Evaluation
            confidence = output.get("confidence", 0.5)
            return Evaluation(
                name="confidence",
                value=confidence,
                comment=f"Model confidence: {confidence:.2f}",
            )

        def aggregate_evaluator(*, item_results, **kwargs):
            from langfuse import Evaluation
            tool_passed = sum(
                1 for r in item_results for e in r.evaluations
                if e.name == "tool_assertion" and e.value == 1.0
            )
            tool_total = sum(
                1 for r in item_results for e in r.evaluations
                if e.name == "tool_assertion"
            )
            contains_passed = sum(
                1 for r in item_results for e in r.evaluations
                if e.name == "contains_assertion" and e.value == 1.0
            )
            contains_total = sum(
                1 for r in item_results for e in r.evaluations
                if e.name == "contains_assertion"
            )
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

        # Run experiment via Langfuse SDK
        try:
            dataset = self.langfuse.get_dataset(dataset_name)

            result = await asyncio.to_thread(
                dataset.run_experiment,
                name=run_name,
                description=f"{manifest.name} v{manifest.version} - config: {config.name}",
                task=atendente_task,
                evaluators=[tool_evaluator, contains_evaluator, confidence_evaluator],
                run_evaluators=[aggregate_evaluator],
                metadata=metadata,
            )

            self.langfuse.flush()

            total = len(result.results) if hasattr(result, "results") else 0
            logger.info(f"Config run completed: {run_name} ({total} items)")

            return {
                "run_name": run_name,
                "config_id": config.id,
                "total_items": total,
                "success": True,
            }

        except Exception as e:
            logger.error(f"Config run failed: {run_name} - {e}")
            return {
                "run_name": run_name,
                "config_id": config.id,
                "error": str(e),
                "success": False,
            }


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
