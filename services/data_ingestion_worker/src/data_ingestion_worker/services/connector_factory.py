"""
Factory para criação de conectores de dados.

Este módulo implementa o princípio de Agnosticismo:
- O worker não sabe qual conector vai usar até o momento da execução
- A escolha do conector é baseada no tipo_servico da credencial
"""

import logging
from typing import Any

# Conectores da lib compartilhada
from vizu_data_connectors import (
    LojaIntegradaConnector,
    ShopifyConnector,
    VTEXConnector,
)
from vizu_data_connectors.bigquery import BigQueryConnector
from google.cloud import bigquery

logger = logging.getLogger(__name__)


class ConnectorFactory:
    """
    Factory para criar conectores baseado no tipo de serviço.
    
    Responsável por:
    1. Buscar credenciais do Secret Manager
    2. Instanciar o conector apropriado
    """

    # Mapeamento de tipos de serviço para classes de conector
    _CONNECTOR_MAP = {
        "BIGQUERY": "bigquery",
        "SHOPIFY": "shopify",
        "VTEX": "vtex",
        "LOJA_INTEGRADA": "loja_integrada",
        "POSTGRESQL": "postgresql",
        "MYSQL": "mysql",
    }

    @classmethod
    async def create_connector(
        cls,
        tipo_servico: str,
        credentials: dict[str, Any]
    ) -> BigQueryConnector | ShopifyConnector | VTEXConnector | LojaIntegradaConnector:
        """
        Cria um conector baseado no tipo de serviço.
        
        Args:
            tipo_servico: Tipo do serviço (BIGQUERY, SHOPIFY, VTEX, etc.)
            credentials: Dicionário com as credenciais já descriptografadas
            
        Returns:
            Uma instância do conector apropriado
        """
        tipo = tipo_servico.upper()

        if tipo == "BIGQUERY":
            # BigQuery precisa de um client especial
            google_client = bigquery.Client()
            return BigQueryConnector(client=google_client)

        elif tipo == "SHOPIFY":
            return ShopifyConnector(credentials)

        elif tipo == "VTEX":
            return VTEXConnector(credentials)

        elif tipo == "LOJA_INTEGRADA":
            return LojaIntegradaConnector(credentials)

        else:
            raise ValueError(f"Tipo de serviço não suportado: {tipo_servico}")

    @classmethod
    def get_supported_resources(cls, tipo_servico: str) -> list:
        """
        Retorna os recursos suportados por cada tipo de conector.
        """
        resources = {
            "BIGQUERY": ["tables", "views"],
            "SHOPIFY": ["products", "orders", "customers", "inventory"],
            "VTEX": ["products", "orders", "customers", "inventory", "categories", "brands"],
            "LOJA_INTEGRADA": ["products", "orders", "customers", "inventory", "categories"],
            "POSTGRESQL": ["tables"],
            "MYSQL": ["tables"],
        }
        return resources.get(tipo_servico.upper(), [])
