# src/analytics_api/core/analytics_mapping.py
import logging

logger = logging.getLogger(__name__)

# Mapeia o ID do cliente (que virá do token JWT)
# para a tabela Prata física no Postgres.
_SILVER_TABLE_MAPPINGS = {
    "e2e-test-client": "pm_dados_faturamento_cliente_x",
    # "polen-client-id": "silver_transacoes_polen", # Exemplo futuro
}

def get_silver_table_name(client_id: str) -> str:
    """Retorna o nome da tabela Prata para o client_id."""
    table_name = _SILVER_TABLE_MAPPINGS.get(client_id)
    if not table_name:
        logger.error(f"Mapeamento Prata não encontrado para client_id: {client_id}")
        raise ValueError(f"Mapeamento Prata não encontrado para {client_id}")
    return table_name