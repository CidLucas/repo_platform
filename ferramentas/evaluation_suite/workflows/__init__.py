# ferramentas/evaluation_suite/workflows/__init__.py
"""
Centralized location for LangGraph workflow experiments.

Each workflow should be in its own subdirectory with:
- workflow.py: The LangGraph workflow definition
- evaluator.py: Optional evaluation functions
- manifest.yaml: Experiment configuration
- data/: Test datasets (CSV files)
"""
