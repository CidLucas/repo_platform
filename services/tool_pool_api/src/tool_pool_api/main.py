import logging
import sys

import uvicorn  # Importe o uvicorn

from .core.config import get_settings
from .server.mcp_server import create_mcp_server

# Configurar logging para todos os módulos do tool_pool_api e vizu_*
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Aumentar o nível de log para módulos específicos
logging.getLogger("tool_pool_api").setLevel(logging.DEBUG)
logging.getLogger("vizu_rag_factory").setLevel(logging.DEBUG)
logging.getLogger("vizu_qdrant_client").setLevel(logging.DEBUG)
logging.getLogger("vizu_llm_service").setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

# --- Carregamento e Registro ---
try:
    logger.info("Carregando servidor MCP e ferramentas...")
    # Desempacota o mcp e o app retornados pela função modificada
    mcp, app = create_mcp_server()
    logger.info("Servidor MCP e ferramentas carregados com sucesso.")
    settings = get_settings()
except Exception as e:
    logger.exception(f"Falha ao carregar o servidor MCP: {e}")
    raise

if __name__ == "__main__":
    logger.info("Iniciando servidor via Uvicorn direto")

    # Usamos uvicorn.run diretamente no objeto 'app' (FastAPI)
    # Isso ignora a configuração problemática do mcp.run()
    uvicorn.run(
        app,
        host="0.0.0.0",  # Necessário para Docker
        port=9000,
        ws="auto",  # A correção para o KeyError original
    )
