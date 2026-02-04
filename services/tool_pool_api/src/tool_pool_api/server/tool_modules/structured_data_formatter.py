"""
Structured Data Formatter

Transforms SQL query results into a format optimized for frontend data grids.
Also provides export utilities (CSV, Google Sheets format).

Usage:
    from .structured_data_formatter import format_sql_result, to_csv, to_sheets_format

    # After SQL query execution
    structured = format_sql_result(columns, rows, sql_query="SELECT ...")

    # For exports
    csv_string = to_csv(structured)
    sheets_data = to_sheets_format(structured)
"""

import csv
import io
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from vizu_models.structured_data import (
    ColumnType,
    StructuredDataColumn,
    StructuredDataResponse,
)


def infer_column_type(column_name: str, sample_values: list[Any]) -> ColumnType:
    """
    Infer the column type from column name and sample values.

    Uses naming conventions common in analytics_v2 schema:
    - valor_*, preco_*, total_*, revenue -> CURRENCY
    - data_*, created_at, updated_at -> DATETIME
    - quantidade, count, qty -> NUMBER

    Args:
        column_name: Name of the column
        sample_values: Sample values from the column for type inference

    Returns:
        Inferred ColumnType enum value
    """
    name_lower = column_name.lower()

    # Currency detection by name
    currency_patterns = [
        "valor", "preco", "price", "revenue", "total_revenue",
        "avg_order_value", "faturamento", "receita"
    ]
    if any(p in name_lower for p in currency_patterns):
        return ColumnType.CURRENCY

    # Date/datetime detection by name
    date_patterns = ["data_", "date", "created_at", "updated_at", "_at", "timestamp"]
    if any(p in name_lower for p in date_patterns):
        return ColumnType.DATETIME

    # Number detection by name
    number_patterns = [
        "quantidade", "qty", "count", "total_", "num_", "_count",
        "rank", "position", "order"
    ]
    if any(p in name_lower for p in number_patterns):
        return ColumnType.NUMBER

    # Infer from values
    non_null_values = [v for v in sample_values if v is not None]
    if not non_null_values:
        return ColumnType.STRING

    sample = non_null_values[0]

    if isinstance(sample, bool):
        return ColumnType.BOOLEAN
    if isinstance(sample, int | float | Decimal):
        return ColumnType.NUMBER
    if isinstance(sample, datetime):
        return ColumnType.DATETIME
    if isinstance(sample, date):
        return ColumnType.DATE

    return ColumnType.STRING


def humanize_column_name(column_name: str) -> str:
    """
    Convert snake_case column names to human-readable labels.

    Examples:
        total_revenue -> Total Revenue
        data_transacao -> Data Transação
        customer_id -> Customer ID

    Args:
        column_name: Snake case column name

    Returns:
        Human readable label
    """
    # Handle common abbreviations
    abbreviations = {
        "id": "ID",
        "uuid": "UUID",
        "cpf": "CPF",
        "cnpj": "CNPJ",
        "uf": "UF",
        "cep": "CEP",
    }

    words = column_name.split("_")
    result = []

    for word in words:
        if word.lower() in abbreviations:
            result.append(abbreviations[word.lower()])
        else:
            result.append(word.capitalize())

    return " ".join(result)


def serialize_value(value: Any) -> Any:
    """
    Serialize a value to JSON-compatible format.

    Args:
        value: Any value from SQL result

    Returns:
        JSON-serializable value
    """
    if value is None:
        return None
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def format_sql_result(
    columns: list[str],
    rows: list[dict[str, Any]],
    sql_query: str | None = None,
    title: str | None = None,
) -> StructuredDataResponse:
    """
    Transform SQL query results into structured data format.

    Args:
        columns: List of column names from SQL result
        rows: List of row dicts (column_name -> value)
        sql_query: Optional SQL query for reference
        title: Optional title for the table

    Returns:
        StructuredDataResponse ready for frontend consumption
    """
    total_rows = len(rows)

    # All rows sent to frontend (frontend handles pagination)
    display_rows = rows

    # Build column definitions
    column_defs = []
    for col_name in columns:
        # Get sample values for type inference
        sample_values = [row.get(col_name) for row in rows[:10]]
        col_type = infer_column_type(col_name, sample_values)

        column_defs.append(StructuredDataColumn(
            key=col_name,
            label=humanize_column_name(col_name),
            type=col_type,
            sortable=True,
            filterable=True,
        ))

    # Serialize rows (handle non-JSON-serializable types)
    serialized_rows = []
    for row in display_rows:
        serialized = {key: serialize_value(value) for key, value in row.items()}
        serialized_rows.append(serialized)

    # Generate summary
    summary = f"{total_rows} registro(s) encontrado(s)"

    return StructuredDataResponse(
        columns=column_defs,
        rows=serialized_rows,
        total_rows=total_rows,
        query_sql=sql_query,
        export_id=str(uuid.uuid4()),
        title=title,
        summary=summary,
        has_more=False,  # All rows now sent to frontend
    )


def to_csv(data: StructuredDataResponse, all_rows: list[dict[str, Any]] | None = None) -> str:
    """
    Convert structured data to CSV string.

    Args:
        data: StructuredDataResponse with column definitions
        all_rows: Optional full row list (if data.rows is truncated).
                  If None, uses data.rows

    Returns:
        CSV string content
    """
    rows_to_export = all_rows if all_rows is not None else data.rows

    if not rows_to_export:
        return ""

    output = io.StringIO()

    # Use column keys for headers
    fieldnames = [col.key for col in data.columns]
    writer = csv.DictWriter(output, fieldnames=fieldnames)

    # Write header with labels
    header = {col.key: col.label for col in data.columns}
    writer.writerow(header)

    # Write data rows
    for row in rows_to_export:
        writer.writerow({k: row.get(k, "") for k in fieldnames})

    return output.getvalue()


def to_sheets_format(
    data: StructuredDataResponse,
    all_rows: list[dict[str, Any]] | None = None
) -> list[list[Any]]:
    """
    Convert structured data to Google Sheets format (list of rows).

    Args:
        data: StructuredDataResponse with column definitions
        all_rows: Optional full row list (if data.rows is truncated).
                  If None, uses data.rows

    Returns:
        List of lists suitable for Google Sheets append_values
    """
    rows_to_export = all_rows if all_rows is not None else data.rows

    if not rows_to_export:
        return []

    # Header row with labels
    header = [col.label for col in data.columns]

    # Data rows
    result = [header]
    for row in rows_to_export:
        row_values = [row.get(col.key, "") for col in data.columns]
        result.append(row_values)

    return result


__all__ = [
    "format_sql_result",
    "to_csv",
    "to_sheets_format",
]
