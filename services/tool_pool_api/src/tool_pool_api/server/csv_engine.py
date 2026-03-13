"""DuckDB Query Engine for CSV Analysis.

Handles:
- Loading CSV files from Supabase Storage into DuckDB
- Executing SQL queries with full SQL support (JOINs, aggregations, window functions, CTEs)
- Multi-CSV analysis and joins
- Result formatting and caching
"""

import logging
import tempfile
from pathlib import Path
from typing import Optional
from uuid import UUID

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)


class DuckDBQueryEngine:
    """In-process analytical SQL engine for CSV queries."""

    def __init__(self):
        """Initialize DuckDB connection (in-memory for this session)."""
        self.conn = duckdb.connect(":memory:")
        # Enable full SQL support
        self._temp_dir = tempfile.mkdtemp(prefix="duckdb_csv_")

    async def load_csv(
        self,
        file_id: str,
        storage_path: str,
        file_name: str,
        supabase_storage,
    ) -> dict:
        """
        Load a CSV file from Supabase Storage into DuckDB.

        Args:
            file_id: UUID of the file
            storage_path: Path in Supabase Storage (e.g., 'sessions/xxx/file.csv')
            file_name: Original file name
            supabase_storage: SupabaseStorage client instance

        Returns:
            dict with keys:
                - table_name: Sanitized name for SQL (e.g., 'vendas_q1_2025')
                - columns: Column names and types
                - row_count: Number of rows loaded
        """
        # Download file from Supabase Storage
        file_buffer = await supabase_storage.download_file(
            bucket="csv_datasets",
            path=storage_path,
        )

        # Save to temp file for DuckDB to read
        temp_path = Path(self._temp_dir) / f"{file_id}.csv"
        with open(temp_path, "wb") as f:
            f.write(file_buffer.getvalue())

        # Sanitize table name from file_name: remove extension, replace spaces/dashes
        table_name = (
            Path(file_name).stem.lower().replace(" ", "_").replace("-", "_")
        )

        # Load into DuckDB
        try:
            self.conn.execute(
                f"""
                CREATE TABLE {table_name} AS
                SELECT * FROM read_csv_auto('{temp_path}')
                """
            )
        except Exception as e:
            logger.error(f"Failed to load CSV into DuckDB: {e}")
            raise

        # Get table info
        result = self.conn.execute(
            f"SELECT * FROM {table_name} LIMIT 0"
        ).description
        columns = [col[0] for col in result] if result else []

        row_count = self.conn.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        ).fetchone()[0]

        logger.info(
            f"Loaded {file_name} as {table_name}: {row_count} rows, {len(columns)} columns"
        )

        return {
            "table_name": table_name,
            "columns": columns,
            "row_count": row_count,
        }

    async def execute_query(
        self,
        sql: str,
        max_rows: int = 1000,
    ) -> dict:
        """
        Execute a SQL query using DuckDB.

        Args:
            sql: SQL SELECT query
            max_rows: Maximum rows to return

        Returns:
            dict with keys:
                - output: Formatted result as string (for display)
                - structured_data: Result as list of dicts
                - row_count: Number of rows returned
                - columns: Column names
                - execution_time_ms: Query execution time

        Raises:
            ValueError: If query is not a SELECT or contains forbidden keywords
            Exception: If DuckDB query execution fails
        """
        import time

        # Validate query (SELECT only, no DDL/DML)
        query_upper = sql.strip().upper()

        if not query_upper.startswith("SELECT"):
            raise ValueError("Only SELECT queries are allowed")

        forbidden_keywords = [
            "DROP",
            "DELETE",
            "INSERT",
            "UPDATE",
            "CREATE",
            "ALTER",
            "TRUNCATE",
        ]
        for keyword in forbidden_keywords:
            if f" {keyword} " in f" {query_upper} ":
                raise ValueError(f"Query contains forbidden keyword: {keyword}")

        # Execute query
        start_time = time.perf_counter()
        try:
            result = self.conn.execute(sql).fetchall()
            description = self.conn.execute(sql).description
            columns = [col[0] for col in description] if description else []
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Convert to dicts
        structured_data = []
        for row in result[:max_rows]:
            structured_data.append(dict(zip(columns, row)))

        # Format output as table string
        output = self._format_as_table(columns, result[:max_rows])

        logger.info(
            f"Query executed: {len(result)} rows in {elapsed_ms:.0f}ms"
        )

        return {
            "output": output,
            "structured_data": structured_data,
            "row_count": len(result),
            "columns": columns,
            "execution_time_ms": elapsed_ms,
        }

    @staticmethod
    def _format_as_table(columns: list[str], rows: list) -> str:
        """Format query result as ASCII table."""
        if not rows:
            return "No results"

        # Convert to pandas for pretty printing
        df = pd.DataFrame(rows, columns=columns)
        return df.to_string(index=False, max_rows=100, max_cols=10)

    def list_tables(self) -> list[dict]:
        """List all loaded tables with their schema."""
        result = self.conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()

        tables = []
        for (table_name,) in result:
            columns_result = self.conn.execute(
                f"SELECT column_name, column_type FROM information_schema.columns WHERE table_name='{table_name}' AND table_schema='main'"
            ).fetchall()

            columns = [
                {"name": col[0], "type": col[1]} for col in columns_result
            ]

            row_count = self.conn.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()[0]

            tables.append(
                {
                    "name": table_name,
                    "columns": columns,
                    "row_count": row_count,
                }
            )

        return tables

    def __del__(self):
        """Cleanup temp files on exit."""
        try:
            import shutil

            if hasattr(self, "_temp_dir"):
                shutil.rmtree(self._temp_dir, ignore_errors=True)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory: {e}")
