#!/usr/bin/env python3
"""
Experiment Orchestrator CLI - Langfuse-First Architecture

Usage:
    # Run experiment (uses Langfuse SDK)
    python -m vizu_experiment_service.cli run <manifest.yaml>

    # Run with legacy runner (httpx only)
    python -m vizu_experiment_service.cli run <manifest.yaml> --legacy

    # Sync manifest to Langfuse Dataset
    python -m vizu_experiment_service.cli sync <manifest.yaml>

    # Classify results and route to HITL
    python -m vizu_experiment_service.cli classify <run_id>

    # Export approved cases to training dataset
    python -m vizu_experiment_service.cli export <run_id> --format jsonl
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_experiment(
    manifest_path: str,
    created_by: str = None,
    use_legacy: bool = False,
):
    """Run an experiment from a manifest file."""
    from sqlmodel.ext.asyncio.session import AsyncSession
    from sqlalchemy.ext.asyncio import create_async_engine

    from .config import settings
    from .manifest import ManifestLoader

    # Load manifest first to validate
    manifest = ManifestLoader.load_from_file(manifest_path)
    logger.info(f"Loaded manifest: {manifest.name} v{manifest.version}")
    logger.info(f"  Clients: {len(manifest.clients)}")
    logger.info(f"  Test cases: {len(manifest.cases)}")

    # Create async DB session
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False,
    )

    async with AsyncSession(engine) as session:
        if use_legacy:
            # Use legacy ExperimentRunner (httpx only)
            from .runner import ExperimentRunner

            logger.info("Using LEGACY runner (httpx)")
            runner = ExperimentRunner(
                db_session=session,
                atendente_url=manifest.api_url or settings.ATENDENTE_API_URL,
                concurrent_limit=manifest.parallel_requests,
            )

            run = await runner.run_from_manifest(manifest, created_by=created_by)

            logger.info(f"\n{'='*50}")
            logger.info("Experiment Run Completed (Legacy)")
            logger.info(f"{'='*50}")
            logger.info(f"Run ID: {run.id}")
            logger.info(f"Status: {run.status}")
            logger.info(f"Total cases: {run.total_cases}")
            logger.info(f"Success: {run.success_cases}")
            logger.info(f"Failures: {run.failure_cases}")
            logger.info(f"Errors: {run.error_cases}")
            logger.info(f"HITL routed: {run.hitl_routed_cases}")

            return run
        else:
            # Use Langfuse-native runner (RECOMMENDED)
            from .langfuse_runner import LangfuseExperimentRunner

            logger.info("Using LANGFUSE runner (recommended)")
            runner = LangfuseExperimentRunner(
                db_session=session,
                atendente_url=manifest.api_url or settings.ATENDENTE_API_URL,
            )

            result = await runner.run_from_manifest(manifest, created_by=created_by)

            logger.info(f"\n{'='*50}")
            logger.info("Experiment Run Completed (Langfuse)")
            logger.info(f"{'='*50}")
            logger.info(f"Dataset: {result.get('dataset_name')}")
            logger.info(f"Run Name: {result.get('run_name')}")
            logger.info(f"Local Run ID: {result.get('local_run_id')}")
            logger.info(f"Total Items: {result.get('total_items')}")
            logger.info("\nView results in Langfuse UI → Datasets → Experiments")

            return result


async def run_workflow_experiment(
    manifest_path: str,
    created_by: str = None,
):
    """Run a workflow experiment from a YAML manifest file."""
    from sqlmodel.ext.asyncio.session import AsyncSession
    from sqlalchemy.ext.asyncio import create_async_engine

    from .config import settings
    from .workflow_runner import WorkflowManifest, WorkflowExperimentRunner

    # Load manifest first to validate
    manifest = WorkflowManifest.from_yaml(manifest_path)
    logger.info(f"Loaded workflow manifest: {manifest.name} v{manifest.version}")
    logger.info(f"  Workflow: {manifest.workflow_path}")
    logger.info(f"  Dataset: {manifest.conversation_csv}")

    # Create async DB session
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False,
    )

    async with AsyncSession(engine) as session:
        runner = WorkflowExperimentRunner(
            db_session=session,
            concurrent_limit=3,
        )

        run = await runner.run_from_manifest(manifest, created_by=created_by)

        logger.info(f"\n{'='*50}")
        logger.info("Workflow Experiment Completed")
        logger.info(f"{'='*50}")
        logger.info(f"Run ID: {run.id}")
        logger.info(f"Status: {run.status}")
        logger.info(f"Total cases: {run.total_cases}")
        logger.info(f"Success: {run.success_cases}")
        logger.info(f"Failures: {run.failure_cases}")
        logger.info(f"Errors: {run.error_cases}")
        logger.info(f"HITL routed: {run.hitl_routed_cases}")

        return run


async def sync_manifest(manifest_path: str):
    """Sync manifest to Langfuse Dataset without running experiment."""
    from .manifest import ManifestLoader
    from .langfuse_runner import LangfuseExperimentRunner

    manifest = ManifestLoader.load_from_file(manifest_path)
    logger.info(f"Loaded manifest: {manifest.name} v{manifest.version}")

    runner = LangfuseExperimentRunner()
    dataset_name = await runner.sync_manifest_to_dataset(manifest)

    logger.info(f"\n{'='*50}")
    logger.info("Manifest Synced to Langfuse")
    logger.info(f"{'='*50}")
    logger.info(f"Dataset: {dataset_name}")
    logger.info(f"Clients: {len(manifest.clients)}")
    logger.info(f"Cases: {len(manifest.cases)}")
    logger.info("\nView in Langfuse UI → Datasets")

    return dataset_name


async def classify_run(run_id: str, route_to_hitl: bool = True):
    """Classify all cases in a run and optionally route to HITL."""
    from uuid import UUID
    from sqlmodel import select
    from sqlmodel.ext.asyncio.session import AsyncSession
    from sqlalchemy.ext.asyncio import create_async_engine

    from vizu_models import ExperimentRun
    from .config import settings
    from .classifier import ResponseClassifier

    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False,
    )

    async with AsyncSession(engine) as session:
        # Find the run
        stmt = select(ExperimentRun).where(ExperimentRun.id == UUID(run_id))
        result = await session.exec(stmt)
        run = result.first()

        if not run:
            logger.error(f"Run not found: {run_id}")
            return None

        classifier = ResponseClassifier(db_session=session)
        counts = await classifier.classify_run(run, route_to_hitl=route_to_hitl)

        logger.info(f"\n{'='*50}")
        logger.info("Classification Results")
        logger.info(f"{'='*50}")
        for key, value in counts.items():
            logger.info(f"  {key}: {value}")

        return counts


async def export_run(run_id: str, output_format: str = "jsonl", output_path: str = None):
    """Export cases from a run to a file."""
    from uuid import UUID
    from sqlmodel.ext.asyncio.session import AsyncSession
    from sqlalchemy.ext.asyncio import create_async_engine

    from .config import settings
    from .dataset_generator import TrainingDatasetGenerator

    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False,
    )

    async with AsyncSession(engine) as session:
        generator = TrainingDatasetGenerator(db_session=session)

        data = await generator.export_run_to_jsonl(
            run_id=UUID(run_id),
            include_high_confidence=True,
            include_reviewed=True,
        )

        if output_path:
            Path(output_path).write_text(data)
            logger.info(f"Exported to {output_path}")
        else:
            print(data)

        return data


def main():
    parser = argparse.ArgumentParser(description="Experiment Orchestrator CLI - Langfuse-First")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run an experiment")
    run_parser.add_argument("manifest", help="Path to manifest YAML file")
    run_parser.add_argument("--created-by", help="User running the experiment")
    run_parser.add_argument(
        "--legacy",
        action="store_true",
        help="Use legacy runner (httpx) instead of Langfuse SDK",
    )

    # Workflow command (NEW)
    workflow_parser = subparsers.add_parser("workflow", help="Run a LangGraph workflow experiment")
    workflow_parser.add_argument("manifest", help="Path to workflow manifest YAML file")
    workflow_parser.add_argument("--created-by", help="User running the experiment")

    # Sync command (new)
    sync_parser = subparsers.add_parser("sync", help="Sync manifest to Langfuse Dataset")
    sync_parser.add_argument("manifest", help="Path to manifest YAML file")

    # Classify command
    classify_parser = subparsers.add_parser("classify", help="Classify a run")
    classify_parser.add_argument("run_id", help="Experiment run ID")
    classify_parser.add_argument("--no-hitl", action="store_true", help="Skip HITL routing")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export run data")
    export_parser.add_argument("run_id", help="Experiment run ID")
    export_parser.add_argument("--format", default="jsonl", choices=["jsonl", "csv"])
    export_parser.add_argument("--output", help="Output file path")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Get run statistics")
    stats_parser.add_argument("run_id", help="Experiment run ID")

    args = parser.parse_args()

    if args.command == "run":
        asyncio.run(
            run_experiment(
                args.manifest,
                args.created_by,
                use_legacy=args.legacy,
            )
        )

    elif args.command == "workflow":
        asyncio.run(
            run_workflow_experiment(
                args.manifest,
                args.created_by,
            )
        )

    elif args.command == "sync":
        asyncio.run(sync_manifest(args.manifest))

    elif args.command == "classify":
        asyncio.run(classify_run(args.run_id, route_to_hitl=not args.no_hitl))

    elif args.command == "export":
        asyncio.run(export_run(args.run_id, args.format, args.output))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
