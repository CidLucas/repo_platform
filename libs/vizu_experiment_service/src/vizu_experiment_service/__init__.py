# vizu_experiment_service/__init__.py
"""
Vizu Experiment Service - Langfuse-First Experiment Orchestration.

Architecture:
- PRIMARY: Use Langfuse SDK for experiment execution and datasets
- LOCAL: YAML manifests for config, CLI for triggers, DB for tracking
- HITL: Streamlit dashboard for human review, sync results to Langfuse

This service coordinates:
1. Manifest loading (YAML → Langfuse Dataset sync)
2. Experiment execution via langfuse.run_experiment()
3. Result classification and HITL routing
4. Training dataset generation from approved cases
"""

from .config import settings, ExperimentSettings, get_experiment_settings
from .manifest import ManifestLoader
from .runner import ExperimentRunner  # Legacy runner (kept for compatibility)
from .langfuse_runner import LangfuseExperimentRunner  # Langfuse-native runner
from .classifier import ResponseClassifier, BatchClassifier
from .dataset_generator import TrainingDatasetGenerator

__all__ = [
    # Config
    "settings",
    "ExperimentSettings",
    "get_experiment_settings",
    # Manifest
    "ManifestLoader",
    # Runners
    "ExperimentRunner",  # Legacy - uses httpx directly
    "LangfuseExperimentRunner",  # Langfuse-native - RECOMMENDED
    # Classifier
    "ResponseClassifier",
    "BatchClassifier",
    # Dataset
    "TrainingDatasetGenerator",
]

