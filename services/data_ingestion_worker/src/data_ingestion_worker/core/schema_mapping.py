# src/data_ingestion_worker/core/schema_mapping.py

"""
Módulo de Configuração de Schema (Simples)

Centraliza o mapeamento "DE-PARA" das colunas de origem (ex: BigQuery)
para o nosso schema canônico interno (ex: PostgreSQL).

Princípio: Agnosticismo. O IngestionService não deve saber
o schema de nenhum cliente, apenas aplicar o mapeamento
que este módulo fornece.
"""
import logging

logger = logging.getLogger(__name__)

# Define o mapeamento para cada cliente.
# Chave: client_id
# Valor: Dicionário de {coluna_origem_no_BQ: coluna_destino_no_PG}

_CLIENT_MAPPINGS = {
    "e2e-test-client": {
        # --- Mapeamento Consolidado ---
        # Chave: "nome do campo no cliente" (Bronze/BQ)
        # Valor: "nome da coluna destino" (Silver/Postgres)

        # IDs e Transação
        "id_operatorinvoice": "order_id",
        "createdat_product": "data_transacao",        # Mantido do mapeamento original

        # Valores/Métricas
        "quantitytraded_product": "quantidade",
        "unitpricekg_product": "valor_unitario",
        "totalprice_product": "valor_total_emitter",  # Valor da Cooperativa (antigo 'valor_total')
        "price_operatorinvoice": "valor_total_receiver", # Valor do Cliente (para cálculo de frete)

        # Emissor (Cooperativa / Vendedor)
        "emitterlegalname": "emitter_nome",
        "emittercity": "emitter_cidade",
        "emitterstateuf": "emitter_estado_uf",

        # Receptor (Cliente)
        "receiverlegalname": "receiver_nome",
        "receivercity": "receiver_cidade",

        # Produto (Campos Brutos para Normalização)
        "description_product": "raw_product_description", # Será normalizado pelo analytics_api
        "material": "raw_product_category",       # Será normalizado pelo analytics_api
        "ncm": "raw_ncm",                         # Será normalizado pelo analytics_api

        # Fiscal (Campo Bruto para Normalização)
        "cfop": "raw_cfop",                       # Será normalizado pelo analytics_api

        # Dados Cadastrais do Emissor (Fornecedor)
        "emitterlegalname": "emitter_nome",
        "emitterlegaldoc": "emitter_cnpj",
        "emitterphone": "emitter_telefone",
        "emitterstateuf": "emitter_estado",
        "emittercity": "emitter_cidade",

        # Dados Cadastrais do Receptor (Cliente)
        "receiverlegalname": "receiver_nome",
        "receiverlegaldoc": "receiver_cnpj",
        "receiverphone": "receiver_telefone", # Assumindo que este campo existe
        "receiverstateuf": "receiver_estado", # Assumindo que este campo existe
        "receivercity": "receiver_cidade"
    },
    # ... mapeamentos para outros clientes (ex: Polen, se for um ID diferente)
}


def get_schema_mapping(client_id: str) -> dict[str, str]:
    """
    Busca o mapeamento de colunas para um client_id específico.
    
    Em uma versão futura, isso poderia buscar de um banco de dados
    ou de um arquivo JSON/YAML no GCS. Por enquanto, cumpre o
    requisito de ser "simples e inputado na mão".
    """
    mapping = _CLIENT_MAPPINGS.get(client_id)
    if not mapping:
        logger.error(f"Mapeamento de schema não encontrado para o client_id: {client_id}")
        # É crucial falhar aqui para evitar ingestão de dados incorretos
        raise ValueError(f"Mapeamento de schema não encontrado para {client_id}")

    logger.info(f"Mapeamento de schema carregado para {client_id}")
    return mapping

def get_source_columns(client_id: str) -> list[str]:
    """Helper que retorna a lista de colunas de ORIGEM para a query SQL."""
    mapping = get_schema_mapping(client_id)
    return list(mapping.keys())
