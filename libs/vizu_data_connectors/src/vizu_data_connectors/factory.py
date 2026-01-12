"""
Factory for creating data connectors.

This module implements the Factory pattern to create appropriate connectors
based on service type at runtime.
"""

import logging
from typing import Any

from vizu_data_connectors.ecommerce import (
    LojaIntegradaConnector,
    ShopifyConnector,
    VTEXConnector,
)

logger = logging.getLogger(__name__)


class ConnectorFactory:
    """
    Factory for creating connectors based on service type.

    Responsible for:
    1. Instantiating the appropriate connector
    2. Handling optional dependencies (e.g., BigQuery)
    """

    # Mapping of service types to connector names
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
    ):
        """
        Creates a connector based on service type.

        Args:
            tipo_servico: Service type (BIGQUERY, SHOPIFY, VTEX, etc.)
            credentials: Dictionary with decrypted credentials

        Returns:
            An instance of the appropriate connector
        """
        tipo = tipo_servico.upper()

        if tipo == "BIGQUERY":
            # BigQuery needs special client
            try:
                from google.cloud import bigquery
                from google.oauth2 import service_account
                from vizu_data_connectors.bigquery import BigQueryConnector

                # If credentials provided, create client with service account
                if credentials and "project_id" in credentials:
                    logger.info(f"Creating BigQuery client with service account for project: {credentials.get('project_id')}")
                    gcp_credentials = service_account.Credentials.from_service_account_info(credentials)
                    google_client = bigquery.Client(
                        credentials=gcp_credentials,
                        project=credentials.get("project_id")
                    )
                else:
                    # Fallback to default credentials from environment
                    logger.info("Creating BigQuery client with default credentials")
                    google_client = bigquery.Client()

                return BigQueryConnector(client=google_client)
            except ImportError as e:
                raise ValueError(
                    f"BigQuery connector requires 'google-cloud-bigquery' package. "
                    f"Install with: pip install vizu-data-connectors[bigquery]"
                ) from e

        elif tipo == "SHOPIFY":
            return ShopifyConnector(credentials)

        elif tipo == "VTEX":
            return VTEXConnector(credentials)

        elif tipo == "LOJA_INTEGRADA":
            return LojaIntegradaConnector(credentials)

        else:
            raise ValueError(f"Unsupported service type: {tipo_servico}")

    @classmethod
    def get_supported_resources(cls, tipo_servico: str) -> list:
        """
        Returns supported resources for each connector type.
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
