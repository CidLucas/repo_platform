import logging
import uvicorn # Importe o uvicorn
from .server.mcp_server import create_mcp_server
from .core.config import get_settings

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
        host="0.0.0.0", # Necessário para Docker
        port=9000,
        ws="auto"       # A correção para o KeyError original
    )