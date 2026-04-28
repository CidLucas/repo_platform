"""
Structured Data Models

Pydantic models for structured tabular data responses from SQL queries.
Used for rendering interactive data grids in the frontend.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ColumnType(Enum):
    """Data type for column formatting and sorting."""

    STRING = "string"
    NUMBER = "number"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    CURRENCY = "currency"  # For valor_total, valor_unitario, etc.


class StructuredDataColumn(BaseModel):
    """Definition of a data column for the frontend grid."""

    key: str = Field(..., description="Column identifier (matches data keys)")
    label: str = Field(..., description="Display name for column header")
    type: ColumnType = Field(
        ColumnType.STRING, description="Data type for formatting/sorting"
    )
    sortable: bool = Field(True, description="Whether column supports sorting")
    filterable: bool = Field(True, description="Whether column supports filtering")
    width: int | None = Field(None, description="Suggested column width in pixels")


class StructuredDataResponse(BaseModel):
    """
    Structured data format for frontend data grids.

    This model is returned alongside text responses when SQL queries produce
    tabular data. The frontend renders this as an interactive table with
    sorting, filtering, pagination, and export capabilities.
    """

    columns: list[StructuredDataColumn] = Field(..., description="Column definitions")
    rows: list[dict[str, Any]] = Field(..., description="Row data as list of dicts")
    total_rows: int = Field(..., description="Total row count (before pagination)")
    query_sql: str | None = Field(
        None, description="SQL query that generated this data (for debugging)"
    )
    export_id: str | None = Field(None, description="Unique ID for export operations")

    # Metadata for display
    title: str | None = Field(None, description="Optional title for the table")
    summary: str | None = Field(None, description="Brief summary of the data")

    # Pagination hint
    has_more: bool = Field(
        False, description="True if more rows exist beyond the display limit"
    )


__all__ = [
    "ColumnType",
    "StructuredDataColumn",
    "StructuredDataResponse",
]
