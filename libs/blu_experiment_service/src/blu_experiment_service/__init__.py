# blu_experiment_service/__init__.py
"""
Blu Experiment Service - Langfuse-First Experiment Orchestration.

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

from blu_experiment_service.classifier import BatchClassifier, ResponseClassifier
from blu_experiment_service.config import ExperimentSettings, get_experiment_settings, settings
from blu_experiment_service.dataset_generator import TrainingDatasetGenerator
from blu_experiment_service.langfuse_runner import LangfuseExperimentRunner  # Langfuse-native runner
from blu_experiment_service.manifest import ManifestLoader
from blu_experiment_service.runner import ExperimentRunner  # Legacy runner (kept for compatibility)

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
