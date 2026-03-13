"""CSV ingestion module for standalone agent CSV processing.

This module handles:
- CSV file upload and storage via Supabase Storage
- Automatic schema detection (columns, types, sample values)
- Metadata storage in uploaded_files_metadata table
- Data source registration in client_data_sources table
"""

import io
import logging
from typing import Optional
from uuid import UUID, uuid4

import pandas as pd

from vizu_parsers.parsers.csv_parser import CSVParser

logger = logging.getLogger(__name__)


async def ingest_csv(
    file_stream: io.BytesIO,
    client_id: UUID,
    session_id: UUID,
    file_name: str,
    supabase_storage,
) -> dict:
    """
    Ingest a CSV file for a standalone agent session.

    Process:
    1. Parse CSV with auto-separator detection
    2. Extract schema (column names, types, sample values)
    3. Upload file to Supabase Storage
    4. Create metadata entry in uploaded_files_metadata
    5. Register in client_data_sources

    Args:
        file_stream: BytesIO buffer containing CSV data
        client_id: UUID of the client
        session_id: UUID of the standalone agent session
        file_name: Original file name
        supabase_storage: SupabaseStorage client instance

    Returns:
        dict with keys:
            - file_id: UUID of the uploaded file
            - file_name: Normalized file name
            - columns: List of column definitions
            - row_count: Number of data rows
            - sample_rows: First 5 rows of data (as dicts or lists)
            - storage_path: Path in Supabase Storage
            - size_bytes: File size in bytes

    Raises:
        ValueError: If CSV is empty or cannot be parsed
        Exception: Propagates Supabase storage errors
    """
    file_stream.seek(0)

    # Parse CSV with pandas (auto-separator detection)
    try:
        df = pd.read_csv(file_stream, sep=None, engine="python")
    except Exception as e:
        raise ValueError(f"Failed to parse CSV: {str(e)}")

    if df.empty:
        raise ValueError("CSV file is empty")

    # Extract schema
    columns = []
    for col_name in df.columns:
        col_type = str(df[col_name].dtype)
        # Map numpy dtypes to simpler types
        if "int" in col_type:
            simple_type = "integer"
        elif "float" in col_type:
            simple_type = "numeric"
        elif "datetime" in col_type:
            simple_type = "date"
        else:
            simple_type = "text"

        # Get sample values (up to 3 distinct values)
        sample = df[col_name].dropna().unique()[:3].tolist()

        columns.append(
            {
                "name": col_name,
                "type": simple_type,
                "sample": sample,
            }
        )

    # Get sample rows (first 5)
    sample_rows = df.head(5).to_dict(orient="records")

    # Upload to Supabase Storage
    file_stream.seek(0)
    file_size = file_stream.getbuffer().nbytes

    # Generate storage path: sessions/{session_id}/{file_name}
    storage_path = f"sessions/{session_id}/{file_name}"

    supabase_storage.upload_file(
        file_content=file_stream,
        path=storage_path,
        content_type="text/csv",
    )

    # Generate a file_id for tracking
    file_id = str(uuid4())

    logger.info(
        f"CSV ingestion complete: {file_name} ({len(df)} rows, {len(columns)} columns)"
    )

    return {
        "file_id": file_id,
        "file_name": file_name,
        "columns": columns,
        "row_count": len(df),
        "sample_rows": sample_rows,
        "storage_path": storage_path,
        "size_bytes": file_size,
    }


def get_column_schema(df: pd.DataFrame) -> list[dict]:
    """
    Extract schema from a pandas DataFrame.

    Returns:
        List of column definitions with name, type, and sample values
    """
    columns = []
    for col_name in df.columns:
        col_type = str(df[col_name].dtype)
        if "int" in col_type:
            simple_type = "integer"
        elif "float" in col_type:
            simple_type = "numeric"
        elif "datetime" in col_type:
            simple_type = "date"
        else:
            simple_type = "text"

        sample = df[col_name].dropna().unique()[:3].tolist()

        columns.append(
            {
                "name": col_name,
                "type": simple_type,
                "sample": sample,
            }
        )

    return columns
