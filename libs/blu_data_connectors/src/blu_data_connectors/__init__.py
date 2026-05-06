"""
Blu Data Connectors - Shared data connectors for Blu data ingestion.

This package provides reusable data connectors for extracting data from various sources:
- BigQuery: Enterprise data warehouse connector
- E-commerce platforms: Shopify, VTEX, Loja Integrada
"""

from blu_data_connectors.base.abstract_connector import (
    AbstractDataConnector,
    ExecutionError,
)
from blu_data_connectors.base.ecommerce_base_connector import (
    AuthenticationError,
    EcommerceBaseConnector,
    EcommerceConnectorError,
    RateLimitError,
)

# Accounting connectors
from blu_data_connectors.accounting import ContaAzulConnector

# E-commerce connectors
from blu_data_connectors.ecommerce import (
    LojaIntegradaConnector,
    ShopifyConnector,
    VTEXConnector,
)

# BigQuery connector (optional dependency)
try:
    from blu_data_connectors.bigquery import BigQueryConnector
except ImportError:
    BigQueryConnector = None  # type: ignore

__all__ = [
    # Base classes
    "AbstractDataConnector",
    "ExecutionError",
    "EcommerceBaseConnector",
    "EcommerceConnectorError",
    "AuthenticationError",
    "RateLimitError",
    # Accounting connectors
    "ContaAzulConnector",
    # E-commerce connectors
    "ShopifyConnector",
    "VTEXConnector",
    "LojaIntegradaConnector",
    # BigQuery connector (optional)
    "BigQueryConnector",
]
