# src/analytics_api/core/analytics_mapping.py
import logging
import os
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

# FALLBACK SILVER TABLE (if no foreign table found)
# Used when client hasn't synced data yet
FALLBACK_SILVER_TABLE = "analytics_silver"

def get_silver_table_name(client_id: str) -> str:
    """
    Returns the silver table name for the client.

    NEW ARCHITECTURE (FDW):
    - Queries client_data_sources to find the foreign table created by ETL
    - Falls back to analytics_silver if no foreign table exists
    - Foreign tables point directly to BigQuery via FDW

    Args:
        client_id: Client identifier

    Returns:
        Table name (either foreign table or fallback)
    """
    try:
        # Get database connection from environment
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logger.warning("DATABASE_URL not set, using fallback table")
            return FALLBACK_SILVER_TABLE

        # Query client_data_sources to find foreign table
        engine = create_engine(database_url)
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT storage_location
                    FROM client_data_sources
                    WHERE client_id = :client_id
                      AND storage_type = 'foreign_table'
                      AND sync_status = 'active'
                    ORDER BY last_synced_at DESC
                    LIMIT 1
                """),
                {"client_id": client_id}
            ).fetchone()

            if result and result[0]:
                foreign_table = result[0]
                logger.info(f"Using foreign table '{foreign_table}' for client_id: {client_id}")
                return foreign_table
            else:
                logger.warning(f"No foreign table found for client_id: {client_id}, using fallback")
                return FALLBACK_SILVER_TABLE

    except Exception as e:
        logger.error(f"Error looking up foreign table for client {client_id}: {e}")
        logger.info(f"Falling back to '{FALLBACK_SILVER_TABLE}'")
        return FALLBACK_SILVER_TABLE
