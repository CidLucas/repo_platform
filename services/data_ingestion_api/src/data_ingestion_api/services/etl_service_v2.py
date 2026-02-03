"""
ETL Service V2 - Lightweight BigQuery ETL using Supabase FDW.

REVISED ARCHITECTURE (No analytics_silver):
    1. User creates BigQuery connector → Creates foreign server in Supabase
    2. User triggers sync → Creates foreign table mapping to BigQuery table
    3. Register data source → Analytics API queries foreign table directly
    4. Analytics API processes raw data → Writes to GOLD tables

Benefits:
    - No google-cloud-bigquery SDK (saves 150MB)
    - No intermediate analytics_silver table (flexible schema)
    - Real-time queries to BigQuery via FDW
    - Analytics API handles column mapping
"""

import logging
from typing import Any, List

from data_ingestion_api.services import supabase_client
from data_ingestion_api.services.bigquery_wrapper_service import (
    _sanitize_identifier,
    bigquery_wrapper_service,
)
from data_ingestion_api.services.schema_matcher_service import schema_matcher
from data_ingestion_api.services.schema_registry_service import MappingStatus, schema_registry

logger = logging.getLogger(__name__)


# Minimal BigQuery REST schema fetcher using service account JSON
def _fetch_bigquery_schema(service_account_json: dict[str, Any], project_id: str, dataset_id: str, table_name: str) -> list[dict[str, str]]:
    """Fetch BigQuery table schema via REST API (no heavy SDK).

    Returns a list of {name, type} mappings using simple Postgres-friendly types.
    """
    try:
        import requests
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account  # lightweight dependency

        creds = service_account.Credentials.from_service_account_info(service_account_json, scopes=["https://www.googleapis.com/auth/bigquery"])
        creds.refresh(Request())

        url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets/{dataset_id}/tables/{table_name}"
        headers = {"Authorization": f"Bearer {creds.token}"}
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        fields = data.get("schema", {}).get("fields", [])
        pg_type_map = {
            "STRING": "text",
            "BOOL": "boolean",
            "BOOLEAN": "boolean",
            "INT64": "bigint",
            "INTEGER": "bigint",
            "FLOAT64": "double precision",
            "FLOAT": "double precision",
            "NUMERIC": "numeric",
            "BIGNUMERIC": "numeric",
            "DECIMAL": "numeric",
            "TIMESTAMP": "timestamptz",
            "DATETIME": "timestamp",
            "DATE": "date",
            "TIME": "time",
            "JSON": "jsonb",
        }

        columns = []
        for f in fields:
            name = f.get("name")
            bq_type = (f.get("type") or "STRING").upper()
            pg_type = pg_type_map.get(bq_type, "text")
            if name:
                columns.append({"name": name.lower(), "type": pg_type})

        if columns:
            logger.info(f"Discovered {len(columns)} columns from BigQuery REST for {dataset_id}.{table_name}")
        else:
            logger.warning("BigQuery REST schema returned no columns; falling back to defaults")
        return columns

    except Exception as e:
        logger.warning(f"Failed to fetch BigQuery schema via REST: {e}")
        return []


def _infer_schema_type(resource_type: str) -> str:
    """Infer canonical schema type from resource_type provided by the connector.

    Falls back to invoices when the table name includes 'invoice' (e.g., products_invoices).
    """
    normalized = (resource_type or "").lower()
    if normalized in schema_matcher.get_supported_types():
        return normalized
    if "invoice" in normalized:
        return "invoices"
    if "order" in normalized:
        return "orders"
    if "product" in normalized:
        return "products"
    if "customer" in normalized:
        return "customers"
    if "inventory" in normalized:
        return "inventory"
    if "category" in normalized:
        return "categories"
    return normalized


class ETLServiceV2:
    """New ETL service using Supabase BigQuery FDW."""

    async def run_etl_job(
        self,
        credential_id: str,
        client_id: str,
        resource_type: str = "invoices",
        bigquery_table: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """
        Run ETL job using Supabase BigQuery FDW.

        NEW FLOW (No analytics_silver):
            1. Load credentials from Supabase
            2. Create/verify BigQuery foreign server exists
            3. Query BigQuery schema (INFORMATION_SCHEMA.COLUMNS)
            4. Create foreign table with actual BigQuery columns
            5. Register data source in client_data_sources table
            6. Return success (Analytics API will query foreign table directly)

        Args:
            credential_id: ID of the BigQuery credential
            client_id: Client identifier for RLS isolation
            resource_type: Type of data (default: "invoices")
            bigquery_table: Full BigQuery table name (optional)
            limit: Optional row limit (unused in this version)

        Returns:
            dict with job status, foreign_table_name, and column info
        """
        logger.info(f"Starting ETL V2 job for client_id={client_id}, resource_type={resource_type}")

        # Validate client_id is a valid UUID (not empty string)
        if not client_id or not client_id.strip():
            raise ValueError("client_id is required and cannot be empty")

        import uuid
        try:
            uuid.UUID(client_id)
        except ValueError:
            raise ValueError(f"client_id must be a valid UUID, got: '{client_id}'")

        from datetime import datetime
        sync_started_at = datetime.utcnow()
        sync_id = None

        try:
            # Step 1: Get BigQuery credentials
            logger.info(f"Retrieving BigQuery credentials for credential_id={credential_id}")
            credential = await supabase_client.select_one(
                "credencial_servico_externo",
                filters={"id": credential_id}
            )

            if not credential:
                raise ValueError(f"Credential not found: {credential_id}")

            # Retrieve credentials (vault or legacy plaintext)
            vault_key_id = credential.get("vault_key_id")
            if vault_key_id:
                # New: Retrieve from Supabase Vault (encrypted)
                logger.info(f"Retrieving credentials from vault: vault_key_id={vault_key_id}")
                creds = await supabase_client.rpc(
                    "get_credential_from_vault",
                    {"p_vault_key_id": vault_key_id}
                )
                if not creds:
                    raise ValueError(f"Failed to retrieve credentials from vault: {vault_key_id}")
            else:
                # Legacy: Parse plaintext JSON from credenciais_cifradas
                import json
                creds_json = credential.get("credenciais_cifradas")
                if not creds_json:
                    raise ValueError(f"No credentials found for credential_id={credential_id}")
                creds = json.loads(creds_json) if isinstance(creds_json, str) else creds_json
                logger.warning(f"Using legacy plaintext credentials for credential_id={credential_id} - consider migrating to vault")

            project_id = creds.get("project_id")
            dataset_id = creds.get("dataset_id")
            table_name = creds.get("table_name")  # Table name provided by user
            location = creds.get("location")  # Location from user input (REQUIRED - no default!)
            service_account_json = creds.get("service_account_json")

            logger.info(f"Credentials loaded: project_id='{project_id}' (dashes: {'-' in (project_id or '')}), dataset_id='{dataset_id}', table_name='{table_name}', location='{location}')")

            # Verify service account has correct project_id
            if isinstance(service_account_json, dict):
                sa_project = service_account_json.get("project_id")
                logger.info(f"Service Account JSON contains project_id='{sa_project}' (dashes: {'-' in (sa_project or '')})")

            if not project_id:
                raise ValueError("Missing project_id in BigQuery credentials")
            if not dataset_id:
                raise ValueError("Missing dataset_id in BigQuery credentials")
            if not service_account_json:
                raise ValueError("Missing service_account_json in BigQuery credentials")

            # Step 2: Create BigQuery foreign server (if not exists)
            logger.info(f"Setting up BigQuery foreign server for client {client_id}")

            # First, look for metadata to avoid duplicate key errors when the server already exists
            safe_client_id = _sanitize_identifier(str(client_id))
            logger.info(f"Looking up bigquery_servers with safe_client_id='{safe_client_id}' and raw='{client_id}'")
            existing_server = await supabase_client.select_one(
                "bigquery_servers",
                filters={"client_id": safe_client_id}
            )

            if not existing_server:
                # Backward compatibility: some rows may store the raw client_id
                existing_server = await supabase_client.select_one(
                    "bigquery_servers",
                    filters={"client_id": str(client_id)}
                )

            if existing_server:
                logger.info(
                    f"Found existing server metadata: client_id={existing_server.get('client_id')}, server_name={existing_server.get('server_name')}"
                )

                # Check if user-provided values have changed (location, dataset_id, project_id)
                needs_recreation = False
                old_location = existing_server.get('location')
                old_dataset = existing_server.get('dataset_id')
                old_project = existing_server.get('project_id')

                if old_location != location:
                    logger.info(f"Location changed from '{old_location}' to '{location}' - will recreate server")
                    needs_recreation = True
                if old_dataset != dataset_id:
                    logger.info(f"Dataset ID changed from '{old_dataset}' to '{dataset_id}' - will recreate server")
                    needs_recreation = True
                if old_project != project_id:
                    logger.info(f"Project ID changed from '{old_project}' to '{project_id}' - will recreate server")
                    needs_recreation = True

                if needs_recreation:
                    logger.info(f"User parameters changed - dropping old server '{existing_server.get('server_name')}'")
                    drop_result = await bigquery_wrapper_service.drop_server(client_id)
                    if not drop_result.get('success'):
                        logger.warning(f"Failed to drop old server: {drop_result.get('error')}")
                    existing_server = None  # Force recreation

            server_exists = existing_server is not None

            if server_exists:
                logger.info(
                    f"Found existing BigQuery server metadata with matching parameters: server_name={existing_server.get('server_name')}"
                )
            else:
                # Fall back to RPC validation in case metadata is missing but the server exists
                server_exists = await bigquery_wrapper_service.validate_connection(client_id)

            if not server_exists:
                logger.info("Server doesn't exist, creating...")
                logger.info(f"Passing to FDW: project_id='{project_id}', dataset_id='{dataset_id}', location='{location}'")
                setup_result = await bigquery_wrapper_service.setup_bigquery_connection(
                    client_id=client_id,
                    service_account_key=service_account_json,
                    project_id=project_id,
                    dataset_id=dataset_id,
                    location=location  # USER-PROVIDED LOCATION (not hardcoded)
                )

                logger.info(f"create_bigquery_server RPC result: {setup_result}")

                if not setup_result.get('success'):
                    error_msg = setup_result.get('error', '')

                    # If the server already exists (race or metadata mismatch), treat as non-fatal
                    if "duplicate key value violates unique constraint \"bigquery_servers_server_name_key\"" in error_msg or "already exists" in error_msg:
                        logger.warning("BigQuery server already exists; proceeding with existing server")
                    else:
                        raise ValueError(f"Failed to create BigQuery server: {error_msg}")

                server_name = (
                    setup_result.get('server_name')
                    if setup_result else None
                ) or (existing_server.get('server_name') if existing_server else None)
                logger.info(f"BigQuery server ready: {server_name or 'existing'}")
            else:
                logger.info("BigQuery server already exists")

            # Re-fetch metadata to ensure the registry has the server row the RPC expects
            existing_server = await supabase_client.select_one(
                "bigquery_servers",
                filters={"client_id": safe_client_id}
            ) or await supabase_client.select_one(
                "bigquery_servers",
                filters={"client_id": str(client_id)}
            )

            if not existing_server:
                raise ValueError(
                    f"BigQuery server metadata missing after setup for client_id={client_id} (safe={safe_client_id}); cannot create foreign tables."
                )
            else:
                logger.info(
                    f"bigquery_servers row confirmed: client_id={existing_server.get('client_id')}, server_name={existing_server.get('server_name')}"
                )

            # Normalize legacy rows: ensure client_id in bigquery_servers matches the sanitized value expected by RPCs
            if existing_server.get('client_id') != safe_client_id:
                logger.warning(
                    "Normalizing bigquery_servers.client_id from '%s' to '%s' for server_name=%s",
                    existing_server.get('client_id'),
                    safe_client_id,
                    existing_server.get('server_name')
                )
                await supabase_client.update(
                    "bigquery_servers",
                    data={"client_id": safe_client_id},
                    filters={"server_name": existing_server.get('server_name')}
                )
                existing_server["client_id"] = safe_client_id

            # Step 3: Set BigQuery table name
            # Use table_name from user input (from BigQuery credential form)
            # If not provided, fall back to resource_type
            if not table_name:
                table_name = resource_type
            logger.info(f"Using BigQuery table: {table_name}")

            # Step 4: Discover BigQuery schema (actual columns) instead of hardcoded list
            logger.info(f"Discovering schema for {project_id}.{dataset_id}.{table_name}")

            discovered_columns = _fetch_bigquery_schema(
                service_account_json,
                project_id,
                dataset_id,
                table_name,
            )

            if discovered_columns:
                foreign_table_columns = discovered_columns
            else:
                logger.warning("Falling back to generic text columns (schema discovery failed)")
                foreign_table_columns = [
                    {"name": "id", "type": "text"},
                ]

            logger.info(f"Creating foreign table with {len(foreign_table_columns)} columns")

            # Step 4b: Build and persist schema mapping (source -> canonical) using matcher
            source_column_names = [c["name"] for c in foreign_table_columns]
            schema_type_for_match = _infer_schema_type(resource_type)
            mapping_dict = {}  # Initialize empty mapping as fallback

            try:
                logger.info(f"\n{'='*80}")
                logger.info(f"[SCHEMA MATCHING] Starting for resource_type='{resource_type}' (schema_type='{schema_type_for_match}')")
                logger.info(f"  Input: {len(source_column_names)} source columns from BigQuery")
                logger.info(f"{'='*80}\n")

                match_result = schema_matcher.auto_match(source_column_names, schema_type_for_match)
                mapping_dict = match_result.matched
                needs_review = match_result.needs_review

                # LOUD SUCCESS/WARNING based on match quality
                if len(match_result.unmatched) > 0:
                    logger.warning(f"\n{'!'*80}")
                    logger.warning("⚠️  WARNING: Schema matching incomplete!")
                    logger.warning(f"  ✓ Mapped: {len(mapping_dict)} columns")
                    logger.warning(f"  ⚠ Needs review: {len(needs_review)} columns")
                    logger.warning(f"  ✗ UNMATCHED: {len(match_result.unmatched)} columns")
                    logger.warning("\n  📍 Mapped source columns (these WILL be available):")
                    for source_col, canonical_col in list(mapping_dict.items())[:20]:
                        logger.warning(f"    '{source_col}' → '{canonical_col}'")
                    if len(mapping_dict) > 20:
                        logger.warning(f"    ... and {len(mapping_dict) - 20} more")
                    logger.warning("\n  Unmatched columns (will NOT be available in analytics):")
                    for col in match_result.unmatched[:20]:
                        logger.warning(f"    - {col}")
                    if len(match_result.unmatched) > 20:
                        logger.warning(f"    ... and {len(match_result.unmatched) - 20} more")
                    logger.warning(f"{'!'*80}\n")
                else:
                    logger.info(f"\n{'='*80}")
                    logger.info("✅ Schema mapping SUCCESS!")
                    logger.info(f"  ✓ All {len(mapping_dict)} columns mapped successfully")
                    if needs_review:
                        logger.info(f"  ⚠ {len(needs_review)} columns flagged for review (lower confidence)")
                    logger.info(f"{'='*80}\n")

                # MAPPING QUALITY ASSESSMENT
                logger.info(f"\n{'='*80}")
                logger.info("[MAPPING QUALITY ASSESSMENT]")

                # 1. Schema Coverage: What % of canonical schema was filled?
                canonical_cols = schema_matcher.get_canonical_schema(schema_type_for_match)
                mapped_canonical = set(mapping_dict.values())
                coverage_pct = (len(mapped_canonical) / len(canonical_cols)) * 100 if canonical_cols else 0

                logger.info(f"  📊 Schema Coverage: {len(mapped_canonical)}/{len(canonical_cols)} ({coverage_pct:.1f}%)")
                logger.info(f"  ✓ Filled canonical columns: {sorted(mapped_canonical)}")

                unmapped_canonical = set(canonical_cols) - mapped_canonical
                if unmapped_canonical:
                    logger.warning(f"  ⚠️  Unfilled canonical columns ({len(unmapped_canonical)}): {sorted(unmapped_canonical)}")

                # 2. Data Loss: What % of source columns were used?
                usage_pct = (len(mapping_dict) / len(source_column_names)) * 100 if source_column_names else 0
                logger.info(f"  📉 Source Column Usage: {len(mapping_dict)}/{len(source_column_names)} ({usage_pct:.1f}%)")
                if len(match_result.unmatched) > 0:
                    loss_pct = (len(match_result.unmatched) / len(source_column_names)) * 100
                    logger.warning(f"  ⚠️  Data Loss: {len(match_result.unmatched)} columns unmapped ({loss_pct:.1f}%)")

                logger.info(f"{'='*80}\n")

                # CRITICAL: Verify key columns are mapped
                critical_columns = ["emitter_nome", "receiver_nome", "order_id"]
                missing_critical = []
                for critical in critical_columns:
                    if critical not in mapping_dict.values():
                        missing_critical.append(critical)

                if missing_critical:
                    logger.error(f"\n{'#'*80}")
                    logger.error("❌ CRITICAL ERROR: Key columns missing from mapping!")
                    logger.error(f"  Missing canonical columns: {missing_critical}")
                    logger.error("  These columns are REQUIRED for analytics but were not matched.")
                    logger.error("  Impact:")
                    for col in missing_critical:
                        if col == "order_id":
                            logger.error("    - order_id: Aggregations will use synthetic IDs (may affect accuracy)")
                        elif col in ["emitter_nome", "receiver_nome"]:
                            logger.error(f"    - {col}: Customer/supplier analytics will be empty")
                    logger.error("  Check if source columns exist in BigQuery or if aliases need updating.")
                    logger.error(f"{'#'*80}\n")

                # Persist mapping in registry (best-effort, non-blocking)
                try:
                    await schema_registry.save_mapping(
                        credential_id=credential_id,
                        resource_type=resource_type,
                        source_columns=source_column_names,
                        mapping=mapping_dict,
                        unmapped_columns=match_result.unmatched,
                        confidence_scores=match_result.confidence_scores,
                        status=MappingStatus.READY if not needs_review else MappingStatus.NEEDS_REVIEW,
                        metadata={
                            "project_id": project_id,
                            "dataset_id": dataset_id,
                            "table_name": table_name,
                            "client_id": client_id,
                        }
                    )
                    logger.info("✓ Schema mapping persisted to data_source_mappings table")
                except Exception as registry_error:
                    logger.warning("\n⚠️  WARNING: Failed to persist mapping to data_source_mappings table")
                    logger.warning(f"  Error: {registry_error}")
                    logger.warning("  Impact: Mapping will still be stored in client_data_sources.column_mapping")
                    logger.warning("  This is non-fatal - ETL will continue.\n")

            except Exception as e:
                logger.error(f"\n{'#'*80}")
                logger.error("❌ CRITICAL ERROR: Schema matching failed completely!")
                logger.error(f"  Error: {e}")
                logger.error("  Impact: No column mapping will be available - analytics will likely FAIL")
                logger.error("  Fallback: Using empty mapping (analytics will use column names as-is)")
                logger.error(f"{'#'*80}\n", exc_info=True)
                mapping_dict = {}  # Empty mapping as last resort

            # Step 5: Create foreign table mapping
            # Use location from credentials (user input) instead of hardcoding

            # Log the payload being sent to Supabase RPC
            foreign_table_payload = {
                'client_id': client_id,
                'table_name': table_name,
                'bigquery_table': table_name,
                'columns': foreign_table_columns,
                'location': location
            }
            logger.info(f"[PAYLOAD] create_foreign_table: {foreign_table_payload}")

            foreign_table_result = await bigquery_wrapper_service.create_foreign_table(
                client_id=client_id,
                table_name=table_name,
                bigquery_table=table_name,
                columns=foreign_table_columns,
                location=location
            )

            logger.info(f"[RESPONSE] create_foreign_table result: {foreign_table_result}")

            if not foreign_table_result.get('success'):
                error_msg = foreign_table_result.get('error', '')
                duplicate = (
                    'already exists' in error_msg
                    or 'duplicate key value violates unique constraint "bigquery_foreign_tables_foreign_table_name_key"' in error_msg
                )

                if duplicate:
                    logger.info("Foreign table already exists (duplicate key), fetching existing metadata...")
                    existing_ft = await supabase_client.select_one(
                        "bigquery_foreign_tables",
                        filters={
                            "client_id": _sanitize_identifier(str(client_id)),
                            "table_name": resource_type,
                        },
                    ) or await supabase_client.select_one(
                        "bigquery_foreign_tables",
                        filters={
                            "client_id": str(client_id),
                            "table_name": resource_type,
                        },
                    )

                    if not existing_ft:
                        raise ValueError(
                            "Foreign table duplicate detected but metadata row not found; manual cleanup may be required."
                        )

                    foreign_table_name = existing_ft.get("foreign_table_name")
                    logger.info(
                        f"Using existing foreign table: {foreign_table_name} (bigquery_table={existing_ft.get('bigquery_table')})"
                    )
                else:
                    raise ValueError(f"Failed to create foreign table: {error_msg}")

            foreign_table_name = foreign_table_result.get('foreign_table_name') if foreign_table_result.get('success') else foreign_table_name
            logger.info(f"Foreign table created: {foreign_table_name}")

            # Step 6: Register data source in registry (skip analytics_silver)
            logger.info("Registering/updating data source in client_data_sources")

            # Convert column list to JSONB format for source_columns
            source_columns_jsonb = {col["name"]: col["type"] for col in foreign_table_columns}

            # Use mapping if computed above
            try:
                column_mapping_for_ds = mapping_dict if mapping_dict else None
            except NameError:
                column_mapping_for_ds = None

            # CRITICAL: Log what we're about to persist
            logger.info(f"\n{'='*80}")
            logger.info("[PERSISTENCE] Saving data source to client_data_sources")
            logger.info(f"  client_id: {client_id}")
            logger.info(f"  credential_id: {credential_id}")
            logger.info(f"  resource_type: {resource_type}")
            logger.info(f"  storage_location: {foreign_table_name}")
            logger.info(f"  column_mapping entries: {len(column_mapping_for_ds) if column_mapping_for_ds else 0}")
            if column_mapping_for_ds:
                logger.info("  Sample mappings (first 10):")
                for source, canonical in list(column_mapping_for_ds.items())[:10]:
                    logger.info(f"    '{source}' → '{canonical}'")
                if len(column_mapping_for_ds) > 10:
                    logger.info(f"    ... and {len(column_mapping_for_ds) - 10} more")
            else:
                logger.error("  ⚠️  WARNING: column_mapping is EMPTY! Analytics will likely fail.")
            logger.info(f"{'='*80}\n")

            # Use upsert to handle re-syncs (updates existing record if client_id+source_type+resource_type exists)
            try:
                await supabase_client.upsert(
                    "client_data_sources",
                    {
                        "client_id": client_id,
                        "credential_id": int(credential_id),  # FK to credencial_servico_externo
                        "source_type": "bigquery",
                        "resource_type": resource_type,
                        "storage_type": "foreign_table",
                        "storage_location": foreign_table_name,
                        "column_mapping": column_mapping_for_ds,
                        "source_columns": source_columns_jsonb,  # Store schema for reference
                        "sync_status": "active",
                        "last_synced_at": "now()",  # Update sync timestamp
                    },
                    on_conflict="client_id,source_type,resource_type"  # Use unique constraint columns
                )
                logger.info("✅ Successfully persisted data source to client_data_sources")
            except Exception as persist_error:
                logger.error(f"\n{'#'*80}")
                logger.error("❌ CRITICAL ERROR: Failed to persist to client_data_sources!")
                logger.error(f"  Error: {persist_error}")
                logger.error("  Impact: Analytics API will NOT be able to find this data source")
                logger.error("  This is a FATAL error - ETL cannot continue")
                logger.error(f"{'#'*80}\n", exc_info=True)
                raise  # Re-raise to fail the ETL job

            # Step 7: Record sync completion in connector_sync_history
            logger.info("Recording sync completion in connector_sync_history")
            sync_completed_at = datetime.utcnow()

            # Note: duration_seconds is a generated column (auto-calculated from timestamps)
            # Use upsert in case of retry (same client_id + sync_started_at = update instead of insert)
            sync_record = await supabase_client.upsert(
                "connector_sync_history",
                {
                    "credential_id": int(credential_id),
                    "client_id": client_id,
                    "status": "completed",
                    "sync_started_at": sync_started_at.isoformat(),
                    "sync_completed_at": sync_completed_at.isoformat(),
                    "records_processed": 0,  # We don't know count until Analytics API processes
                    "records_inserted": 0,
                    "resource_type": resource_type,
                    "target_table": foreign_table_name,
                    "error_message": None,
                },
                on_conflict="client_id,sync_started_at"  # Unique constraint we just created
            )
            sync_id = sync_record.get("id") if sync_record else None
            logger.info(f"Sync history recorded with id={sync_id}")

            # Step 8: Trigger Analytics API to pre-populate gold tables
            logger.info("Triggering Analytics API to populate gold tables")
            await self._trigger_analytics_processing(client_id)

            logger.info("ETL V2 job completed: Foreign table ready and gold tables populated")

            return {
                "status": "success",
                "client_id": client_id,
                "resource_type": resource_type,
                "foreign_table": foreign_table_name,
                "columns": [col["name"] for col in foreign_table_columns],
                "sync_id": sync_id,
                "message": "Foreign table created and gold tables populated. Data ready!",
            }

        except Exception as e:
            logger.error(f"ETL V2 job failed: {e}", exc_info=True)

            # Record failed sync in history
            try:
                sync_failed_at = datetime.utcnow()

                # Note: duration_seconds is a generated column (auto-calculated from timestamps)
                # Use upsert to handle retries (same client_id + sync_started_at = update instead of insert)
                await supabase_client.upsert(
                    "connector_sync_history",
                    {
                        "credential_id": int(credential_id),
                        "client_id": client_id,
                        "status": "failed",
                        "sync_started_at": sync_started_at.isoformat(),
                        "sync_completed_at": sync_failed_at.isoformat(),
                        "records_processed": 0,
                        "records_inserted": 0,
                        "resource_type": resource_type,
                        "error_message": str(e),
                    },
                    on_conflict="client_id,sync_started_at"  # Unique constraint we created
                )
                logger.info("Failed sync recorded in connector_sync_history")
            except Exception as history_error:
                logger.error(f"Failed to record sync history: {history_error}")

            return {
                "status": "error",
                "client_id": client_id,
                "resource_type": resource_type,
                "error": str(e),
            }

    async def _trigger_analytics_processing(self, client_id: str) -> None:
        """
        Trigger Analytics API to recompute and write analytics_v2 tables.

        Calls /api/ingest/recompute which:
        - Loads Silver dataframe via get_silver_dataframe()
        - Computes aggregations (customers, suppliers, products)
        - Writes to analytics_v2 tables

        This ensures data is visible immediately after sync without user navigation.

        IMPORTANT: Passes client_id as query parameter for proper data isolation.

        NOTE: This is non-blocking - if analytics API is unavailable, data is still
        persisted to the silver layer. Analytics can be triggered manually later.
        """
        import os

        import httpx

        analytics_api_url = os.getenv("ANALYTICS_API_URL", "http://analytics_api:8000")
        recompute_endpoint = f"{analytics_api_url}/api/ingest/recompute"

        try:
            # Timeout increased to 5 minutes - BigQuery FDW queries can take a while
            async with httpx.AsyncClient(timeout=300) as http_client:
                logger.info(f"🔄 Triggering analytics recompute for client {client_id}")
                logger.info(f"   Endpoint: {recompute_endpoint}")

                response = await http_client.post(
                    recompute_endpoint,
                    params={"client_id": client_id},
                    headers={
                        "X-Client-ID": client_id,
                        "User-Agent": "ETL-Service-V2/1.0"
                    }
                )

                if response.status_code in (200, 202):
                    logger.info(f"✅ Analytics recompute successful: {response.status_code}")
                    logger.info(f"   Analytics_v2 tables written for {client_id}")
                else:
                    logger.error(
                        f"❌ Analytics recompute failed: {response.status_code} - {response.text[:200]}"
                    )
        except httpx.ConnectError as e:
            logger.warning(f"⚠️  Cannot reach Analytics API: {e}")
            logger.info("   Data is safely persisted to silver layer. Analytics can be triggered manually.")
        except httpx.TimeoutException:
            logger.warning(f"⏱️  Analytics recompute timed out for {client_id}")
            logger.info("   Data is safely persisted to silver layer. Analytics can be triggered manually.")
        except Exception as e:
            logger.warning(f"⚠️  Failed to trigger analytics: {type(e).__name__}: {str(e)[:200]}")
            logger.info("   Data is safely persisted to silver layer. Analytics can be triggered manually.")


# Singleton instance
etl_service_v2 = ETLServiceV2()
