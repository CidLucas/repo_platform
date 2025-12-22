# Schema matching e discovery services
from data_ingestion_api.services.schema_discovery_service import SchemaDiscoveryService
from data_ingestion_api.services.schema_matcher_service import SchemaMatcherService
from data_ingestion_api.services.schema_registry_service import SchemaRegistryService

# Import the shared supabase client directly from the library
from vizu_supabase_client.client import get_supabase_client

__all__ = [
    "get_supabase_client",
    "SchemaMatcherService",
    "SchemaDiscoveryService",
    "SchemaRegistryService",
]
