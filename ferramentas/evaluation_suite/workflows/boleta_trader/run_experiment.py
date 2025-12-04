#!/usr/bin/env python3
"""
Workflow experiment runner with optional database persistence and Langfuse tracing.

Usage:
    # Standalone (JSON output only):
    python -m ferramentas.evaluation_suite.workflows.boleta_trader.run_experiment manifest.yaml

    # With database storage (requires DATABASE_URL):
    python -m ferramentas.evaluation_suite.workflows.boleta_trader.run_experiment manifest.yaml --db

    # With Langfuse tracing:
    python -m ferramentas.evaluation_suite.workflows.boleta_trader.run_experiment manifest.yaml --langfuse
"""

import sys
import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum

import yaml
import pandas as pd
from langchain_core.messages import HumanMessage
import difflib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# --- Data Classes ---

class CaseOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"
    NEEDS_REVIEW = "needs_review"


@dataclass
class ExperimentResult:
    """Result for a single test case."""
    test_id: str
    trigger_message: str
    sender: str
    success: bool
    outcome: CaseOutcome
    duration_ms: int
    boleta_formatada: Optional[str] = None
    dados_extraidos: Optional[Dict] = None
    dados_validacao: Optional[Dict] = None
    evaluation: Optional[Dict] = None
    error: Optional[str] = None
    langfuse_trace_id: Optional[str] = None


@dataclass
class ExperimentSummary:
    """Summary of an experiment run."""
    manifest_name: str
    manifest_version: str
    run_id: str
    started_at: str
    completed_at: Optional[str] = None
    total_cases: int = 0
    success_cases: int = 0
    failure_cases: int = 0
    error_cases: int = 0
    results: List[Dict] = field(default_factory=list)
    db_run_id: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


# --- Manifest Loading ---

def load_manifest(manifest_path: str) -> Dict[str, Any]:
    """Load manifest from YAML file."""
    with open(manifest_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# --- Module Loading ---

def load_module(module_path: str) -> Any:
    """
    Dynamically load a Python module.
    Supports both file paths and dotted module paths.
    """
    import importlib
    import importlib.util

    if "/" in module_path or module_path.endswith(".py"):
        path = Path(module_path)
        if not path.exists():
            raise FileNotFoundError(f"Module file not found: {module_path}")
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    else:
        try:
            return importlib.import_module(module_path)
        except ImportError:
            # Add project root to path
            project_root = Path(__file__).parent.parent.parent.parent.parent
            sys.path.insert(0, str(project_root))
            sys.path.insert(0, str(project_root / "ferramentas"))
            return importlib.import_module(module_path)


def load_workflow(manifest: Dict[str, Any]) -> Any:
    """Load the LangGraph workflow from the manifest."""
    module = load_module(manifest["workflow_path"])
    fn_name = manifest.get("workflow_function", "get_workflow")
    return getattr(module, fn_name)()


def load_evaluator(manifest: Dict[str, Any]) -> Optional[Callable]:
    """Load the evaluator function from the manifest."""
    evaluator_path = manifest.get("evaluator_path")
    if not evaluator_path:
        return None
    module = load_module(evaluator_path)
    fn_name = manifest.get("evaluator_function", "summarize_for_manual_review")
    return getattr(module, fn_name)


# --- Data Loading ---

def load_conversations(csv_path: str) -> List[Dict[str, Any]]:
    """Load conversation data from CSV."""
    df = pd.read_csv(csv_path)
    return df.to_dict("records")


def find_trigger_sequences(
    messages: List[Dict[str, Any]],
    trigger_keywords: List[str],
    message_column: str = "message",
    sender_column: str = "nome_fantasia",
    group_column: str = "test_id",
    context_window: int = 15,
) -> List[Dict[str, Any]]:
    """Find messages that contain trigger keywords and extract context."""
    test_cases = []

    for i, msg in enumerate(messages):
        content = msg.get(message_column, "").lower().strip()

        # Check for trigger keyword matches
        is_trigger = any(
            difflib.get_close_matches(w, trigger_keywords, n=1, cutoff=0.8)
            for w in content.split()
        )

        if is_trigger:
            start_idx = max(0, i - context_window)
            context_messages = messages[start_idx:i + 1]

            test_cases.append({
                "test_id": f"trigger_{i}_{msg.get(group_column, i)}",
                "trigger_index": i,
                "trigger_message": msg,
                "context_messages": context_messages,
                "sender": msg.get(sender_column, "unknown"),
            })

    return test_cases


# --- Workflow Execution ---

def execute_workflow_case(
    workflow: Any,
    case: Dict[str, Any],
    evaluator: Optional[Callable],
    manifest: Dict[str, Any],
    langfuse_handler: Any = None,
) -> ExperimentResult:
    """Execute workflow for a single test case."""
    start_time = datetime.utcnow()

    msg_col = manifest.get("message_column", "message")
    sender_col = manifest.get("sender_column", "nome_fantasia")

    result = ExperimentResult(
        test_id=case["test_id"],
        trigger_message=case["trigger_message"].get(msg_col, ""),
        sender=case["sender"],
        success=False,
        outcome=CaseOutcome.ERROR,
        duration_ms=0,
    )

    try:
        # Build initial state with message history
        messages = [
            HumanMessage(
                content=msg.get(msg_col, ""),
                name=msg.get(sender_col, "user"),
            )
            for msg in case["context_messages"]
        ]

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
        if langfuse_handler:
            config["callbacks"] = [langfuse_handler]

        final_state = workflow.invoke(initial_state, config)

        # Extract results
        result.boleta_formatada = final_state.get("boleta_formatada")
        result.dados_extraidos = final_state.get("dados_extraidos")
        result.dados_validacao = final_state.get("dados_validacao")

        # Use evaluator if provided
        if evaluator:
            class MockRun:
                def __init__(self, outputs):
                    self.outputs = outputs

            eval_result = evaluator(MockRun(final_state))
            result.evaluation = eval_result
            result.success = eval_result.get("boleta_gerada", False)
            result.outcome = CaseOutcome.SUCCESS if result.success else CaseOutcome.FAILURE
        else:
            result.success = result.boleta_formatada is not None
            result.outcome = CaseOutcome.SUCCESS if result.success else CaseOutcome.FAILURE

        result.duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

    except Exception as e:
        logger.error(f"Case {case['test_id']} failed: {e}", exc_info=True)
        result.error = str(e)
        result.outcome = CaseOutcome.ERROR
        result.duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

    return result


# --- Database Integration (Optional) ---

def save_to_database(summary: ExperimentSummary, manifest: Dict[str, Any]) -> Optional[str]:
    """Save experiment results to database using vizu_db_connector."""
    try:
        from vizu_db_connector.database import SessionLocal
        from vizu_models import ExperimentRun, ExperimentCase, ExperimentStatus, CaseOutcome as DBCaseOutcome

        db = SessionLocal()
        try:
            # Create experiment run
            run = ExperimentRun(
                manifest_name=manifest["name"],
                manifest_version=manifest.get("version", "1.0.0"),
                manifest_json=manifest,
                status=ExperimentStatus.COMPLETED,
                started_at=datetime.fromisoformat(summary.started_at),
                completed_at=datetime.utcnow(),
                total_cases=summary.total_cases,
                completed_cases=summary.total_cases,
                success_cases=summary.success_cases,
                failure_cases=summary.failure_cases,
                error_cases=summary.error_cases,
            )
            db.add(run)
            db.commit()
            db.refresh(run)

            # Create experiment cases
            for result_dict in summary.results:
                outcome_map = {
                    "success": DBCaseOutcome.SUCCESS,
                    "failure": DBCaseOutcome.FAILURE,
                    "error": DBCaseOutcome.ERROR,
                    "needs_review": DBCaseOutcome.NEEDS_REVIEW,
                }
                case = ExperimentCase(
                    run_id=run.id,
                    case_id=result_dict["test_id"],
                    input_message=result_dict["trigger_message"],
                    actual_response=result_dict.get("boleta_formatada"),
                    raw_response=result_dict,
                    outcome=outcome_map.get(result_dict["outcome"], DBCaseOutcome.ERROR).value,
                    request_duration_ms=result_dict["duration_ms"],
                    error_message=result_dict.get("error"),
                )
                db.add(case)

            db.commit()
            logger.info(f"Saved experiment run to database: {run.id}")
            return str(run.id)

        finally:
            db.close()

    except ImportError as e:
        logger.warning(f"Database not available (missing dependencies): {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to save to database: {e}")
        return None


# --- Langfuse Integration (Optional) ---

def get_langfuse_handler(manifest: Dict[str, Any], run_id: str):
    """Get Langfuse callback handler if configured."""
    try:
        from langfuse.callback import CallbackHandler

        host = os.getenv("LANGFUSE_HOST")
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")

        if not all([host, public_key, secret_key]):
            logger.info("Langfuse not configured (missing env vars)")
            return None

        handler = CallbackHandler(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
            session_id=run_id,
            tags=[manifest["name"], "workflow-experiment"],
        )
        logger.info(f"Langfuse tracing enabled: {host}")
        return handler

    except ImportError:
        logger.info("Langfuse not available (package not installed)")
        return None


# --- Main Runner ---

def run_experiment(
    manifest_path: str,
    use_db: bool = False,
    use_langfuse: bool = False,
) -> ExperimentSummary:
    """Run a workflow experiment from a manifest file."""
    import uuid

    # Load manifest
    manifest = load_manifest(manifest_path)
    run_id = str(uuid.uuid4())

    logger.info(f"Starting experiment: {manifest['name']} (run_id={run_id})")
    logger.info(f"  Workflow: {manifest['workflow_path']}")
    logger.info(f"  Dataset: {manifest.get('data_file')}")

    summary = ExperimentSummary(
        manifest_name=manifest["name"],
        manifest_version=manifest.get("version", "1.0.0"),
        run_id=run_id,
        started_at=datetime.utcnow().isoformat(),
    )

    # Load workflow and evaluator
    workflow = load_workflow(manifest)
    logger.info("Workflow loaded successfully")

    evaluator = load_evaluator(manifest)
    if evaluator:
        logger.info(f"Evaluator loaded: {manifest.get('evaluator_path')}")

    # Setup Langfuse if requested
    langfuse_handler = None
    if use_langfuse:
        langfuse_handler = get_langfuse_handler(manifest, run_id)

    # Load conversations
    csv_path = manifest.get("data_file") or manifest.get("conversation_csv")
    conversations = load_conversations(csv_path)
    logger.info(f"Loaded {len(conversations)} messages from CSV")

    # Find trigger sequences
    trigger_keywords = manifest.get("trigger_keywords", ["fecha", "fechado", "trava", "fechamos"])
    test_cases = find_trigger_sequences(
        conversations,
        trigger_keywords,
        message_column=manifest.get("message_column", "message"),
        sender_column=manifest.get("sender_column", "nome_fantasia"),
        group_column=manifest.get("conversation_group_column", "test_id"),
    )
    logger.info(f"Found {len(test_cases)} trigger sequences to test")

    summary.total_cases = len(test_cases)

    # Run each test case
    results = []
    for i, case in enumerate(test_cases):
        logger.info(f"Running case {i+1}/{len(test_cases)}: {case['test_id']}")
        result = execute_workflow_case(
            workflow, case, evaluator, manifest, langfuse_handler
        )
        results.append(result)

        status = "✓" if result.success else "✗"
        logger.info(f"  {status} {result.test_id} ({result.duration_ms}ms)")

    # Update summary
    summary.completed_at = datetime.utcnow().isoformat()
    summary.success_cases = sum(1 for r in results if r.outcome == CaseOutcome.SUCCESS)
    summary.error_cases = sum(1 for r in results if r.outcome == CaseOutcome.ERROR)
    summary.failure_cases = summary.total_cases - summary.success_cases - summary.error_cases
    summary.results = [asdict(r) for r in results]

    # Save to database if requested
    if use_db:
        db_run_id = save_to_database(summary, manifest)
        summary.db_run_id = db_run_id

    # Print summary
    logger.info(f"\n{'='*50}")
    logger.info("Experiment Results")
    logger.info(f"{'='*50}")
    logger.info(f"Run ID: {summary.run_id}")
    logger.info(f"Total cases: {summary.total_cases}")
    logger.info(f"Success: {summary.success_cases} ({100*summary.success_cases/max(1,summary.total_cases):.1f}%)")
    logger.info(f"Failures: {summary.failure_cases}")
    logger.info(f"Errors: {summary.error_cases}")
    if summary.db_run_id:
        logger.info(f"Database Run ID: {summary.db_run_id}")

    return summary


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run workflow experiment")
    parser.add_argument("manifest", help="Path to manifest YAML file")
    parser.add_argument("--output", "-o", help="Output JSON file for results")
    parser.add_argument("--db", action="store_true", help="Save results to database")
    parser.add_argument("--langfuse", action="store_true", help="Enable Langfuse tracing")

    args = parser.parse_args()

    # Run experiment
    summary = run_experiment(
        args.manifest,
        use_db=args.db,
        use_langfuse=args.langfuse,
    )

    # Determine output path
    output_path = args.output
    if not output_path:
        # Default: save next to manifest
        manifest_dir = Path(args.manifest).parent
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_path = manifest_dir / f"results_{timestamp}.json"

    # Save results
    with open(output_path, "w") as f:
        json.dump(summary.to_dict(), f, indent=2, default=str)
    logger.info(f"Results saved to: {output_path}")

    return 0 if summary.error_cases == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
