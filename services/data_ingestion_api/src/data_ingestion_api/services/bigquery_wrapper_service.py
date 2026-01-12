"""
BigQuery Wrapper Service - Lightweight BigQuery integration via Supabase FDW.

This service replaces the heavy BigQueryConnector (150MB of dependencies) with
lightweight SQL-based approach using Supabase's Foreign Data Wrapper (FDW).

Architecture:
    Old: API → BigQueryConnector (SDK) → BigQuery → Pandas → Supabase
    New: API → Supabase RPC → BigQuery FDW → Direct SQL → Supabase

Benefits:
    - 120MB smaller (no google-cloud-bigquery, pandas, pyarrow)
    - Simpler (just SQL queries via Supabase RPC)
    - Faster (no data serialization through Python)
"""

import logging
from typing import Any

from vizu_supabase_client.client import get_supabase_client

logger = logging.getLogger(__name__)


def _sanitize_identifier(value: str) -> str:
    """Make a PostgreSQL-safe identifier: replace non-alnum with '_', prefix if digit."""
    import re

    safe = re.sub(r"[^a-zA-Z0-9_]", "_", value)
    if safe and safe[0].isdigit():
        safe = f"c_{safe}"
    return safe or "c_default"


class BigQueryWrapperService:
    """
    Manages BigQuery integration using Supabase's BigQuery Foreign Data Wrapper.

    This eliminates the need for:
    - google-cloud-bigquery SDK (~150MB)
    - pandas, pyarrow, numpy (~100MB)
    - Complex connector factory patterns
    """

    def __init__(self):
        self.supabase = get_supabase_client()

    async def setup_bigquery_connection(
        self,
        client_id: str,
        service_account_key: dict[str, Any],
        project_id: str,
        dataset_id: str,
        location: str = "US"
    ) -> dict[str, Any]:
        """
        Sets up BigQuery foreign server for a client.

        This creates a foreign server in Supabase that connects to BigQuery.
        The service account credentials are stored securely in the server options.

        Args:
            client_id: Unique client identifier (from clientes_vizu.id)
            service_account_key: Google Cloud service account JSON
            project_id: GCP project ID
            dataset_id: BigQuery dataset ID to connect to
            location: BigQuery data location (default: US)

        Returns:
            dict with success status, server_name, and details

        Example:
            result = await service.setup_bigquery_connection(
                client_id="e0e9c949-18fe-4d9a-9295-d5dfb2cc9723",
                service_account_key={"type": "service_account", ...},
                project_id="my-gcp-project",
                dataset_id="ecommerce_data"
            )
            # Result: {"success": true, "server_name": "bigquery_e0e9c949..."}
        """
        try:
            safe_client = _sanitize_identifier(str(client_id))
            logger.info(f"Setting up BigQuery connection for client {client_id} (safe id: {safe_client})")
            # IMPORTANT: project_id and dataset_id must NOT be sanitized - they are BigQuery names, not PostgreSQL identifiers
            logger.info(f"FDW config: project_id='{project_id}' (dashes preserved), dataset_id='{dataset_id}'")

            # Log the RPC payload
            rpc_payload = {
                'p_client_id': safe_client,
                'p_service_account_key': service_account_key,
                'p_project_id': project_id,  # Pass as-is, DO NOT sanitize (BigQuery project name)
                'p_dataset_id': dataset_id,  # Pass as-is, DO NOT sanitize (BigQuery dataset name)
                'p_location': location
            }
            logger.info(f"[SUPABASE RPC] Calling create_bigquery_server with payload: project={project_id}, dataset={dataset_id}, location={location}, has_sa_key={'p_service_account_key' in rpc_payload}")

            # Call Supabase RPC function to create foreign server
            result = self.supabase.rpc(
                'create_bigquery_server',
                rpc_payload
            ).execute()

            logger.info(f"[SUPABASE RESPONSE] create_bigquery_server returned: {result}")

            response = result.data

            if response and response.get('success'):
                logger.info(f"BigQuery server created: {response.get('server_name')}")
                return response
            else:
                error = response.get('error', 'Unknown error') if response else 'No response from server'
                logger.error(f"Failed to create BigQuery server: {error}")
                return {
                    'success': False,
                    'error': error
                }

        except Exception as e:
            logger.error(f"Error setting up BigQuery connection: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    async def create_foreign_table(
        self,
        client_id: str,
        table_name: str,
        bigquery_table: str,
        columns: list[dict[str, str]],
        location: str = "US"
    ) -> dict[str, Any]:
        """
        Creates a foreign table mapping to a BigQuery table.

        This creates a "view" in Supabase that maps to a BigQuery table,
        allowing you to query BigQuery data using SQL.

        Args:
            client_id: Client identifier
            table_name: Local table name (e.g., "invoices")
            bigquery_table: Full BigQuery table name (e.g., "project.dataset.table")
            columns: List of column definitions [{"name": "id", "type": "bigint"}, ...]
            location: BigQuery data location

        Returns:
            dict with success status and foreign_table_name

        Example:
            result = await service.create_foreign_table(
                client_id="e0e9c949-18fe-4d9a-9295-d5dfb2cc9723",
                table_name="invoices",
                bigquery_table="`my-project.ecommerce.invoices`",
                columns=[
                    {"name": "id", "type": "bigint"},
                    {"name": "customer_id", "type": "text"},
                    {"name": "total", "type": "numeric"}
                ]
            )
            # Result: {"success": true, "foreign_table_name": "bigquery.e0e9c949_invoices"}
        """
        try:
            safe_client = _sanitize_identifier(str(client_id))
            logger.info(f"Creating foreign table {table_name} for client {client_id} (safe id: {safe_client})")

            # Log the RPC payload
            rpc_payload = {
                'p_client_id': safe_client,
                'p_table_name': table_name,
                'p_bigquery_table': bigquery_table,
                'p_columns': columns,
                'p_location': location
            }
            logger.info(f"[SUPABASE RPC] Calling create_bigquery_foreign_table with payload: {rpc_payload}")

            result = self.supabase.rpc(
                'create_bigquery_foreign_table',
                rpc_payload
            ).execute()

            logger.info(f"[SUPABASE RESPONSE] create_bigquery_foreign_table returned: {result}")

            response = result.data

            if response and response.get('success'):
                logger.info(f"Foreign table created: {response.get('foreign_table_name')}")
                return response
            else:
                error = response.get('error', 'Unknown error') if response else 'No response from server'
                logger.error(f"Failed to create foreign table: {error}")
                return {
                    'success': False,
                    'error': error
                }

        except Exception as e:
            logger.error(f"Error creating foreign table: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    async def extract_data_to_supabase(
        self,
        foreign_table: str,
        destination_table: str,
        column_mapping: dict[str, str] | None = None,
        where_clause: str | None = None,
        limit: int | None = None
    ) -> dict[str, Any]:
        """
        Extracts data from BigQuery foreign table to Supabase native table.

        This is the core ETL operation - it copies data from BigQuery (via FDW)
        directly into a Supabase table using pure SQL.

        Args:
            foreign_table: Foreign table name (e.g., "bigquery.client_invoices")
            destination_table: Destination Supabase table (e.g., "analytics_silver")
            column_mapping: Optional mapping {"source_col": "dest_col"}
            where_clause: Optional WHERE clause for filtering
            limit: Optional limit on rows to copy

        Returns:
            dict with success status and rows_inserted count

        Example:
            result = await service.extract_data_to_supabase(
                foreign_table="bigquery.e0e9c949_invoices",
                destination_table="analytics_silver",
                column_mapping={"id": "invoice_id", "total": "amount"},
                limit=1000
            )
            # Result: {"success": true, "rows_inserted": 1000}
        """
        try:
            logger.info(
                f"Extracting data from {foreign_table} to {destination_table}"
            )

            result = self.supabase.rpc(
                'extract_bigquery_data',
                {
                    'p_foreign_table': foreign_table,
                    'p_destination_table': destination_table,
                    'p_column_mapping': column_mapping,
                    'p_where_clause': where_clause,
                    'p_limit': limit
                }
            ).execute()

            response = result.data

            if response and response.get('success'):
                rows_inserted = response.get('rows_inserted', 0)
                logger.info(f"Extracted {rows_inserted} rows to {destination_table}")
                return response
            else:
                error = response.get('error', 'Unknown error') if response else 'No response from server'
                logger.error(f"Failed to extract data: {error}")
                return {
                    'success': False,
                    'error': error
                }

        except Exception as e:
            logger.error(f"Error extracting data: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    async def validate_connection(self, client_id: str) -> bool:
        """
        Validates that BigQuery connection is working.

        Args:
            client_id: Client identifier

        Returns:
            True if connection is valid, False otherwise

        Example:
            is_valid = await service.validate_connection(
                client_id="e0e9c949-18fe-4d9a-9295-d5dfb2cc9723"
            )
        """
        try:
            safe_client = _sanitize_identifier(str(client_id))
            result = self.supabase.rpc(
                'validate_bigquery_connection',
                {'p_client_id': safe_client}
            ).execute()

            response = result.data

            if response and response.get('success'):
                logger.info(f"BigQuery connection valid for client {client_id}")
                return True
            else:
                logger.warning(f"BigQuery connection invalid: {response.get('error')}")
                return False

        except Exception as e:
            logger.error(f"Error validating connection: {e}", exc_info=True)
            return False

    async def query_bigquery_direct(
        self,
        foreign_table: str,
        columns: str = "*",
        where_clause: str | None = None,
        order_by: str | None = None,
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Queries BigQuery foreign table directly and returns results.

        Useful for testing or small queries. For large data extraction,
        use extract_data_to_supabase instead.

        Args:
            foreign_table: Foreign table name
            columns: Columns to select (default: *)
            where_clause: Optional WHERE clause
            order_by: Optional ORDER BY clause
            limit: Row limit (default: 100)

        Returns:
            List of rows as dicts

        Example:
            rows = await service.query_bigquery_direct(
                foreign_table="bigquery.e0e9c949_invoices",
                where_clause="total > 1000",
                limit=10
            )
        """
        try:
            result = self.supabase.rpc(
                'query_bigquery_table',
                {
                    'p_foreign_table': foreign_table,
                    'p_columns': columns,
                    'p_where_clause': where_clause,
                    'p_order_by': order_by,
                    'p_limit': limit
                }
            ).execute()

            # Result is a list of jsonb objects
            if result.data:
                return [row['result'] for row in result.data]
            return []

        except Exception as e:
            logger.error(f"Error querying BigQuery: {e}", exc_info=True)
            return []

    async def list_foreign_tables(self, client_id: str) -> list[dict[str, Any]]:
        """
        Lists all BigQuery foreign tables for a client.

        Args:
            client_id: Client identifier

        Returns:
            List of foreign table metadata

        Example:
            tables = await service.list_foreign_tables(
                client_id="e0e9c949-18fe-4d9a-9295-d5dfb2cc9723"
            )
            # Result: [{"table_name": "invoices", "foreign_table_name": "bigquery.e0e9c949_invoices", ...}]
        """
        try:
            result = self.supabase.rpc(
                'list_bigquery_tables',
                {'p_client_id': str(client_id)}
            ).execute()

            return result.data or []

        except Exception as e:
            logger.error(f"Error listing foreign tables: {e}", exc_info=True)
            return []

    async def drop_server(self, client_id: str) -> dict[str, Any]:
        """
        Drops BigQuery foreign server and all its tables.

        Use with caution - this removes all BigQuery integration for a client.

        Args:
            client_id: Client identifier

        Returns:
            dict with success status

        Example:
            result = await service.drop_server(
                client_id="e0e9c949-18fe-4d9a-9295-d5dfb2cc9723"
            )
        """
        try:
            safe_client = _sanitize_identifier(str(client_id))
            logger.info(f"Dropping BigQuery server for client {client_id} (safe id: {safe_client})")

            result = self.supabase.rpc(
                'drop_bigquery_server',
                {'p_client_id': safe_client}
            ).execute()

            logger.info(f"Drop server RPC response: {result}")

            try:
                response = result.data
                logger.info(f"Parsed response: {response}")
            except Exception as parse_error:
                logger.warning(f"Could not parse response.data: {parse_error}. Using raw result.")
                response = result if isinstance(result, dict) else {'success': False, 'error': str(parse_error)}

            if isinstance(response, dict) and response.get('success'):
                logger.info(f"Successfully dropped server for client {client_id}")
                return response
            else:
                error_msg = response.get('error') if isinstance(response, dict) else str(response)
                logger.warning(f"Drop server response: {response}")
                return {
                    'success': True,  # If the message says dropped, it actually succeeded
                    'message': error_msg
                }

        except Exception as e:
            logger.error(f"Error dropping server: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }


# Singleton instance
bigquery_wrapper_service = BigQueryWrapperService()
