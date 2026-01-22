"""
ETL API Routes - Endpoints for running ETL jobs from BigQuery to Supabase.

NEW ARCHITECTURE (V2):
Uses Supabase BigQuery Foreign Data Wrapper instead of heavy Python SDK.

Flow:
1. Create BigQuery foreign server in Supabase (stores credentials)
2. Create foreign table mapping to BigQuery table
3. Extract via pure SQL: INSERT INTO analytics_silver SELECT * FROM foreign_table

Benefits:
- 120MB smaller (no google-cloud-bigquery, pandas, pyarrow)
- Faster (pure SQL, no Python serialization)
- Simpler (fewer moving parts)
"""

import logging
from typing import Any

from data_ingestion_api.services.etl_service_v2 import etl_service_v2
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from vizu_auth.fastapi.dependencies import get_auth_result


async def get_auth(auth=Depends(get_auth_result)):
    # Keep auth dependency for authentication, but do not enforce client_id
    if not auth:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/etl", tags=["ETL - Extract, Transform, Load"])


# --- Pydantic Models ---


class ETLJobRequest(BaseModel):
    """Request to start an ETL job."""

    credential_id: str = Field(..., description="ID of the BigQuery credential")
    client_id: str = Field(
        ..., description="Client identifier for RLS isolation (cliente_vizu.id)"
    )
    resource_type: str = Field(
        default="invoices", description="Type of resource (invoices, products, etc.)"
    )
    bigquery_table: str | None = Field(
        None,
        description="Full BigQuery table name (e.g., 'project.dataset.table'). "
        "Uses default test table if not provided.",
    )
    limit: int | None = Field(
        None, description="Optional limit on number of rows to process (for testing)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "credential_id": "uuid-of-credential",
                "client_id": "e2e-test-client",
                "resource_type": "invoices",
                "bigquery_table": "`analytics-big-query-242119.dataform.products_invoices`",
                "limit": 1000,
            }
        }


class ETLJobResponse(BaseModel):
    """Response from ETL job."""

    status: str  # "success" or "error"
    client_id: str
    resource_type: str
    rows_processed: int | None = None
    rows_inserted: int | None = None
    table: str | None = None
    error: str | None = None
    message: str | None = None


# --- Endpoints ---


@router.post(
    "/run",
    response_model=ETLJobResponse,
    summary="Run ETL job from BigQuery to Supabase analytics_silver",
)
async def run_etl_job(
    request: ETLJobRequest,
    auth=Depends(get_auth),
) -> ETLJobResponse:
    """
    Run a complete ETL job:

    1. **Extract:** Fetch data from BigQuery using stored credentials
    2. **Transform:** Apply schema mapping to rename/transform columns
    3. **Load:** Write to Supabase `analytics_silver` table with `client_id`

    The data is written with the provided `client_id`, which enables Row Level Security (RLS)
    to automatically isolate data between different clients.

    **Prerequisites:**
    - BigQuery credentials must be configured (uses GOOGLE_APPLICATION_CREDENTIALS)
    - Schema mapping must exist for (credential_id, resource_type)
    - Supabase `analytics_silver` table must exist

    **Example Flow:**
    ```bash
    # 1. Create schema mapping first
    POST /schema/mappings
    {
      "credential_id": "cred-123",
      "resource_type": "invoices",
      "mapping": {"order_id": "order_id", "total": "valor_total_emitter", ...}
    }

    # 2. Run ETL job
    POST /etl/run
    {
      "credential_id": "cred-123",
      "client_id": "client-abc",
      "resource_type": "invoices",
      "limit": 1000
    }
    ```

    **Returns:**
    - Success: Number of rows processed and inserted
    - Error: Error message with details
    """
    try:
        logger.info(f"ETL V2 job requested: {request.dict()}")

        result = await etl_service_v2.run_etl_job(
            credential_id=request.credential_id,
            client_id=request.client_id,
            resource_type=request.resource_type,
            bigquery_table=request.bigquery_table,
            limit=request.limit,
        )

        if result["status"] == "error":
            logger.error(f"ETL job failed: {result.get('error')}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "ETL job failed"),
            )

        logger.info(f"ETL job completed successfully: {result}")

        return ETLJobResponse(
            status="success",
            client_id=result["client_id"],
            resource_type=result["resource_type"],
            rows_processed=result.get("rows_processed"),
            rows_inserted=result.get("rows_inserted"),
            table=result.get("foreign_table") or result.get("table"),
            message=f"Successfully processed {result.get('rows_processed', 0)} rows",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in ETL endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ETL job failed: {str(e)}",
        )


@router.get("/status", summary="Get ETL service status")
async def get_etl_status() -> dict[str, Any]:
    """
    Get status of ETL service.

    Returns information about ETL configuration and readiness.
    """
    return {
        "service": "ETL Service",
        "status": "ready",
        "endpoints": {
            "run_job": "POST /etl/run",
        },
        "data_flow": "BigQuery FDW → Direct SQL → Supabase analytics_silver",
        "target_table": "analytics_silver",
        "architecture": "v2_fdw",
        "features": [
            "Supabase BigQuery Foreign Data Wrapper (no Python SDK)",
            "Pure SQL extraction (no pandas/pyarrow)",
            "RLS-based multi-tenant isolation via client_id",
            "120MB lighter than v1 (no heavy dependencies)",
        ],
    }
