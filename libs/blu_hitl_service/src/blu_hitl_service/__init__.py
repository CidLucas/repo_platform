# libs/blu_hitl_service/__init__.py
"""
Blu HITL Service - Human-in-the-Loop para criação de datasets.

Fornece:
- HitlService: Avaliação de critérios e roteamento
- HitlQueue: Gerenciamento de fila Redis
- LangfuseDatasetManager: Integração com Langfuse datasets
"""

from blu_hitl_service.langfuse_integration import LangfuseDatasetManager
from blu_hitl_service.queue import HitlQueue
from blu_hitl_service.service import HitlService

__all__ = ["HitlService", "HitlQueue", "LangfuseDatasetManager"]
