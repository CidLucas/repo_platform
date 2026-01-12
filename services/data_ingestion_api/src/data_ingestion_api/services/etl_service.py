"""
ETL Service - Extract, Transform, Load data from BigQuery to Supabase analytics_silver.

This service:
1. Extracts data from BigQuery using stored credentials
2. Transforms data using schema mappings
3. Loads data to Supabase analytics_silver table with client_id for RLS isolation
"""

import logging
from typing import Any

import pandas as pd

from data_ingestion_api.services import supabase_client
from vizu_data_connectors.factory import ConnectorFactory

logger = logging.getLogger(__name__)


class ETLService:
    """Service for ETL operations from BigQuery to Supabase analytics_silver."""

    async def run_etl_job(
        self,
        credential_id: str,
        client_id: str,
        resource_type: str = "invoices",
        bigquery_table: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """
        Run complete ETL job: BigQuery → Transform → Supabase analytics_silver.

        Args:
            credential_id: ID of the BigQuery credential to use
            client_id: Client identifier for RLS isolation (goes into client_id column)
            resource_type: Type of data being ingested (e.g., "invoices", "products")
            bigquery_table: Full BigQuery table name (e.g., "project.dataset.table")
            limit: Optional limit on number of rows to process

        Returns:
            dict with job status and metrics
        """
        logger.info(f"Starting ETL job for client_id={client_id}, resource_type={resource_type}")

        try:
            # Step 1: Get BigQuery credentials and metadata
            logger.info(f"Retrieving BigQuery credentials for credential_id={credential_id}")
            credential = await supabase_client.select_one(
                "credencial_servico_externo",
                filters={"id": credential_id}
            )

            if not credential:
                raise ValueError(f"Credential not found: {credential_id}")

            # Parse credentials to get BigQuery project and dataset
            import json
            creds_json = credential.get("credenciais_cifradas")
            if not creds_json:
                raise ValueError(f"No credentials found for credential_id={credential_id}")

            creds = json.loads(creds_json) if isinstance(creds_json, str) else creds_json

            project_id = creds.get("project_id")
            dataset_id = creds.get("dataset_id")

            if not project_id:
                raise ValueError("Missing project_id in BigQuery credentials")

            if not dataset_id:
                raise ValueError(
                    "Missing dataset_id in BigQuery credentials. "
                    "Please specify which BigQuery dataset to use."
                )

            # Step 2: Build BigQuery table reference
            # The user configured which dataset to use when they created the connector
            # Now we need to specify which table within that dataset
            if not bigquery_table:
                # Default: use the resource_type as the table name within the configured dataset
                # For example: project.dataset_id.invoices
                bigquery_table = f"`{project_id}.{dataset_id}.{resource_type}`"
                logger.info(f"No table specified - using default: {bigquery_table}")
            else:
                logger.info(f"Using provided BigQuery table: {bigquery_table}")

            # Step 3: Create connector
            connector = await self._create_connector(credential_id)

            # Step 4: Build query
            # For BigQuery, we query all columns (no schema mapping required)
            query = f"SELECT * FROM {bigquery_table}"

            if limit:
                query += f" LIMIT {limit}"

            logger.info(f"Extracting from BigQuery: {query}")

            # Step 3: Extract, Transform, Load
            total_rows = 0
            total_inserted = 0

            async for chunk_df in connector.extract_data(query, chunk_size=1000):
                logger.info(f"Processing chunk of {len(chunk_df)} rows")

                # Add client_id column for RLS
                chunk_df["client_id"] = client_id

                # Add resource_type for categorization
                chunk_df["resource_type"] = resource_type

                # Load to Supabase analytics_silver
                rows_inserted = await self._load_to_supabase(chunk_df)

                total_rows += len(chunk_df)
                total_inserted += rows_inserted

                logger.info(
                    f"Chunk processed: {len(chunk_df)} rows extracted, "
                    f"{rows_inserted} rows inserted"
                )

            logger.info(
                f"ETL job completed: {total_rows} rows processed, "
                f"{total_inserted} rows inserted to analytics_silver"
            )

            return {
                "status": "success",
                "client_id": client_id,
                "resource_type": resource_type,
                "rows_processed": total_rows,
                "rows_inserted": total_inserted,
                "table": "analytics_silver",
            }

        except Exception as e:
            logger.error(f"ETL job failed: {e}", exc_info=True)
            return {
                "status": "error",
                "client_id": client_id,
                "resource_type": resource_type,
                "error": str(e),
            }

    async def _load_to_supabase(self, df: pd.DataFrame) -> int:
        """
        Load DataFrame to Supabase analytics_silver table.

        Args:
            df: DataFrame with transformed data (must include client_id column)

        Returns:
            Number of rows successfully inserted
        """
        rows_inserted = 0
        rows_failed = 0

        # Convert DataFrame to list of dicts
        records = df.to_dict(orient="records")

        logger.info(f"Inserting {len(records)} records to analytics_silver using batch insert")

        # Clean all records first
        clean_records = [self._clean_record(record) for record in records]

        # Batch insert configuration
        batch_size = 100  # Supabase handles up to 500 well, but 100 is safer
        total_batches = (len(clean_records) + batch_size - 1) // batch_size

        # Insert in batches
        for i in range(0, len(clean_records), batch_size):
            batch_num = (i // batch_size) + 1
            batch = clean_records[i : i + batch_size]

            try:
                logger.info(
                    f"Inserting batch {batch_num}/{total_batches} "
                    f"({len(batch)} records)..."
                )

                # Supabase client insert supports both single record and list
                await supabase_client.insert("analytics_silver", batch)
                rows_inserted += len(batch)

                logger.info(f"Batch {batch_num}/{total_batches} inserted successfully")

            except Exception as e:
                logger.error(
                    f"Failed to insert batch {batch_num}/{total_batches}: {e}",
                    exc_info=True,
                )
                rows_failed += len(batch)
                # Continue with next batch even if this one fails
                continue

        logger.info(
            f"Batch insert completed: {rows_inserted} inserted, "
            f"{rows_failed} failed out of {len(records)} total"
        )
        return rows_inserted

    async def _create_connector(self, credential_id: str):
        """
        Create data connector using credentials stored in Supabase.

        Uses ConnectorFactory to create the appropriate connector based on
        stored credentials.

        Args:
            credential_id: ID of the credential stored in Supabase

        Returns:
            Configured connector instance

        Raises:
            ValueError: If credentials not found or invalid
        """
        try:
            # Get credential metadata from Supabase
            credential = await supabase_client.select_one(
                "credencial_servico_externo",
                filters={"id": credential_id}
            )

            if not credential:
                raise ValueError(f"Credential not found: {credential_id}")

            # Get credentials JSON and service type
            creds_json = credential.get("credenciais_cifradas")
            tipo_servico = credential.get("tipo_servico", "BIGQUERY")

            if not creds_json:
                raise ValueError(f"No credentials found for credential {credential_id}")

            logger.info(f"Parsing credentials for {tipo_servico} connector")

            # Parse credentials from JSON (stored directly in Supabase, not Secret Manager)
            import json
            credentials_dict = json.loads(creds_json) if isinstance(creds_json, str) else creds_json

            if not credentials_dict:
                raise ValueError(f"Failed to parse credentials for {credential_id}")

            # Use ConnectorFactory to create the appropriate connector
            connector = await ConnectorFactory.create_connector(
                tipo_servico=tipo_servico,
                credentials=credentials_dict
            )

            logger.info(f"Successfully created {tipo_servico} connector")
            return connector

        except Exception as e:
            logger.error(f"Failed to create connector: {e}", exc_info=True)
            raise ValueError(f"Failed to create connector: {str(e)}")

    def _clean_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """
        Clean record for JSON serialization.

        Converts pandas types (NaT, NA, etc.) to None.
        """
        clean = {}
        for key, value in record.items():
            if pd.isna(value):
                clean[key] = None
            elif isinstance(value, pd.Timestamp):
                clean[key] = value.isoformat()
            else:
                clean[key] = value
        return clean


# Singleton instance
etl_service = ETLService()
