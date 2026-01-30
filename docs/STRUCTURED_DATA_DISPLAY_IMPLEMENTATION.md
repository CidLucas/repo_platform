# Structured Data Display Implementation Plan

## ✅ IMPLEMENTED - January 2026

## 📋 Executive Summary

This document outlines the implementation of enhanced SQL query results display in the Vizu chat interface. Instead of rendering raw markdown tables, users now get a Google Sheets-like interactive data grid with sorting, filtering, pagination, and export capabilities.

### User Requirements Applied:
1. **Google Sheets export**: Let user select existing spreadsheet ✅
2. **Row limit**: Display max 20 rows, export for full data ✅
3. **Mobile**: Card view on small screens ✅
4. **Column visibility**: Nice-to-have (deferred)
5. **Dark mode**: Supported via Chakra UI ✅

---

## 🎯 Objectives

1. **Structured Data Format**: Transform SQL query results into a well-typed structured format
2. **Interactive Data Grid**: Create a `SimpleDataTable` React component with sorting, filtering, pagination
3. **Export Capabilities**: Enable CSV download and Google Sheets export (leveraging existing `write_to_sheet` tool)
4. **Copy to Clipboard**: Quick data copying functionality
5. **Responsive Design**: Works on desktop and mobile

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                               BACKEND                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐    ┌────────────────────────┐    ┌─────────────────┐ │
│  │   sql_module.py  │───▶│ structured_data_       │───▶│ AgentChatResp.  │ │
│  │ executar_sql_    │    │ formatter.py           │    │ structured_data │ │
│  │ agent            │    │ - format_sql_result()  │    │                 │ │
│  └──────────────────┘    │ - to_csv()             │    └─────────────────┘ │
│                          │ - to_sheets_format()   │                         │
│                          └────────────────────────┘                         │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                               FRONTEND                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐    ┌────────────────────────┐                         │
│  │   ChatPanel.tsx  │───▶│  SimpleDataTable.tsx   │                         │
│  │   (message       │    │  - Sorting (▲▼)        │                         │
│  │   rendering)     │    │  - Filtering (search)  │                         │
│  └──────────────────┘    │  - Pagination          │                         │
│                          │  - Export CSV/Sheets   │                         │
│                          │  - Copy to Clipboard   │                         │
│                          └────────────────────────┘                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Files to Create/Modify

### Backend (tool_pool_api)

| File | Action | Purpose |
|------|--------|---------|
| `libs/vizu_models/src/vizu_models/structured_data.py` | **CREATE** | Pydantic models for structured data format |
| `services/tool_pool_api/src/tool_pool_api/server/tool_modules/structured_data_formatter.py` | **CREATE** | SQL result → structured data transformer + CSV/Sheets format converters |
| `services/tool_pool_api/src/tool_pool_api/server/tool_modules/sql_module.py` | **MODIFY** | Return structured data alongside raw output |
| `libs/vizu_models/src/vizu_models/agent_types.py` | **MODIFY** | Add `structured_data` field to `AgentChatResponse` |
| `services/tool_pool_api/src/tool_pool_api/server/tool_modules/google_module.py` | **MODIFY** | Add `export_sql_to_sheet` convenience wrapper |

### Frontend (vizu_dashboard)

| File | Action | Purpose |
|------|--------|---------|
| `apps/vizu_dashboard/src/components/SimpleDataTable.tsx` | **CREATE** | Interactive data grid component |
| `apps/vizu_dashboard/src/components/ChatPanel.tsx` | **MODIFY** | Detect and render structured data messages |
| `apps/vizu_dashboard/src/services/chatService.ts` | **MODIFY** | Update response interface for structured data |
| `apps/vizu_dashboard/src/utils/dataExport.ts` | **CREATE** | CSV download + copy utilities |

---

## 📦 Data Models

### 1. StructuredDataColumn (vizu_models)

```python
# libs/vizu_models/src/vizu_models/structured_data.py

from pydantic import BaseModel, Field
from enum import Enum

class ColumnType(str, Enum):
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
    type: ColumnType = Field(ColumnType.STRING, description="Data type for formatting/sorting")
    sortable: bool = Field(True, description="Whether column supports sorting")
    filterable: bool = Field(True, description="Whether column supports filtering")
    width: int | None = Field(None, description="Suggested column width in pixels")
```

### 2. StructuredDataResponse (vizu_models)

```python
class StructuredDataResponse(BaseModel):
    """Structured data format for frontend data grids."""

    columns: list[StructuredDataColumn] = Field(..., description="Column definitions")
    rows: list[dict] = Field(..., description="Row data as list of dicts")
    total_rows: int = Field(..., description="Total row count (before pagination)")
    query_sql: str | None = Field(None, description="SQL query that generated this data")
    export_id: str | None = Field(None, description="Unique ID for export operations")

    # Metadata for display
    title: str | None = Field(None, description="Optional title for the table")
    summary: str | None = Field(None, description="Brief summary of the data")
```

### 3. Updated AgentChatResponse

```python
# libs/vizu_models/src/vizu_models/agent_types.py

class AgentChatResponse(BaseModel):
    response: str = Field(..., description="Resposta do agente")
    session_id: str = Field(..., description="ID da sessão")
    model_used: str | None = Field(None)
    elicitation_pending: ElicitationRequest | None = Field(None)
    tools_called: list[str] | None = Field(None)
    trace_id: str | None = Field(None)

    # NEW FIELD
    structured_data: StructuredDataResponse | None = Field(
        None,
        description="Structured tabular data for rich display (from SQL queries)"
    )
```

---

## 🔧 Backend Implementation Details

### 1. structured_data_formatter.py

```python
# services/tool_pool_api/src/tool_pool_api/server/tool_modules/structured_data_formatter.py

"""
Structured Data Formatter

Transforms SQL query results into a format optimized for frontend data grids.
Also provides export utilities (CSV, Google Sheets format).
"""

import csv
import io
import re
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
    """
    name_lower = column_name.lower()

    # Currency detection by name
    currency_patterns = ['valor', 'preco', 'price', 'revenue', 'total_revenue', 'avg_order_value']
    if any(p in name_lower for p in currency_patterns):
        return ColumnType.CURRENCY

    # Date/datetime detection by name
    date_patterns = ['data_', 'date', 'created_at', 'updated_at', '_at']
    if any(p in name_lower for p in date_patterns):
        return ColumnType.DATETIME

    # Number detection by name
    number_patterns = ['quantidade', 'qty', 'count', 'total_', 'num_', '_count']
    if any(p in name_lower for p in number_patterns):
        return ColumnType.NUMBER

    # Infer from values
    non_null_values = [v for v in sample_values if v is not None]
    if not non_null_values:
        return ColumnType.STRING

    sample = non_null_values[0]

    if isinstance(sample, bool):
        return ColumnType.BOOLEAN
    if isinstance(sample, (int, float, Decimal)):
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
    """
    # Handle common abbreviations
    abbreviations = {
        'id': 'ID',
        'uuid': 'UUID',
        'cpf': 'CPF',
        'cnpj': 'CNPJ',
        'uf': 'UF',
    }

    words = column_name.split('_')
    result = []

    for word in words:
        if word.lower() in abbreviations:
            result.append(abbreviations[word.lower()])
        else:
            result.append(word.capitalize())

    return ' '.join(result)


def format_sql_result(
    columns: list[str],
    rows: list[dict],
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
    for row in rows:
        serialized = {}
        for key, value in row.items():
            if isinstance(value, (datetime, date)):
                serialized[key] = value.isoformat()
            elif isinstance(value, Decimal):
                serialized[key] = float(value)
            elif isinstance(value, uuid.UUID):
                serialized[key] = str(value)
            else:
                serialized[key] = value
        serialized_rows.append(serialized)

    # Generate summary
    summary = f"{len(rows)} registro(s) encontrado(s)"
    if len(rows) >= 1000:
        summary += " (limite atingido)"

    return StructuredDataResponse(
        columns=column_defs,
        rows=serialized_rows,
        total_rows=len(rows),
        query_sql=sql_query,
        export_id=str(uuid.uuid4()),
        title=title,
        summary=summary,
    )


def to_csv(data: StructuredDataResponse) -> str:
    """
    Convert structured data to CSV string.

    Args:
        data: StructuredDataResponse

    Returns:
        CSV string content
    """
    output = io.StringIO()

    if not data.rows:
        return ""

    # Use column keys for headers
    fieldnames = [col.key for col in data.columns]
    writer = csv.DictWriter(output, fieldnames=fieldnames)

    # Write header with labels
    header = {col.key: col.label for col in data.columns}
    writer.writerow(header)

    # Write data rows
    for row in data.rows:
        writer.writerow({k: row.get(k, '') for k in fieldnames})

    return output.getvalue()


def to_sheets_format(data: StructuredDataResponse) -> list[list[Any]]:
    """
    Convert structured data to Google Sheets format (list of rows).

    Args:
        data: StructuredDataResponse

    Returns:
        List of lists suitable for Google Sheets append_values
    """
    if not data.rows:
        return []

    # Header row with labels
    header = [col.label for col in data.columns]

    # Data rows
    rows = [header]
    for row in data.rows:
        row_values = [row.get(col.key, '') for col in data.columns]
        rows.append(row_values)

    return rows
```

### 2. SQL Module Changes

```python
# services/tool_pool_api/src/tool_pool_api/server/tool_modules/sql_module.py

# In _executar_sql_agent_logic, after executing the query:

from .structured_data_formatter import format_sql_result

# ... existing code ...

# After: cursor = conn.execute(sa_text(final_sql))
#        results = cursor.fetchall()

if not results:
    result = "No results found."
    structured_data = None
else:
    columns = list(cursor.keys())
    rows_as_dicts = [dict(zip(columns, row)) for row in results]

    # Create structured data for frontend
    structured_data = format_sql_result(
        columns=columns,
        rows=rows_as_dicts,
        sql_query=final_sql,
        title=f"Resultado: {query[:50]}..."  # Truncate for title
    )

    # Keep text result for backward compatibility
    result = str(rows_as_dicts)

return {
    "output": result,
    "sql": final_sql,
    "success": True,
    "structured_data": structured_data.model_dump() if structured_data else None,
}
```

### 3. Google Module Export Extension

```python
# services/tool_pool_api/src/tool_pool_api/server/tool_modules/google_module.py

# Add new tool for SQL export to Sheets

async def _export_data_to_sheet_logic(
    data: list[list],
    sheet_title: str,
    cliente_id: str,
    account_email: str | None = None,
) -> dict:
    """Export structured data to a new Google Sheet."""
    tokens = await _get_google_tokens(cliente_id, account_email)
    client = GoogleSheetsClient(access_token=tokens["access_token"])

    # Create new spreadsheet
    spreadsheet = await client.create_spreadsheet(sheet_title)
    spreadsheet_id = spreadsheet["spreadsheet_id"]

    # Write data
    await client.append_values(spreadsheet_id, "A1", data)

    return {
        "status": "success",
        "spreadsheet_id": spreadsheet_id,
        "spreadsheet_url": spreadsheet["spreadsheet_url"],
        "rows_written": len(data),
    }
```

---

## 🎨 Frontend Implementation Details

### 1. SimpleDataTable Component

```tsx
// apps/vizu_dashboard/src/components/SimpleDataTable.tsx

import {
  Box,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Input,
  HStack,
  IconButton,
  Text,
  Select,
  Flex,
  Button,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Tooltip,
  useToast,
} from '@chakra-ui/react';
import {
  TriangleDownIcon,
  TriangleUpIcon,
  DownloadIcon,
  CopyIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from '@chakra-ui/icons';
import { useState, useMemo } from 'react';
import { FaGoogleDrive } from 'react-icons/fa';

// Types matching backend StructuredDataResponse
interface Column {
  key: string;
  label: string;
  type: 'string' | 'number' | 'date' | 'datetime' | 'boolean' | 'currency';
  sortable?: boolean;
  filterable?: boolean;
  width?: number;
}

interface StructuredData {
  columns: Column[];
  rows: Record<string, any>[];
  total_rows: number;
  title?: string;
  summary?: string;
  export_id?: string;
}

interface SimpleDataTableProps {
  data: StructuredData;
  onExportToSheets?: (data: StructuredData) => Promise<void>;
  maxHeight?: string;
}

export const SimpleDataTable = ({
  data,
  onExportToSheets,
  maxHeight = '400px'
}: SimpleDataTableProps) => {
  const toast = useToast();

  // Sorting state
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  // Filtering state
  const [filters, setFilters] = useState<Record<string, string>>({});

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Filter rows
  const filteredRows = useMemo(() => {
    return data.rows.filter(row => {
      return Object.entries(filters).every(([key, value]) => {
        if (!value) return true;
        const cellValue = String(row[key] ?? '').toLowerCase();
        return cellValue.includes(value.toLowerCase());
      });
    });
  }, [data.rows, filters]);

  // Sort rows
  const sortedRows = useMemo(() => {
    if (!sortColumn) return filteredRows;

    return [...filteredRows].sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];

      // Handle nulls
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return sortDirection === 'asc' ? 1 : -1;
      if (bVal == null) return sortDirection === 'asc' ? -1 : 1;

      // Compare based on type
      const column = data.columns.find(c => c.key === sortColumn);
      if (column?.type === 'number' || column?.type === 'currency') {
        return sortDirection === 'asc'
          ? Number(aVal) - Number(bVal)
          : Number(bVal) - Number(aVal);
      }

      return sortDirection === 'asc'
        ? String(aVal).localeCompare(String(bVal))
        : String(bVal).localeCompare(String(aVal));
    });
  }, [filteredRows, sortColumn, sortDirection, data.columns]);

  // Paginate rows
  const paginatedRows = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return sortedRows.slice(start, start + pageSize);
  }, [sortedRows, currentPage, pageSize]);

  const totalPages = Math.ceil(sortedRows.length / pageSize);

  // Handlers
  const handleSort = (columnKey: string) => {
    if (sortColumn === columnKey) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(columnKey);
      setSortDirection('asc');
    }
  };

  const handleFilterChange = (columnKey: string, value: string) => {
    setFilters(prev => ({ ...prev, [columnKey]: value }));
    setCurrentPage(1);
  };

  const formatCellValue = (value: any, type: Column['type']) => {
    if (value == null) return '-';

    switch (type) {
      case 'currency':
        return new Intl.NumberFormat('pt-BR', {
          style: 'currency',
          currency: 'BRL'
        }).format(Number(value));
      case 'number':
        return new Intl.NumberFormat('pt-BR').format(Number(value));
      case 'date':
        return new Date(value).toLocaleDateString('pt-BR');
      case 'datetime':
        return new Date(value).toLocaleString('pt-BR');
      case 'boolean':
        return value ? 'Sim' : 'Não';
      default:
        return String(value);
    }
  };

  // Export functions
  const copyToClipboard = async () => {
    const headers = data.columns.map(c => c.label).join('\t');
    const rows = sortedRows.map(row =>
      data.columns.map(c => row[c.key] ?? '').join('\t')
    ).join('\n');

    await navigator.clipboard.writeText(`${headers}\n${rows}`);
    toast({
      title: 'Copiado!',
      description: 'Dados copiados para a área de transferência',
      status: 'success',
      duration: 2000,
    });
  };

  const downloadCSV = () => {
    const headers = data.columns.map(c => c.label).join(',');
    const rows = sortedRows.map(row =>
      data.columns.map(c => {
        const val = row[c.key] ?? '';
        // Escape commas and quotes in CSV
        return `"${String(val).replace(/"/g, '""')}"`;
      }).join(',')
    ).join('\n');

    const csv = `${headers}\n${rows}`;
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${data.title || 'dados'}.csv`;
    link.click();
    URL.revokeObjectURL(url);

    toast({
      title: 'Download iniciado',
      status: 'success',
      duration: 2000,
    });
  };

  return (
    <Box
      borderRadius="lg"
      border="1px solid"
      borderColor="gray.200"
      overflow="hidden"
      bg="white"
    >
      {/* Header with title and actions */}
      <Flex
        justify="space-between"
        align="center"
        p={3}
        borderBottom="1px solid"
        borderColor="gray.100"
        bg="gray.50"
      >
        <Box>
          {data.title && (
            <Text fontWeight="600" fontSize="sm">{data.title}</Text>
          )}
          <Text fontSize="xs" color="gray.500">{data.summary}</Text>
        </Box>

        <HStack spacing={2}>
          <Tooltip label="Copiar dados">
            <IconButton
              aria-label="Copiar"
              icon={<CopyIcon />}
              size="sm"
              variant="ghost"
              onClick={copyToClipboard}
            />
          </Tooltip>

          <Menu>
            <MenuButton as={IconButton} aria-label="Exportar" icon={<DownloadIcon />} size="sm" variant="ghost" />
            <MenuList>
              <MenuItem icon={<DownloadIcon />} onClick={downloadCSV}>
                Download CSV
              </MenuItem>
              {onExportToSheets && (
                <MenuItem
                  icon={<FaGoogleDrive />}
                  onClick={() => onExportToSheets(data)}
                >
                  Exportar para Google Sheets
                </MenuItem>
              )}
            </MenuList>
          </Menu>
        </HStack>
      </Flex>

      {/* Table */}
      <Box overflowX="auto" maxH={maxHeight} overflowY="auto">
        <Table size="sm" variant="simple">
          <Thead position="sticky" top={0} bg="white" zIndex={1}>
            {/* Filter row */}
            <Tr>
              {data.columns.map(col => (
                <Th key={`filter-${col.key}`} p={1}>
                  {col.filterable !== false && (
                    <Input
                      size="xs"
                      placeholder="Filtrar..."
                      value={filters[col.key] || ''}
                      onChange={(e) => handleFilterChange(col.key, e.target.value)}
                    />
                  )}
                </Th>
              ))}
            </Tr>
            {/* Header row */}
            <Tr>
              {data.columns.map(col => (
                <Th
                  key={col.key}
                  cursor={col.sortable !== false ? 'pointer' : 'default'}
                  onClick={() => col.sortable !== false && handleSort(col.key)}
                  _hover={col.sortable !== false ? { bg: 'gray.50' } : undefined}
                  whiteSpace="nowrap"
                >
                  <HStack spacing={1}>
                    <Text>{col.label}</Text>
                    {sortColumn === col.key && (
                      sortDirection === 'asc'
                        ? <TriangleUpIcon boxSize={3} />
                        : <TriangleDownIcon boxSize={3} />
                    )}
                  </HStack>
                </Th>
              ))}
            </Tr>
          </Thead>
          <Tbody>
            {paginatedRows.map((row, idx) => (
              <Tr key={idx} _hover={{ bg: 'gray.50' }}>
                {data.columns.map(col => (
                  <Td key={col.key} whiteSpace="nowrap">
                    {formatCellValue(row[col.key], col.type)}
                  </Td>
                ))}
              </Tr>
            ))}
          </Tbody>
        </Table>
      </Box>

      {/* Pagination */}
      <Flex
        justify="space-between"
        align="center"
        p={3}
        borderTop="1px solid"
        borderColor="gray.100"
        bg="gray.50"
      >
        <HStack spacing={2}>
          <Text fontSize="xs" color="gray.500">Linhas por página:</Text>
          <Select
            size="xs"
            w="70px"
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setCurrentPage(1);
            }}
          >
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </Select>
        </HStack>

        <HStack spacing={2}>
          <Text fontSize="xs" color="gray.500">
            {(currentPage - 1) * pageSize + 1}-{Math.min(currentPage * pageSize, sortedRows.length)} de {sortedRows.length}
          </Text>
          <IconButton
            aria-label="Página anterior"
            icon={<ChevronLeftIcon />}
            size="xs"
            isDisabled={currentPage === 1}
            onClick={() => setCurrentPage(p => p - 1)}
          />
          <IconButton
            aria-label="Próxima página"
            icon={<ChevronRightIcon />}
            size="xs"
            isDisabled={currentPage >= totalPages}
            onClick={() => setCurrentPage(p => p + 1)}
          />
        </HStack>
      </Flex>
    </Box>
  );
};
```

### 2. ChatPanel Updates

```tsx
// apps/vizu_dashboard/src/components/ChatPanel.tsx

// Add to Message interface:
interface Message {
  id: string;
  content: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
  structuredData?: StructuredData; // NEW
}

// In the messages rendering section, add detection:
{messages.map((message) => (
  <Flex key={message.id} justify={message.sender === 'user' ? 'flex-end' : 'flex-start'}>
    <Box maxW="85%">
      {/* Text content */}
      {message.content && (
        <Box
          bg={message.sender === 'user' ? 'black' : 'rgba(0, 0, 0, 0.06)'}
          color={message.sender === 'user' ? 'white' : 'black'}
          px={4}
          py={3}
          borderRadius="18px"
        >
          <Text fontSize="15px">{message.content}</Text>
        </Box>
      )}

      {/* Structured data table */}
      {message.structuredData && (
        <Box mt={2}>
          <SimpleDataTable
            data={message.structuredData}
            onExportToSheets={handleExportToSheets}
          />
        </Box>
      )}
    </Box>
  </Flex>
))}
```

---

## 🔄 Data Flow

```
1. User asks: "Quais são os top 10 produtos por receita?"
                    │
                    ▼
2. ChatPanel sends POST /chat
                    │
                    ▼
3. atendente_core processes → calls executar_sql_agent tool
                    │
                    ▼
4. sql_module generates SQL, executes, formats with structured_data_formatter
                    │
                    ▼
5. Response includes:
   {
     "response": "Aqui estão os top 10 produtos...",
     "structured_data": {
       "columns": [...],
       "rows": [...],
       "total_rows": 10
     }
   }
                    │
                    ▼
6. ChatPanel detects structured_data → renders SimpleDataTable
                    │
                    ▼
7. User can sort, filter, export, copy
```

---

## ✅ Implementation Checklist

### Phase 1: Backend Data Models (Day 1)
- [ ] Create `libs/vizu_models/src/vizu_models/structured_data.py`
- [ ] Add models: `ColumnType`, `StructuredDataColumn`, `StructuredDataResponse`
- [ ] Update `libs/vizu_models/src/vizu_models/__init__.py` exports
- [ ] Update `AgentChatResponse` with `structured_data` field

### Phase 2: Backend Formatter (Day 1-2)
- [ ] Create `structured_data_formatter.py` in tool_modules
- [ ] Implement `format_sql_result()`
- [ ] Implement `to_csv()` and `to_sheets_format()`
- [ ] Update `sql_module.py` to return structured data

### Phase 3: Frontend Component (Day 2-3)
- [ ] Create `SimpleDataTable.tsx` component
- [ ] Implement sorting logic
- [ ] Implement filtering logic
- [ ] Implement pagination
- [ ] Implement CSV download
- [ ] Implement copy to clipboard
- [ ] Add Google Sheets export button (calls existing tool)

### Phase 4: Integration (Day 3-4)
- [ ] Update `chatService.ts` interfaces
- [ ] Update `ChatPanel.tsx` to detect and render structured data
- [ ] Test end-to-end flow
- [ ] Handle edge cases (empty results, large datasets)

### Phase 5: Polish (Day 4-5)
- [ ] Responsive design testing
- [ ] Loading states
- [ ] Error handling
- [ ] Performance optimization for large datasets

---

## ⚠️ Key Considerations

### Security
- SQL queries already have client_id injection - structured data inherits this
- No sensitive columns (like client_id) should appear in column definitions
- Export to Sheets uses existing authenticated Google integration

### Performance
- Pagination is client-side for simplicity (data is already limited to 1000 rows by SQL)
- Consider virtual scrolling if datasets exceed 1000 rows frequently
- CSV export works on filtered/sorted data (what user sees)

### UX
- Table should be visually distinct from regular chat messages
- Export options should be discoverable but not cluttered
- Column widths should auto-adjust based on content

---

## 🚀 Quick Start

After approval, run:

```bash
# Backend
cd libs/vizu_models && poetry install
cd services/tool_pool_api && poetry install

# Frontend
cd apps/vizu_dashboard && npm install

# Test
make up
```

---

## ❓ Questions for Clarification

1. **Google Sheets flow**: Should export create a NEW spreadsheet each time, or should users be able to select an existing one?

2. **Large datasets**: The SQL module limits to 1000 rows. Should we show a warning when the limit is hit? Allow users to "load more"?

3. **Mobile experience**: On small screens, should we switch to a card-based view instead of horizontal scroll?

4. **Column visibility**: Should users be able to hide/show columns?

5. **Theming**: Should the table follow dark mode if the user has it enabled?

Please review this plan and let me know if you have any questions or modifications before we proceed with implementation.
