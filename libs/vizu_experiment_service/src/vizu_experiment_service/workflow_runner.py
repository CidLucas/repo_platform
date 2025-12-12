# vizu_experiment_service/workflow_runner.py
"""Workflow runner - orchestrates test execution against LangGraph workflows."""

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from langchain_core.messages import HumanMessage
from vizu_models import (
    CaseOutcome,
    ClassificationResult,
    ExperimentCase,
    ExperimentRun,
    ExperimentStatus,
)

logger = logging.getLogger(__name__)


class WorkflowManifest:
    """
    Manifest for workflow experiments.

    Defines a LangGraph workflow to test with conversation data.
    """

    def __init__(
        self,
        name: str,
        workflow_path: str,
        data_file: str,
        message_column: str = "message",
        conversation_group_column: str = "test_id",
        sender_column: str = "nome_fantasia",
        version: str = "1.0.0",
        workflow_function: str = "get_workflow",
        evaluator_path: str | None = None,
        evaluator_function: str = "summarize_for_manual_review",
        conversation_csv: str = None,  # Legacy alias for data_file
        trigger_keywords: list[str] = None,
        description: str = "",
        timeout_seconds: int = 120,
        ollama_base_url: str = "http://localhost:11434",
        ollama_model: str = "llama3.2",
        tags: list[str] = None,
    ):
        self.name = name
        self.version = version
        self.workflow_path = workflow_path
        self.workflow_function = workflow_function
        self.evaluator_path = evaluator_path
        self.evaluator_function = evaluator_function
        # Support both data_file and legacy conversation_csv
        self.conversation_csv = conversation_csv or data_file
        self.data_file = data_file or conversation_csv
        self.message_column = message_column
        self.conversation_group_column = conversation_group_column
        self.sender_column = sender_column
        self.trigger_keywords = trigger_keywords or ["fecha", "fechado", "trava", "fechamos", "travo", "fecho"]
        self.description = description
        self.timeout_seconds = timeout_seconds
        self.ollama_base_url = ollama_base_url
        self.ollama_model = ollama_model
        self.tags = tags or []

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "WorkflowManifest":
        """Load manifest from YAML file."""
        import yaml
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "name": self.name,
            "version": self.version,
            "workflow_path": self.workflow_path,
            "workflow_function": self.workflow_function,
            "evaluator_path": self.evaluator_path,
            "evaluator_function": self.evaluator_function,
            "data_file": self.data_file,
            "message_column": self.message_column,
            "conversation_group_column": self.conversation_group_column,
            "sender_column": self.sender_column,
            "trigger_keywords": self.trigger_keywords,
            "description": self.description,
            "timeout_seconds": self.timeout_seconds,
            "ollama_base_url": self.ollama_base_url,
            "ollama_model": self.ollama_model,
            "tags": self.tags,
        }


class WorkflowExperimentRunner:
    """
    Executes experiments against LangGraph workflows.

    Flow:
    1. Load manifest (YAML)
    2. Load the LangGraph workflow from Python file
    3. Load conversation data from CSV
    4. Find trigger messages and execute workflow
    5. Evaluate results using optional evaluator function
    6. Store ExperimentCase with results
    """

    def __init__(
        self,
        db_session,
        concurrent_limit: int = 3,
    ):
        """
        Initialize the workflow experiment runner.

        Args:
            db_session: SQLModel async session
            concurrent_limit: Max concurrent workflow executions
        """
        self.db = db_session
        self.concurrent_limit = concurrent_limit
        self.semaphore = asyncio.Semaphore(concurrent_limit)

    def _load_module_from_path(self, module_path: str) -> Any:
        """
        Dynamically load a Python module.

        Supports both:
        - File paths: /path/to/module.py
        - Module imports: package.subpackage.module
        """
        import importlib

        # Check if it's a file path (contains / or ends with .py)
        if "/" in module_path or module_path.endswith(".py"):
            path = Path(module_path)
            if not path.exists():
                raise FileNotFoundError(f"Module file not found: {module_path}")

            spec = importlib.util.spec_from_file_location(path.stem, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        else:
            # It's a dotted module path (e.g., ferramentas.evaluation_suite.workflows.boleta_trader.workflow)
            try:
                return importlib.import_module(module_path)
            except ImportError as e:
                # Try adding current directory to sys.path and retry
                import os
                import sys

                # Add common project roots to path
                for root_candidate in [os.getcwd(), ".", ".."]:
                    abs_path = os.path.abspath(root_candidate)
                    if abs_path not in sys.path:
                        sys.path.insert(0, abs_path)

                try:
                    return importlib.import_module(module_path)
                except ImportError:
                    raise ImportError(f"Could not import module '{module_path}': {e}")

    def _load_workflow(self, manifest: WorkflowManifest) -> Any:
        """Load the LangGraph workflow from the manifest."""
        module = self._load_module_from_path(manifest.workflow_path)
        workflow_fn = getattr(module, manifest.workflow_function)
        return workflow_fn()

    def _load_evaluator(self, manifest: WorkflowManifest) -> Callable | None:
        """Load the evaluator function from the manifest."""
        if not manifest.evaluator_path:
            return None

        module = self._load_module_from_path(manifest.evaluator_path)
        return getattr(module, manifest.evaluator_function)

    def _load_conversations(self, csv_path: str) -> list[dict[str, Any]]:
        """Load conversation data from CSV."""
        import pandas as pd
        df = pd.read_csv(csv_path)
        return df.to_dict("records")

    def _find_trigger_sequences(
        self,
        messages: list[dict[str, Any]],
        trigger_keywords: list[str],
        manifest: WorkflowManifest,
        context_window: int = 15,
    ) -> list[dict[str, Any]]:
        """
        Find messages that contain trigger keywords and extract context.

        Returns list of test cases with trigger message and context.
        """
        import difflib

        msg_col = manifest.message_column
        sender_col = manifest.sender_column
        group_col = manifest.conversation_group_column

        test_cases = []

        for i, msg in enumerate(messages):
            content = msg.get(msg_col, "").lower().strip()

            # Check if any word in the message matches a trigger keyword
            is_trigger = any(
                difflib.get_close_matches(w, trigger_keywords, n=1, cutoff=0.8)
                for w in content.split()
            )

            if is_trigger:
                # Get context window (previous messages)
                start_idx = max(0, i - context_window)
                context_messages = messages[start_idx:i + 1]

                test_cases.append({
                    "test_id": f"trigger_{i}_{msg.get(group_col, i)}",
                    "trigger_index": i,
                    "trigger_message": msg,
                    "context_messages": context_messages,
                    "sender": msg.get(sender_col, "unknown"),
                })

        return test_cases

    async def run_from_manifest_file(
        self,
        manifest_path: str,
        created_by: str | None = None,
    ) -> ExperimentRun:
        """
        Execute a workflow experiment from a YAML manifest file.
        """
        manifest = WorkflowManifest.from_yaml(manifest_path)
        return await self.run_from_manifest(manifest, created_by)

    async def run_from_manifest(
        self,
        manifest: WorkflowManifest,
        created_by: str | None = None,
    ) -> ExperimentRun:
        """
        Execute a workflow experiment from a manifest config.
        """
        # Create ExperimentRun
        run = ExperimentRun(
            manifest_name=manifest.name,
            manifest_version=manifest.version,
            manifest_json=manifest.to_dict(),
            status=ExperimentStatus.RUNNING,
            started_at=datetime.utcnow(),
            created_by=created_by,
        )
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)

        logger.info(f"Starting workflow experiment: {manifest.name} v{manifest.version} (id={run.id})")

        try:
            # Load workflow and evaluator
            workflow = self._load_workflow(manifest)
            evaluator = self._load_evaluator(manifest)

            logger.info(f"Loaded workflow from: {manifest.workflow_path}")
            if evaluator:
                logger.info(f"Loaded evaluator from: {manifest.evaluator_path}")

            # Load and process conversation data
            csv_path = manifest.data_file or manifest.conversation_csv
            conversations = self._load_conversations(csv_path)
            logger.info(f"Loaded {len(conversations)} messages from CSV")

            # Find trigger sequences
            test_cases = self._find_trigger_sequences(
                conversations,
                manifest.trigger_keywords,
                manifest,
            )
            logger.info(f"Found {len(test_cases)} trigger sequences to test")

            run.total_cases = len(test_cases)

            # Execute workflow for each trigger
            results = await asyncio.gather(
                *[
                    self._execute_workflow_case(
                        run, workflow, evaluator, case, manifest
                    )
                    for case in test_cases
                ],
                return_exceptions=True,
            )

            # Commit all cases at once
            valid_cases = [r for r in results if isinstance(r, ExperimentCase)]
            for case in valid_cases:
                self.db.add(case)
            await self.db.commit()

            # Count outcomes
            success = sum(
                1 for r in results
                if isinstance(r, ExperimentCase) and r.outcome == CaseOutcome.SUCCESS.value
            )
            failure = sum(
                1 for r in results
                if isinstance(r, ExperimentCase) and r.outcome == CaseOutcome.FAILURE.value
            )
            error = sum(
                1 for r in results
                if isinstance(r, Exception)
                or (isinstance(r, ExperimentCase) and r.outcome == CaseOutcome.ERROR.value)
            )
            hitl_routed = sum(
                1 for r in results
                if isinstance(r, ExperimentCase) and r.outcome == CaseOutcome.NEEDS_REVIEW.value
            )

            # Update run stats
            run.status = ExperimentStatus.COMPLETED
            run.completed_at = datetime.utcnow()
            run.completed_cases = len(valid_cases)
            run.success_cases = success
            run.failure_cases = failure
            run.error_cases = error
            run.hitl_routed_cases = hitl_routed

        except Exception as e:
            logger.error(f"Workflow experiment failed: {e}", exc_info=True)
            run.status = ExperimentStatus.FAILED
            run.notes = f"Error: {str(e)}"
            run.completed_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(run)

        logger.info(
            f"Workflow experiment completed: {manifest.name} - "
            f"{run.success_cases}/{run.total_cases} success, "
            f"{run.error_cases} errors, "
            f"{run.hitl_routed_cases} needs review"
        )

        return run

    async def _execute_workflow_case(
        self,
        run: ExperimentRun,
        workflow: Any,
        evaluator: Callable | None,
        case: dict[str, Any],
        manifest: WorkflowManifest,
    ) -> ExperimentCase:
        """
        Execute workflow for a single test case.
        """
        async with self.semaphore:
            start_time = datetime.utcnow()

            msg_col = manifest.message_column
            sender_col = manifest.sender_column

            # Create case record
            experiment_case = ExperimentCase(
                run_id=run.id,
                case_id=case["test_id"],
                input_message=case["trigger_message"].get(msg_col, ""),
            )

            try:
                # Build initial state with message history
                messages = []
                for msg in case["context_messages"]:
                    messages.append(
                        HumanMessage(
                            content=msg.get(msg_col, ""),
                            name=msg.get(sender_col, "user"),
                        )
                    )

                initial_state = {
                    "messages": messages,
                    "negociacao_em_aberto": False,
                    "participante_1_id": None,
                    "participante_2_id": None,
                    "horario_abertura": None,
                    "contexto_relevante": None,
                    "negociacao_concluida": False,
                    "dados_validacao": None,
                    "dados_extraidos": None,
                    "boleta_formatada": None,
                }

                # Execute workflow
                config = {"configurable": {"thread_id": case["test_id"]}}

                # Run in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                final_state = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: workflow.invoke(initial_state, config)
                    ),
                    timeout=manifest.timeout_seconds
                )

                # Extract results
                boleta = final_state.get("boleta_formatada")
                dados_extraidos = final_state.get("dados_extraidos")
                negociacao_concluida = final_state.get("negociacao_concluida", False)

                experiment_case.actual_response = boleta or "No boleta generated"
                experiment_case.raw_response = {
                    "boleta_formatada": boleta,
                    "dados_extraidos": dados_extraidos,
                    "negociacao_concluida": negociacao_concluida,
                    "dados_validacao": final_state.get("dados_validacao"),
                }

                # Use evaluator if provided
                if evaluator:
                    # Create a mock run object for the evaluator
                    class MockRun:
                        def __init__(self, outputs):
                            self.outputs = outputs

                    mock_run = MockRun(final_state)
                    eval_result = evaluator(mock_run)

                    experiment_case.raw_response["evaluation"] = eval_result

                    if eval_result.get("boleta_gerada"):
                        experiment_case.outcome = CaseOutcome.SUCCESS.value
                        experiment_case.classification = ClassificationResult.HIGH_CONFIDENCE.value
                    else:
                        experiment_case.outcome = CaseOutcome.FAILURE.value
                        experiment_case.classification = ClassificationResult.LOW_CONFIDENCE.value
                else:
                    # Simple classification based on whether boleta was generated
                    if boleta:
                        experiment_case.outcome = CaseOutcome.SUCCESS.value
                        experiment_case.classification = ClassificationResult.HIGH_CONFIDENCE.value
                    elif negociacao_concluida:
                        experiment_case.outcome = CaseOutcome.NEEDS_REVIEW.value
                        experiment_case.classification = ClassificationResult.MEDIUM_CONFIDENCE.value
                    else:
                        experiment_case.outcome = CaseOutcome.FAILURE.value
                        experiment_case.classification = ClassificationResult.LOW_CONFIDENCE.value

                experiment_case.request_duration_ms = int(
                    (datetime.utcnow() - start_time).total_seconds() * 1000
                )

            except TimeoutError:
                logger.error(f"Case {case['test_id']} timed out after {manifest.timeout_seconds}s")
                experiment_case.outcome = CaseOutcome.ERROR.value
                experiment_case.error_message = f"Timeout after {manifest.timeout_seconds}s"
                experiment_case.request_duration_ms = manifest.timeout_seconds * 1000

            except Exception as e:
                logger.error(f"Case {case['test_id']} failed: {e}", exc_info=True)
                experiment_case.outcome = CaseOutcome.ERROR.value
                experiment_case.error_message = str(e)
                experiment_case.request_duration_ms = int(
                    (datetime.utcnow() - start_time).total_seconds() * 1000
                )

            return experiment_case
