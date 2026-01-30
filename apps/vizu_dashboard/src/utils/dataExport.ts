/**
 * Data Export Utilities
 *
 * Functions for exporting structured data to various formats (CSV, clipboard)
 * and integrating with Google Sheets.
 */

import type { StructuredData, Column } from '../components/SimpleDataTable';

/**
 * Convert structured data to CSV string
 */
export function toCSV(data: StructuredData): string {
  if (!data.rows.length) return '';

  const headers = data.columns.map((c) => c.label).join(',');
  const rows = data.rows
    .map((row) =>
      data.columns
        .map((c) => {
          const val = row[c.key] ?? '';
          // Escape commas and quotes in CSV
          return `"${String(val).replace(/"/g, '""')}"`;
        })
        .join(',')
    )
    .join('\n');

  return `${headers}\n${rows}`;
}

/**
 * Download data as CSV file
 */
export function downloadCSV(data: StructuredData, filename?: string): void {
  const csv = toCSV(data);
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename || `${data.title?.replace(/[^a-z0-9]/gi, '_') || 'dados'}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

/**
 * Copy data to clipboard as tab-separated values (for pasting into spreadsheets)
 */
export async function copyToClipboard(data: StructuredData): Promise<void> {
  const headers = data.columns.map((c) => c.label).join('\t');
  const rows = data.rows.map((row) => data.columns.map((c) => row[c.key] ?? '').join('\t')).join('\n');

  await navigator.clipboard.writeText(`${headers}\n${rows}`);
}

/**
 * Convert structured data to Google Sheets format (array of arrays)
 */
export function toSheetsFormat(data: StructuredData): unknown[][] {
  if (!data.rows.length) return [];

  // Header row with labels
  const header = data.columns.map((c) => c.label);

  // Data rows
  const rows = data.rows.map((row) => data.columns.map((c) => row[c.key] ?? ''));

  return [header, ...rows];
}

/**
 * Format a cell value based on column type for display
 */
export function formatValue(value: unknown, type: Column['type']): string {
  if (value == null) return '-';

  switch (type) {
    case 'currency':
      return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL',
      }).format(Number(value));
    case 'number':
      return new Intl.NumberFormat('pt-BR').format(Number(value));
    case 'date':
      return new Date(String(value)).toLocaleDateString('pt-BR');
    case 'datetime':
      return new Date(String(value)).toLocaleString('pt-BR');
    case 'boolean':
      return value ? 'Sim' : 'Não';
    default:
      return String(value);
  }
}

/**
 * Infer a summary of the data for display
 */
export function generateSummary(data: StructuredData): string {
  const count = data.total_rows || data.rows.length;
  if (data.has_more) {
    return `Exibindo ${data.rows.length} de ${count} registros. Exporte para ver todos.`;
  }
  return `${count} registro(s) encontrado(s)`;
}

export type { StructuredData, Column };
