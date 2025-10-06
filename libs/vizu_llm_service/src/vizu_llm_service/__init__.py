"""
Vizu LLM Service: Biblioteca centralizada para roteamento e instanciação de LLMs.
"""

from .client import get_model, ModelTier, ModelTask

# Expõe os componentes principais para serem facilmente importáveis.
__all__ = [
    "get_model",
    "ModelTier",
    "ModelTask",
]