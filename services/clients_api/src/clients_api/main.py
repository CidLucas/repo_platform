# services/clients_api/src/clients_api/main.py (VERSÃO CORRIGIDA)
from fastapi import FastAPI, Request
from .api.router import api_router
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError  # Importação crítica
from starlette.exceptions import HTTPException as StarletteHTTPException


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

    @app.exception_handler(IntegrityError)
    async def integrity_exception_handler(request: Request, exc: IntegrityError):
        """
        Captura erros de violação de restrição de integridade (Ex: chave duplicada)
        e retorna um erro 409 (Conflict).
        """
        # Você pode inspecionar 'exc.orig' para obter a mensagem de erro específica do psycopg2
        # ou usar uma mensagem genérica se for um erro interno de DB
        return JSONResponse(
            status_code=409,  # 409 Conflict é um bom código para duplicação de recursos
            content={
                "detail": "O recurso já existe ou viola uma regra de unicidade de dados (ex: api_key duplicada)."
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        # Garante que até mesmo erros HTTPException retornem JSON
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    return app


# A instância 'app' agora é criada apenas quando o arquivo é executado diretamente.
# Os testes importarão a factory 'create_app' em vez disso.
app = create_app()
