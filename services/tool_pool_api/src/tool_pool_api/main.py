import logging
from server.mcp_server import create_mcp_server
from core.config import get_settings
# (Remover import de StarletteMiddleware, não é mais necessário aqui)

logger = logging.getLogger(__name__)

# --- Carregamento e Registro ---
try:
    logger.info("Carregando servidor MCP e ferramentas...")
    mcp = create_mcp_server()
    logger.info("Servidor MCP e ferramentas carregados com sucesso.")
    settings = get_settings()
except Exception as e:
    logger.exception(f"Falha ao carregar o servidor MCP: {e}")
    raise



if __name__ == "__main__":
    # O 'mcp.run()' NÃO é usado. Usamos Uvicorn para rodar o 'app' ASGI.
    logger.info(f"Iniciando servidor")
    mcp.run(transport="http", host="127.0.0.1", port=9000)