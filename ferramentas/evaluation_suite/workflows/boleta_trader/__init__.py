# ferramentas/evaluation_suite/workflows/boleta_trader/__init__.py
"""
Boleta Trader Workflow - Trading ticket extraction from WhatsApp conversations.

Two versions available:
- workflow.py (v1): Direct Ollama access (legacy)
- workflow_v2.py (v2): Uses vizu_llm_service with multi-provider support

Usage:
    # V1 (legacy - direct Ollama)
    make experiment-workflow-local

    # V2 (recommended - vizu_llm_service)
    make experiment-workflow-v2

    # With CSV export
    make experiment-workflow-v2-export
"""

from .evaluator import evaluate_extraction_accuracy, summarize_for_manual_review
from .workflow import get_workflow
from .workflow_v2 import get_workflow as get_workflow_v2

__all__ = [
    "get_workflow",
    "get_workflow_v2",
    "summarize_for_manual_review",
    "evaluate_extraction_accuracy",
]
