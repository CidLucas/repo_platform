# src/analytics_api/main.py
from fastapi import FastAPI
from analytics_api.api.router import api_router
from analytics_api.core.config import settings
import logging

# Configuração básica de logging (melhorar com observability_bootstrap)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LOG PARA VERIFICAR A URL DO BANCO
logger.info(f"DATABASE_URL em uso: {settings.DATABASE_URL}")

# TODO: Importar e configurar o vizu_observability_bootstrap
# (Conforme Manual de Engenharia)
# from vizu_observability_bootstrap import bootstrap
# bootstrap(service_name="analytics-api")

# --- Criação da Instância FastAPI ---
# Esta é a variável 'app' que o Uvicorn procura
app = FastAPI(
    title="Vizu Analytics API",
    version="0.1.0",
    description="Serviço responsável pelos cálculos Silver -> Gold e RAG."
    # TODO: Adicionar configuração de OpenAPI (docs_url, redoc_url)
)

# Rota de Health Check
@app.get("/health", tags=["Infra"])
def health_check():
    """Verifica se a API está operacional."""
    logger.info("Health check solicitado.")
    return {"status": "ok", "service": "analytics-api", "client_id_configurado": settings.MOCK_CLIENT_ID}

# Inclui todas as rotas (Home, Rankings, Detalhe) com prefixo /api/v1
logger.info("Incluindo rotas da API com prefixo /api/v1")
app.include_router(api_router, prefix="/api/v1")

# (Opcional, mas recomendado para desenvolvimento local com React)
# Configurar CORS se o frontend estiver noutro domínio (ex: localhost:3000)
from fastapi.middleware.cors import CORSMiddleware

origins = [
    "http://localhost:3000", # Assumindo que o React corre na porta 3000
    "http://127.0.0.1:3000",
    # Adicionar a URL do frontend em produção/staging
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Permite todos os métodos (GET, POST, etc.)
    allow_headers=["*"], # Permite todos os headers
)
logger.info(f"Middleware CORS configurado para permitir origens: {origins}")

# Bloco para permitir execução direta com 'python src/analytics_api/main.py' (embora usemos Uvicorn)
if __name__ == "__main__":
    import uvicorn
    logger.info("Iniciando servidor Uvicorn para desenvolvimento local...")
    # Usamos host="0.0.0.0" para permitir acesso de fora do container (se rodado em Docker)
    # ou de outras máquinas na rede local. Usamos a porta 8001 como padrão.
    uvicorn.run(app, host="0.0.0.0", port=8001)