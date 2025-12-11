"""
Definições de clientes de teste (personas).

Este arquivo é mantido para compatibilidade, mas agora importa
as definições centralizadas de vizu_models.seed_clients.

IMPORTANTE: Não edite SEED_CLIENTS aqui. Edite em libs/vizu_models/src/vizu_models/seed_clients.py
"""
from vizu_models import SEED_CLIENTS, get_all_rag_collections, get_client_by_name

# Re-export para compatibilidade
__all__ = ["SEED_CLIENTS", "get_client_by_name", "get_all_rag_collections"]
