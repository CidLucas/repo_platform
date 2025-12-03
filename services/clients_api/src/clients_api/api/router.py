# services/clients_api/src/clients_api/api/router.py (VERSÃO CORRIGIDA - AGREGADOR)
from fastapi import APIRouter

# Importa os routers de cada entidade (os "gerentes de departamento")
from .endpoints import clientes, configuracoes

# Declara o router principal (o "gerente geral")
api_router = APIRouter()

# Inclui os routers específicos, adicionando prefixos e tags para organização
api_router.include_router(clientes.router, prefix="/clientes", tags=["Clientes"])
api_router.include_router(
    configuracoes.router, prefix="/configuracoes", tags=["Configurações"]
)
