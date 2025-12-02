# vizu_experiment_service/runner.py
"""Experiment runner - orchestrates test execution against atendente API."""

import asyncio
import uuid
import logging
from datetime import datetime
from typing import Optional

import httpx

from vizu_models import (
    ExperimentRun,
    ExperimentCase,
    ExperimentStatus,
    CaseOutcome,
    ClassificationResult,
    ExperimentManifest,
    TestCaseDefinition,
    ClientVariant,
)
from .config import settings
from .manifest import ManifestLoader

logger = logging.getLogger(__name__)


class ExperimentRunner:
    """
    Executes experiments against the atendente API.

    Flow:
    1. Load manifest (YAML)
    2. Create ExperimentRun in DB with manifest JSON
    3. Fire test cases concurrently against atendente
    4. Collect responses and Langfuse trace IDs
    5. Store ExperimentCase with results and classifications
    """

    def __init__(
        self,
        db_session,
        atendente_url: Optional[str] = None,
        concurrent_limit: int = 5,
    ):
        """
        Initialize the experiment runner.

        Args:
            db_session: SQLModel async session
            atendente_url: URL of atendente API (defaults to settings)
            concurrent_limit: Max concurrent API calls
        """
        self.db = db_session
        self.atendente_url = atendente_url or settings.ATENDENTE_API_URL
        self.concurrent_limit = concurrent_limit
        self.semaphore = asyncio.Semaphore(concurrent_limit)

    async def run_from_manifest_file(
        self,
        manifest_path: str,
        created_by: Optional[str] = None,
    ) -> ExperimentRun:
        """
        Execute an experiment from a YAML manifest file.

        Args:
            manifest_path: Path to the manifest YAML
            created_by: Optional user who initiated the run

        Returns:
            Completed ExperimentRun
        """
        manifest = ManifestLoader.load_from_file(manifest_path)
        return await self.run_from_manifest(manifest, created_by)

    async def run_from_manifest(
        self,
        manifest: ExperimentManifest,
        created_by: Optional[str] = None,
    ) -> ExperimentRun:
        """
        Execute an experiment from a manifest config.

        Args:
            manifest: The experiment manifest
            created_by: Optional user who initiated the run

        Returns:
            Completed ExperimentRun
        """
        # Override API URL from manifest if specified
        api_url = manifest.api_url or self.atendente_url

        # Create ExperimentRun
        run = ExperimentRun(
            manifest_name=manifest.name,
            manifest_version=manifest.version,
            manifest_json=manifest.model_dump(mode="json"),
            status=ExperimentStatus.RUNNING,
            started_at=datetime.utcnow(),
            created_by=created_by,
        )
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)

        logger.info(f"Starting experiment run: {manifest.name} v{manifest.version} (id={run.id})")

        try:
            # Build case list: generic cases + client-specific cases
            all_cases = self._build_case_list(manifest)
            run.total_cases = len(all_cases)

            # Execute test cases concurrently (with semaphore limit)
            results = await asyncio.gather(
                *[
                    self._execute_case(run, client, case, api_url, manifest)
                    for client, case in all_cases
                ],
                return_exceptions=True,
            )

            # Count outcomes
            success = sum(1 for r in results if isinstance(r, ExperimentCase) and r.outcome == CaseOutcome.SUCCESS)
            failure = sum(1 for r in results if isinstance(r, ExperimentCase) and r.outcome == CaseOutcome.FAILURE)
            error = sum(1 for r in results if isinstance(r, Exception) or (isinstance(r, ExperimentCase) and r.outcome == CaseOutcome.ERROR))
            hitl_routed = sum(1 for r in results if isinstance(r, ExperimentCase) and r.outcome == CaseOutcome.NEEDS_REVIEW)

            # Update run stats
            run.status = ExperimentStatus.COMPLETED
            run.completed_at = datetime.utcnow()
            run.completed_cases = len([r for r in results if isinstance(r, ExperimentCase)])
            run.success_cases = success
            run.failure_cases = failure
            run.error_cases = error
            run.hitl_routed_cases = hitl_routed

        except Exception as e:
            logger.error(f"Experiment run failed: {e}")
            run.status = ExperimentStatus.FAILED
            run.notes = f"Error: {str(e)}"
            run.completed_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(run)

        logger.info(
            f"Experiment run completed: {manifest.name} - "
            f"{run.success_cases}/{run.total_cases} success, "
            f"{run.hitl_routed_cases} routed to HITL"
        )

        return run

    def _build_case_list(
        self,
        manifest: ExperimentManifest,
    ) -> list[tuple[ClientVariant, TestCaseDefinition]]:
        """
        Build complete list of (client, case) tuples to execute.

        Returns:
            List of (ClientVariant, TestCaseDefinition) tuples
        """
        all_cases = []

        for client in manifest.clients:
            # Add generic cases for this client
            for case in manifest.cases:
                # Skip if case has specific client that doesn't match
                if case.cliente_id and case.cliente_id != client.cliente_id:
                    continue
                all_cases.append((client, case))

            # Add client-specific cases
            if manifest.client_specific_cases:
                client_cases = manifest.client_specific_cases.get(client.cliente_id, [])
                for case in client_cases:
                    all_cases.append((client, case))

        return all_cases

    async def _execute_case(
        self,
        run: ExperimentRun,
        client: ClientVariant,
        case: TestCaseDefinition,
        api_url: str,
        manifest: ExperimentManifest,
    ) -> ExperimentCase:
        """
        Execute a single test case against atendente API.

        Returns:
            ExperimentCase with response and classification
        """
        async with self.semaphore:
            start_time = datetime.utcnow()
            trace_id = str(uuid.uuid4())

            # Create case record
            experiment_case = ExperimentCase(
                run_id=run.id,
                case_id=case.id,
                cliente_id=uuid.UUID(client.cliente_id),
                cliente_name=client.name,
                input_message=case.message,
                expected_tool=case.expected_tool,
                expected_contains=case.expected_contains,
            )

            try:
                async with httpx.AsyncClient(timeout=manifest.timeout_seconds) as http:
                    response = await http.post(
                        f"{api_url}/chat",
                        json={
                            "message": case.message,
                            "client_id": client.cliente_id,
                            "conversation_id": str(uuid.uuid4()),
                        },
                        headers={
                            "X-Experiment-Run-Id": str(run.id),
                            "X-Trace-Id": trace_id,
                        },
                    )

                    response.raise_for_status()
                    data = response.json()

                    # Extract response data
                    experiment_case.actual_response = data.get("response", "")
                    experiment_case.tools_called = data.get("tools_called", [])
                    experiment_case.actual_tool_called = (
                        experiment_case.tools_called[0]
                        if experiment_case.tools_called
                        else None
                    )
                    experiment_case.model_used = data.get("model")
                    experiment_case.langfuse_trace_id = data.get("trace_id") or trace_id
                    experiment_case.confidence_score = data.get("confidence")
                    experiment_case.raw_response = data
                    experiment_case.request_duration_ms = int(
                        (datetime.utcnow() - start_time).total_seconds() * 1000
                    )

                    # Run assertions
                    experiment_case.tool_assertion_passed = self._check_tool_assertion(
                        case.expected_tool,
                        experiment_case.tools_called,
                    )
                    experiment_case.contains_assertion_passed = self._check_contains_assertion(
                        case.expected_contains,
                        case.expected_not_contains,
                        experiment_case.actual_response,
                    )

                    # Classify outcome
                    experiment_case.outcome, experiment_case.classification = self._classify_case(
                        experiment_case,
                        manifest.hitl,
                        run.completed_cases or 0,  # For first_n logic
                    )

            except Exception as e:
                logger.error(f"Case {case.id} failed: {e}")
                experiment_case.outcome = CaseOutcome.ERROR
                experiment_case.error_message = str(e)
                experiment_case.request_duration_ms = int(
                    (datetime.utcnow() - start_time).total_seconds() * 1000
                )

            self.db.add(experiment_case)
            await self.db.commit()
            await self.db.refresh(experiment_case)

            return experiment_case

    def _check_tool_assertion(
        self,
        expected_tool: Optional[str],
        actual_tools: list[str],
    ) -> Optional[bool]:
        """Check if expected tool was called."""
        if not expected_tool:
            return None  # No assertion

        return expected_tool in (actual_tools or [])

    def _check_contains_assertion(
        self,
        expected_contains: Optional[list[str]],
        expected_not_contains: Optional[list[str]],
        response: str,
    ) -> Optional[bool]:
        """Check if response contains/doesn't contain expected strings."""
        if not expected_contains and not expected_not_contains:
            return None  # No assertion

        response_lower = response.lower()

        # Check expected contains
        if expected_contains:
            for s in expected_contains:
                if s.lower() not in response_lower:
                    return False

        # Check expected NOT contains
        if expected_not_contains:
            for s in expected_not_contains:
                if s.lower() in response_lower:
                    return False

        return True

    def _classify_case(
        self,
        case: ExperimentCase,
        hitl_config,
        case_index: int,
    ) -> tuple[CaseOutcome, ClassificationResult]:
        """
        Classify case outcome and determine if HITL review needed.

        Returns:
            (CaseOutcome, ClassificationResult) tuple
        """
        # Check for assertion failures
        if case.tool_assertion_passed is False or case.contains_assertion_passed is False:
            return CaseOutcome.FAILURE, ClassificationResult.LOW_CONFIDENCE

        # All assertions passed (or no assertions)
        assertions_passed = (
            case.tool_assertion_passed in (True, None) and
            case.contains_assertion_passed in (True, None)
        )

        # Determine classification
        confidence = case.confidence_score or 0.5

        if confidence >= hitl_config.confidence_threshold:
            classification = ClassificationResult.HIGH_CONFIDENCE
        elif confidence >= hitl_config.confidence_threshold * 0.7:
            classification = ClassificationResult.MEDIUM_CONFIDENCE
        else:
            classification = ClassificationResult.LOW_CONFIDENCE

        # Check HITL routing rules
        should_route_hitl = False

        # Rule 1: Low confidence
        if classification == ClassificationResult.LOW_CONFIDENCE:
            should_route_hitl = True

        # Rule 2: Always review certain tools
        if case.actual_tool_called and case.actual_tool_called in hitl_config.always_review_tools:
            should_route_hitl = True
            classification = ClassificationResult.TOOL_USED

        # Rule 3: First N cases per client
        if case_index < hitl_config.always_review_first_n:
            should_route_hitl = True

        # Rule 4: Random sample
        import random
        if random.random() < hitl_config.sample_rate:
            should_route_hitl = True

        if should_route_hitl:
            return CaseOutcome.NEEDS_REVIEW, classification

        return (CaseOutcome.SUCCESS if assertions_passed else CaseOutcome.FAILURE), classification
