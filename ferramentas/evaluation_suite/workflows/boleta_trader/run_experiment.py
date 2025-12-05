#!/usr/bin/env python3
"""
Workflow experiment runner with optional database persistence and Langfuse tracing.

Usage:
    # Standalone (JSON output only):
    python -m ferramentas.evaluation_suite.workflows.boleta_trader.run_experiment manifest.yaml

    # With CSV export:
    python -m ferramentas.evaluation_suite.workflows.boleta_trader.run_experiment manifest.yaml --export-csv

    # With database storage (requires DATABASE_URL):
    python -m ferramentas.evaluation_suite.workflows.boleta_trader.run_experiment manifest.yaml --db

    # With Langfuse tracing:
    python -m ferramentas.evaluation_suite.workflows.boleta_trader.run_experiment manifest.yaml --langfuse
"""

import csv
import sys
import os
import json
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


@dataclass
class ExperimentResult:
    """Result for a single test case with all node outputs."""
    test_id: str
    query: str  # Full conversation passed to check_negotiation node
    sender: str
    success: bool
    outcome: CaseOutcome
    duration_ms: int
    # Node outputs
    description: Optional[str] = None  # check_negotiation output (justificativa)
    extracted: Optional[Dict] = None  # extractor output (dados_extraidos)
    boleta_formatada: Optional[str] = None  # formatter output (final boleta)
    error: Optional[str] = None


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
    csv_path: Optional[str] = None

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
    limit: Optional[int] = None,
) -> ExperimentResult:
    """Execute workflow for a single test case."""
    start_time = datetime.utcnow()

    msg_col = manifest.get("message_column", "message")
    sender_col = manifest.get("sender_column", "nome_fantasia")

    query = case["trigger_message"].get(msg_col, "")

    result = ExperimentResult(
        test_id=case["test_id"],
        query=query,
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

        # Execute workflow and capture intermediate states
        # (The formatter node resets some fields, so we use stream to capture them)
        config = {"configurable": {"thread_id": case["test_id"]}}
        if langfuse_handler:
            config["callbacks"] = [langfuse_handler]

        # Track intermediate outputs before they get reset
        captured_contexto = None
        captured_validacao = None
        captured_extraidos = None
        final_state = None

        # Use stream to capture state at each node
        for state_update in workflow.stream(initial_state, config):
            # State updates come as {node_name: partial_state}
            for node_name, partial_state in state_update.items():
                # Capture contexto_relevante from gatekeeper before it gets cleared
                if partial_state.get("contexto_relevante"):
                    captured_contexto = partial_state["contexto_relevante"]
                # Capture dados_validacao from validator before it gets cleared
                if partial_state.get("dados_validacao"):
                    captured_validacao = partial_state["dados_validacao"]
                # Capture dados_extraidos from extractor before it gets cleared
                if partial_state.get("dados_extraidos"):
                    captured_extraidos = partial_state["dados_extraidos"]
                # Keep track of final state
                final_state = partial_state

        # Use captured values (these are from intermediate nodes before reset)
        result.query = captured_contexto or result.query

        if captured_validacao:
            result.description = captured_validacao.get("justificativa")

        result.extracted = captured_extraidos

        # boleta_formatada comes from final state (formatter doesn't reset this)
        if final_state:
            result.boleta_formatada = final_state.get("boleta_formatada")

        # Use evaluator if provided
        if evaluator:
            class MockRun:
                def __init__(self, outputs):
                    self.outputs = outputs

            # Create state with all captured values for evaluator
            eval_state = {
                "contexto_relevante": captured_contexto,
                "dados_validacao": captured_validacao,
                "dados_extraidos": captured_extraidos,
                "boleta_formatada": final_state.get("boleta_formatada") if final_state else None,
            }
            eval_result = evaluator(MockRun(eval_state))
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
                }
                case = ExperimentCase(
                    run_id=run.id,
                    case_id=result_dict["test_id"],
                    input_message=result_dict["query"],
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


# --- CSV Export ---

def export_to_csv(results: List[ExperimentResult], output_path: str) -> str:
    """
    Export experiment results to CSV with query and node outputs.

    Columns:
    - test_id: Case identifier
    - query: Full conversation passed to check_negotiation node
    - description: Output of check_negotiation node (justificativa)
    - extracted: Output of extractor node (JSON)
    - boleta_formatada: Output of formatter node (final boleta)
    - success: Whether the workflow succeeded
    - duration_ms: Execution time
    - error: Error message if any
    """
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "test_id",
            "query",
            "description",
            "extracted",
            "boleta_formatada",
            "success",
            "duration_ms",
            "error",
        ])
        writer.writeheader()

        for result in results:
            writer.writerow({
                "test_id": result.test_id,
                "query": result.query or "",
                "description": result.description or "",
                "extracted": json.dumps(result.extracted, ensure_ascii=False) if result.extracted else "",
                "boleta_formatada": result.boleta_formatada or "",
                "success": result.success,
                "duration_ms": result.duration_ms,
                "error": result.error or "",
            })

    logger.info(f"Exported {len(results)} results to CSV: {output_path}")
    return output_path


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
    export_csv: bool = False,
    limit: Optional[int] = None,
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

    # Apply limit if specified
    if limit and limit > 0:
        test_cases = test_cases[:limit]
        logger.info(f"Limited to {len(test_cases)} test cases")

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

    # Export to CSV if requested
    if export_csv:
        manifest_dir = Path(manifest_path).parent
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        csv_output_path = manifest_dir / f"results_{timestamp}.csv"
        export_to_csv(results, str(csv_output_path))
        summary.csv_path = str(csv_output_path)

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
    if summary.csv_path:
        logger.info(f"CSV Export: {summary.csv_path}")

    return summary


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run workflow experiment")
    parser.add_argument("manifest", help="Path to manifest YAML file")
    parser.add_argument("--output", "-o", help="Output JSON file for results")
    parser.add_argument("--db", action="store_true", help="Save results to database")
    parser.add_argument("--langfuse", action="store_true", help="Enable Langfuse tracing")
    parser.add_argument("--export-csv", action="store_true", help="Export results to CSV")
    parser.add_argument("--limit", type=int, help="Limit number of test cases to run")

    args = parser.parse_args()

    # Run experiment
    summary = run_experiment(
        args.manifest,
        use_db=args.db,
        use_langfuse=args.langfuse,
        export_csv=args.export_csv,
        limit=args.limit,
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
