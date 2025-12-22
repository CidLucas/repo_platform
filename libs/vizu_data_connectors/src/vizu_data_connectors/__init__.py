"""
Vizu Data Connectors - Shared data connectors for Vizu data ingestion.

This package provides reusable data connectors for extracting data from various sources:
- BigQuery: Enterprise data warehouse connector
- E-commerce platforms: Shopify, VTEX, Loja Integrada
"""

from vizu_data_connectors.base.abstract_connector import (
    AbstractDataConnector,
    ExecutionError,
)
from vizu_data_connectors.base.ecommerce_base_connector import (
    AuthenticationError,
    EcommerceBaseConnector,
    EcommerceConnectorError,
    RateLimitError,
)

# E-commerce connectors
from vizu_data_connectors.ecommerce import (
    LojaIntegradaConnector,
    ShopifyConnector,
    VTEXConnector,
)

# BigQuery connector (optional dependency)
try:
    from vizu_data_connectors.bigquery import BigQueryConnector
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
    # E-commerce connectors
    "ShopifyConnector",
    "VTEXConnector",
    "LojaIntegradaConnector",
    # BigQuery connector (optional)
    "BigQueryConnector",
]
