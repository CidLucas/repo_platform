import logging

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# 1. Cria a instância principal do servidor MCP.
# "VizuToolPool" será o 'service_name' que os clientes usarão para se conectar.
logger.info("Criando instância FastMCP('VizuToolPool')...")
mcp = FastMCP("VizuToolPool")
logger.info("Instância MCP criada.")

# # 2. Importa os módulos de sessão e ferramentas para registar os decoradores.
# Estes arquivos ainda estão vazios, mas vamos preenchê-los a seguir.
# O simples ato de importá-los faz com que @mcp.tool e @mcp.session_manager
# sejam executados e registados na instância 'mcp'.
try:
    import tool_pool_api.server.session  # noqa: F401
    import tool_pool_api.server.tools  # noqa: F401
    logger.info("Módulos 'session' e 'tools' importados para registo.")
except ImportError:
    logger.warning("Não foi possível importar 'session' ou 'tools'. (Esperado no primeiro setup)")