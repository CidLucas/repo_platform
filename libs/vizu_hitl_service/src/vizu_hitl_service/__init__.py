# libs/vizu_hitl_service/__init__.py
"""
Vizu HITL Service - Human-in-the-Loop para criação de datasets.

Fornece:
- HitlService: Avaliação de critérios e roteamento
- HitlQueue: Gerenciamento de fila Redis
- LangfuseDatasetManager: Integração com Langfuse datasets
"""

from .langfuse_integration import LangfuseDatasetManager
from .queue import HitlQueue
from .service import HitlService

__all__ = ["HitlService", "HitlQueue", "LangfuseDatasetManager"]
