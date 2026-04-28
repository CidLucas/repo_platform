"""Base classes for data connectors."""

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

__all__ = [
    "AbstractDataConnector",
    "ExecutionError",
    "EcommerceBaseConnector",
    "EcommerceConnectorError",
    "AuthenticationError",
    "RateLimitError",
]
