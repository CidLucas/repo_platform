# services/clients_api/src/clients_api/main.py (VERSÃO CORRIGIDA)
from fastapi import FastAPI
from .api.router import api_router

def create_app() -> FastAPI:
    """
    Cria e configura a instância da aplicação FastAPI.
    Este padrão (Application Factory) é essencial para testes.
    """
    app = FastAPI(title="Clients API - Vizu")

    # Inclui o router agregador na aplicação, com um prefixo global de versão
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["Monitoring"])
    def health_check():
        return {"status": "ok"}

    return app

# A instância 'app' agora é criada apenas quando o arquivo é executado diretamente.
# Os testes importarão a factory 'create_app' em vez disso.
app = create_app()