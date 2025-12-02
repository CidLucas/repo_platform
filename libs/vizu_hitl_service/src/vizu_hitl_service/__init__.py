# libs/vizu_hitl_service/__init__.py
"""
Vizu HITL Service - Human-in-the-Loop para criação de datasets.

Fornece:
- HitlService: Avaliação de critérios e roteamento
- HitlQueue: Gerenciamento de fila Redis
- LangfuseDatasetManager: Integração com Langfuse datasets
"""

from .service import HitlService
from .queue import HitlQueue
from .langfuse_integration import LangfuseDatasetManager

__all__ = ["HitlService", "HitlQueue", "LangfuseDatasetManager"]
