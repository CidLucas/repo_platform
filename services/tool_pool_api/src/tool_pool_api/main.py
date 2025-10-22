import logging

# 1. Importa a instância 'mcp' principal do nosso mcp_server
# Esta instância já foi pré-configurada e teve as ferramentas
# e o session_manager registados no momento da importação.
from tool_pool_api.server.mcp_server import mcp

# (Opcional) Podemos ter uma função de inicialização aqui se
# precisarmos configurar loggers ou observabilidade antes de tudo.
# Por enquanto, nossas dependências já fazem isso.
# from tool_pool_api.core.observability import setup_observability
# setup_observability()

logger = logging.getLogger(__name__)

# 2. O ponto de entrada da aplicação
if __name__ == "__main__":
    """
    Este é o entrypoint do serviço, chamado pelo CMD no Dockerfile.
    Ele inicia o servidor MCP, que por sua vez é um servidor FastAPI.
    """
    logger.info("Iniciando o servidor MCP 'VizuToolPool'...")

    # O 'transport' define como o MCP se comunica.
    # "streamable-http" é o nosso padrão para streaming de respostas.
    mcp.run(transport="streamable-http")